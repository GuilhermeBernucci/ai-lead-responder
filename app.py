"""
Kit de agendamento com IA para barbearias e salões.

- http://localhost:8000/        -> site da barbearia (fictícia) com o chat que agenda
- http://localhost:8000/painel  -> painel do dono: agenda + lembretes, explicados passo a passo
- http://localhost:8000/planos  -> página de preços (o que VOCÊ vende para a barbearia)
"""

import html
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from ia import SERVICOS, responder

PASTA = Path(__file__).parent
ARQUIVO_AGENDA = PASTA / "agendamentos.json"
FORMATO_SLOT = "%A %b %d %H:%M"  # ex.: "Friday Nov 27 15:00"


def hora(dt):
    """"3:00 PM" sem zero à esquerda; o %-I do strftime não funciona no Windows."""
    return f"{dt.hour % 12 or 12}:{dt:%M %p}"


# ---------------- Dados ----------------

def slot_para_data(slot: str) -> datetime:
    agora = datetime.now()
    data = datetime.strptime(f"{agora.year} {slot}", f"%Y {FORMATO_SLOT}")
    if data < agora - timedelta(days=60):  # virada de ano (ex.: agendamento em janeiro)
        data = data.replace(year=agora.year + 1)
    return data


def criar_exemplos() -> list:
    """Uma semana de exemplo, para o painel não aparecer vazio na demonstração."""
    clientes = [("Andre", "Skin Fade", 1, 10), ("Chris", "Beard Trim", 1, 11), ("Maria (son)", "Kids Cut", 1, 15),
                ("Kevin", "Haircut + Beard", 2, 9), ("Tyler", "Haircut", 2, 13), ("Omar", "Skin Fade", 3, 17)]
    exemplos, base = [], datetime.now().replace(minute=0, second=0, microsecond=0)
    for nome, servico, dias, hora in clientes:
        dia = base + timedelta(days=dias)
        if dia.weekday() == 6:
            dia += timedelta(days=1)
        exemplos.append({"service": servico, "slot": dia.replace(hour=hora).strftime(FORMATO_SLOT),
                         "customer_name": nome, "phone": "(305) 555-01" + str(10 + len(exemplos)),
                         "booked_at": "2:14 AM" if nome == "Kevin" else "earlier"})
    return exemplos


def carregar_agenda() -> list:
    if not ARQUIVO_AGENDA.exists():
        salvar_agenda(criar_exemplos())
    return json.loads(ARQUIVO_AGENDA.read_text(encoding="utf-8"))


def salvar_agenda(agenda: list) -> None:
    ARQUIVO_AGENDA.write_text(json.dumps(agenda, indent=2, ensure_ascii=False), encoding="utf-8")


def horarios_livres() -> list:
    """Horários dos próximos dias (seg-sáb, 9h-18h), sem os já ocupados."""
    ocupados = {a["slot"] for a in carregar_agenda()}
    livres = []
    dia = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    while len(livres) < 60:
        if dia.weekday() != 6:  # domingo fechado
            for hora in range(9, 19):
                slot = dia.replace(hour=hora).strftime(FORMATO_SLOT)
                if slot not in ocupados:
                    livres.append(slot)
        dia += timedelta(days=1)
    return livres


def lembretes(agendamento: dict) -> list:
    """Os SMS que o sistema manda para este cliente: (quando, para quê, texto)."""
    nome = agendamento["customer_name"].split()[0]
    servico = agendamento["service"]
    inicio = slot_para_data(agendamento["slot"])
    return [
        (inicio - timedelta(hours=24), "Reminder", "cuts no-shows",
         f"Hi {nome}! Reminder: your {servico} at Fresh Cuts is tomorrow at {hora(inicio)}. Reply C to cancel."),
        (inicio - timedelta(hours=2), "Heads-up", "keeps you on time",
         f"See you soon, {nome}! Your {servico} is in 2 hours. 120 Ocean Dr."),
        (inicio + timedelta(weeks=4), "Rebooking", "brings them back",
         f"Hey {nome}, it's been 4 weeks since your last {servico}. Want me to book your next one?"),
    ]


def loja_fechada(horario: str) -> bool:
    """True se o agendamento foi feito fora do horário da loja (9h-19h), ex.: '2:14 AM'."""
    try:
        hora = datetime.strptime(horario, "%I:%M %p").hour
    except ValueError:
        return False
    return hora < 9 or hora >= 19


