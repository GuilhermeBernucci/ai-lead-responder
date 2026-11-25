"""
Kit de agendamento com IA para barbearias e salões.

- http://localhost:8000/        -> site da barbearia com o chat que agenda (o que o CLIENTE vê)
- http://localhost:8000/painel  -> agenda do dono + lembretes automáticos programados
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


def carregar_agenda() -> list:
    if ARQUIVO_AGENDA.exists():
        return json.loads(ARQUIVO_AGENDA.read_text(encoding="utf-8"))
    return []


def horarios_livres() -> list:
    """Gera os horários dos próximos 6 dias (seg-sáb, 9h-18h) e tira os já ocupados."""
    ocupados = {a["slot"] for a in carregar_agenda()}
    livres = []
    dia = datetime.now() + timedelta(days=1)
    while len(livres) < 60:
        if dia.weekday() != 6:  # domingo fechado
            for hora in range(9, 19):
                slot = f"{dia.strftime('%A %b %d')} {hora:02d}:00"
                if slot not in ocupados:
                    livres.append(slot)
        dia += timedelta(days=1)
    return livres


def lembretes(agendamento: dict) -> list:
    """Os lembretes que o sistema mandaria por SMS para este cliente."""
    nome, servico, slot = agendamento["customer_name"], agendamento["service"], agendamento["slot"]
    return [
        ("24h antes", f"Hi {nome}! Reminder: your {servico} at Fresh Cuts is tomorrow ({slot}). Reply C to cancel."),
        ("2h antes", f"See you soon, {nome}! Your {servico} is in 2 hours. 120 Ocean Dr."),
        ("4 semanas depois", f"Hey {nome}, it's been 4 weeks since your last {servico}. Want me to book your next one? 💈"),
    ]


def pagina(nome_arquivo: str, conteudo: str = "") -> str:
    return (PASTA / nome_arquivo).read_text(encoding="utf-8").replace("{{CONTEUDO}}", conteudo)


def montar_painel() -> str:
    agenda = carregar_agenda()
    faturamento = sum(SERVICOS[a["service"]]["preco"] for a in agenda if a["service"] in SERVICOS)
    cartoes = [f"<p class='resumo'>📅 <b>{len(agenda)}</b> agendamentos feitos pela IA · "
               f"💵 <b>${faturamento}</b> em serviços</p>"]
    for a in agenda:
        sms = "".join(f"<li><b>{q}:</b> {html.escape(t)}</li>" for q, t in lembretes(a))
        cartoes.append(f"""
        <div class="card">
          <b>{html.escape(a['slot'])}</b> · {html.escape(a['service'])}
          (${SERVICOS.get(a['service'], {}).get('preco', '?')})<br>
          {html.escape(a['customer_name'])} · {html.escape(a['phone'])}
          <details><summary>Lembretes automáticos programados (SMS)</summary><ul>{sms}</ul></details>
        </div>""")
    if not agenda:
        cartoes.append("<p>Nenhum agendamento ainda. Converse com o chat no site.</p>")
    return pagina("painel.html", "".join(cartoes))


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
            agenda.append({k: resultado[k] for k in ["service", "slot", "customer_name", "phone"]})
            ARQUIVO_AGENDA.write_text(json.dumps(agenda, indent=2, ensure_ascii=False), encoding="utf-8")
            # Num produto real: aqui programaríamos os SMS de verdade (ex.: Twilio)
        elif resultado["ready_to_book"]:
            resultado["reply"] = "Sorry, that slot was just taken! Could you pick another time?"
            resultado["ready_to_book"] = False

        self._enviar(json.dumps(resultado), "application/json")

    def _enviar(self, conteudo: str, tipo: str):
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.end_headers()
        self.wfile.write(conteudo.encode("utf-8"))


if __name__ == "__main__":
    print("Abra no navegador: http://localhost:8000  (Ctrl+C para parar)")
    HTTPServer(("localhost", 8000), Servidor).serve_forever()
