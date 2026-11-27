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

import traducao as tr
from ia import ABRE, FECHA, SERVICOS, primeiro_dia_util, responder

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
    # Amanhã às 15h já está ocupado (corte + barba, 1h): é o horário que a demo pede no chat
    clientes = [("Andre", "Haircut", 1, 10), ("Chris", "Beard Trim", 1, 11), ("Maria", "Haircut", 1, 14),
                ("Kevin", "Haircut + Beard", 1, 15), ("Tyler", "Haircut", 2, 13), ("Omar", "Haircut + Beard", 3, 17)]
    exemplos = []
    amanha = primeiro_dia_util(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
    for nome, servico, dias, hora in clientes:
        dia = primeiro_dia_util(amanha + timedelta(days=dias - 1))
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


def blocos_ocupados() -> set:
    """Cada agendamento ocupa blocos de 30 min conforme a duração do serviço (corte + barba = 2 blocos)."""
    ocupados = set()
    for a in carregar_agenda():
        inicio = slot_para_data(a["slot"])
        for minuto in range(0, SERVICOS.get(a["service"], {}).get("minutos", 30), 30):
            ocupados.add(inicio + timedelta(minutes=minuto))
    return ocupados


def horarios_livres(minutos: int = 30, dias: int = 7) -> list:
    """Horários de início livres nos próximos dias úteis (seg-sáb, 9h-19h) para um serviço de N minutos."""
    ocupados = blocos_ocupados()
    livres = []
    dia = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    for _ in range(dias):
        if dia.weekday() != 6:  # domingo fechado
            inicio = dia.replace(hour=ABRE)
            while inicio + timedelta(minutes=minutos) <= dia.replace(hour=FECHA):
                blocos = [inicio + timedelta(minutes=m) for m in range(0, minutos, 30)]
                if not any(b in ocupados for b in blocos):
                    livres.append(inicio.strftime(FORMATO_SLOT))
                inicio += timedelta(minutes=30)
        dia += timedelta(days=1)
    return livres


def livres_por_servico() -> dict:
    return {nome: horarios_livres(s["minutos"]) for nome, s in SERVICOS.items()}


def lembretes(agendamento: dict) -> list:
    """Os SMS que o sistema manda para este cliente: (quando, para quê, texto)."""
    nome = agendamento["customer_name"].split()[0]
    servico = tr.servico(agendamento["service"])
    inicio = slot_para_data(agendamento["slot"])
    return [
        (inicio - timedelta(hours=24), tr.t("Reminder", "Lembrete"), tr.t("cuts no-shows", "evita faltas"),
         tr.t(f"Hi {nome}! Reminder: your {servico} at Black Crown is tomorrow at {tr.hora(inicio)}. Reply C to cancel.",
              f"Oi, {nome}! Lembrete: seu {servico.lower()} na Black Crown é amanhã às {tr.hora(inicio)}. Responda C para cancelar.")),
        (inicio - timedelta(hours=2), tr.t("Heads-up", "Aviso"), tr.t("keeps you on time", "garante a pontualidade"),
         tr.t(f"See you soon, {nome}! Your {servico} is in 2 hours. 120 Ocean Dr.",
              f"Até já, {nome}! Seu {servico.lower()} é daqui a 2 horas. 120 Ocean Dr.")),
        (inicio + timedelta(weeks=4), tr.t("Rebooking", "Retorno"), tr.t("brings them back", "traz o cliente de volta"),
         tr.t(f"Hey {nome}, it's been 4 weeks since your last {servico}. Want me to book your next one?",
              f"E aí, {nome}? Já faz 4 semanas do seu último {servico.lower()}. Quer que eu marque o próximo?")),
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
    return tr.pagina((PASTA / nome_arquivo).read_text(encoding="utf-8")).replace("{{CONTEUDO}}", conteudo)


def montar_painel() -> str:
    agenda = sorted(carregar_agenda(), key=lambda a: slot_para_data(a["slot"]))
    total = sum(tr.preco(a["service"], SERVICOS.get(a["service"], {}).get("preco", 0)) for a in agenda)
    fora_do_horario = sum(1 for a in agenda if loja_fechada(a.get("booked_at", "")))

    partes = [f"""
    <section class="numeros" aria-label="{tr.t('This week at a glance', 'Resumo da semana')}">
      <div><strong>{len(agenda)}</strong><span>{tr.t('appointments booked by your assistant', 'horários marcados pelo seu assistente')}</span></div>
      <div><strong>{tr.moeda(total)}</strong><span>{tr.t('in services on the calendar', 'em serviços na agenda')}</span></div>
      <div><strong>{len(agenda) * 3}</strong><span>{tr.t("text messages scheduled, so you don't have to send them", 'mensagens programadas, que você não precisa mandar')}</span></div>
      <div><strong>{fora_do_horario}</strong><span>{tr.t('booked while the shop was closed', 'marcados com a barbearia fechada')}</span></div>
    </section>"""]

    if not agenda:
        partes.append("<p class='vazio'>" + tr.t("No appointments yet. Open your website and book a test appointment in the chat to see it appear here.", "Nenhum horário ainda. Abra o seu site e marque um horário de teste no chat para ver ele aparecer aqui.") + "</p>")

    dia_atual = None
    for a in agenda:
        inicio = slot_para_data(a["slot"])
        if inicio.date() != dia_atual:
            if dia_atual is not None:
                partes.append("</div>")
            dia_atual = inicio.date()
            partes.append(f"<h3 class='dia'>{tr.dia(inicio)}</h3><div class='lista'>")

        passos = []
        for quando, nome, motivo, texto in lembretes(a):
            estado = "sent" if quando < datetime.now() else "scheduled"
            passos.append(f"""<li class="{estado}"><b>{nome}</b> · {tr.dia(quando, curto=True)}, {tr.hora(quando)}
              <span class="motivo">{motivo}</span><q>{html.escape(texto)}</q></li>""")

        preco = tr.moeda(tr.preco(a["service"], SERVICOS.get(a["service"], {}).get("preco", 0)))
        partes.append(f"""
        <article class="horario">
          <time>{tr.hora(inicio)}</time>
          <div class="info">
            <b>{html.escape(a['customer_name'])}</b> · {html.escape(tr.servico(a['service']))} · {preco}
            <span class="tel">{html.escape(tr.telefone(a['phone']))}</span>
            <details><summary>{tr.t('What happens next with this client', 'O que acontece agora com este cliente')}</summary><ol class="linha">{''.join(passos)}</ol></details>
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

        livres = livres_por_servico()
        resultado = responder(conversa, livres)

        # Nunca confiamos cegamente na IA: só agenda se o horário existir e estiver livre para esse serviço
        if resultado["ready_to_book"] and resultado["slot"] in livres.get(resultado["service"], []):
            agenda = carregar_agenda()
            novo = {k: resultado[k] for k in ["service", "slot", "customer_name", "phone"]}
            novo["booked_at"] = hora(datetime.now())
            agenda.append(novo)
            salvar_agenda(agenda)
            # Num produto real: aqui programaríamos os SMS de verdade (ex.: Twilio)
        elif resultado["ready_to_book"]:
            resultado["reply"] = tr.t("That slot was just taken. Pick another time and I'll book it.",
                                      "Esse horário acabou de ser ocupado. Escolha outro que eu marco pra você.")
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