# ---------------- Páginas ----------------

def pagina(nome_arquivo: str, conteudo: str = "") -> str:
    return (PASTA / nome_arquivo).read_text(encoding="utf-8").replace("{{CONTEUDO}}", conteudo)


def montar_painel() -> str:
    agenda = sorted(carregar_agenda(), key=lambda a: slot_para_data(a["slot"]))
    total = sum(SERVICOS.get(a["service"], {}).get("preco", 0) for a in agenda)
    fora_do_horario = sum(1 for a in agenda if loja_fechada(a.get("booked_at", "")))

    partes = [f"""
    <section class="numeros" aria-label="This week at a glance">
      <div><strong>{len(agenda)}</strong><span>appointments booked by your assistant</span></div>
      <div><strong>${total}</strong><span>in services on the calendar</span></div>
      <div><strong>{len(agenda) * 3}</strong><span>text messages scheduled, so you don't have to send them</span></div>
      <div><strong>{fora_do_horario}</strong><span>booked while the shop was closed</span></div>
    </section>"""]

    if not agenda:
        partes.append("<p class='vazio'>No appointments yet. Open your website and book a test appointment in the chat to see it appear here.</p>")

    dia_atual = None
    for a in agenda:
        inicio = slot_para_data(a["slot"])
        if inicio.date() != dia_atual:
            if dia_atual is not None:
                partes.append("</div>")
            dia_atual = inicio.date()
            partes.append(f"<h3 class='dia'>{inicio:%A, %B} {inicio.day}</h3><div class='lista'>")

        passos = []
        for quando, nome, motivo, texto in lembretes(a):
            estado = "sent" if quando < datetime.now() else "scheduled"
            passos.append(f"""<li class="{estado}"><b>{nome}</b> · {quando:%a %b} {quando.day}, {hora(quando)}
              <span class="motivo">{motivo}</span><q>{html.escape(texto)}</q></li>""")

        preco = SERVICOS.get(a["service"], {}).get("preco", "?")
        partes.append(f"""
        <article class="horario">
          <time>{hora(inicio)}</time>
          <div class="info">
            <b>{html.escape(a['customer_name'])}</b> · {html.escape(a['service'])} · ${preco}
            <span class="tel">{html.escape(a['phone'])}</span>
            <details><summary>What happens next with this client</summary><ol class="linha">{''.join(passos)}</ol></details>
          </div>
        </article>""")
    if dia_atual is not None:
        partes.append("</div>")
    return pagina("painel.html", "".join(partes))


# ---------------- Servidor ----------------

class Servidor(BaseHTTPRequestHandler):
    def do_GET(self):
        rotas = {"/painel": montar_painel, "/planos": lambda: pagina("planos.html")}
        self._enviar(rotas.get(self.path, lambda: pagina("site.html"))(), "text/html")

    def do_POST(self):  # /chat: o navegador manda a conversa, a IA responde
        tamanho = int(self.headers.get("Content-Length", 0))
        conversa = json.loads(self.rfile.read(tamanho))["conversa"]

        livres = horarios_livres()
        resultado = responder(conversa, livres)

        # Nunca confiamos cegamente na IA: só agenda se o horário existir e estiver livre
        if resultado["ready_to_book"] and resultado["slot"] in livres:
            agenda = carregar_agenda()
            novo = {k: resultado[k] for k in ["service", "slot", "customer_name", "phone"]}
            novo["booked_at"] = hora(datetime.now())
            agenda.append(novo)
            salvar_agenda(agenda)
            # Num produto real: aqui programaríamos os SMS de verdade (ex.: Twilio)
        elif resultado["ready_to_book"]:
            resultado["reply"] = "That slot was just taken. Pick another time and I'll book it."
            resultado["ready_to_book"] = False

        self._enviar(json.dumps(resultado), "application/json")

    def log_message(self, *args):  # deixa o terminal limpo
        pass

    def _enviar(self, conteudo: str, tipo: str):
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.end_headers()
        self.wfile.write(conteudo.encode("utf-8"))


if __name__ == "__main__":
    print("Abra no navegador: http://localhost:8000  (Ctrl+C para parar)")
    HTTPServer(("localhost", 8000), Servidor).serve_forever()
