"""
Lead responder com IA para empreiteiros (cliente fictício: Summit Build & Remodel, Dallas).

- http://localhost:8000/          -> site da empresa, com o pedido de orçamento
- http://localhost:8000/obrigado  -> o que o cliente vê depois de enviar (o e-mail que recebeu)
- http://localhost:8000/painel    -> painel da dona: leads separados por prioridade, explicados
"""

import html
import json
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from ia import analisar_pedido

PASTA = Path(__file__).parent
ARQUIVO_PEDIDOS = PASTA / "pedidos.json"  # nosso "banco de dados" simples
CAMPOS = ["nome", "email", "telefone", "tipo", "orcamento", "prazo", "mensagem"]

# Cada nível de lead vira uma ação clara para a dona
GRUPOS = [
    ("hot", "Call today", "Clear project, real budget, wants to start soon. These are the jobs you win by calling first."),
    ("warm", "Call this week", "A real project, but the budget or timeline is still open. A friendly call keeps you in the running."),
    ("cold", "Keep in touch", "Still exploring. They already got a reply; a follow-up email in a few weeks is enough for now."),
]


# ---------------- Dados ----------------

def carregar_pedidos() -> list:
    if not ARQUIVO_PEDIDOS.exists():
        criar_exemplos()
    return json.loads(ARQUIVO_PEDIDOS.read_text(encoding="utf-8"))


def salvar_pedidos(pedidos: list) -> None:
    ARQUIVO_PEDIDOS.write_text(json.dumps(pedidos, indent=2, ensure_ascii=False), encoding="utf-8")


def criar_exemplos() -> None:
    """Leads de exemplo, para o painel não aparecer vazio na demonstração."""
    salvar_pedidos([])
    exemplos = [
        ("Mike Johnson", "(214) 555-0133", "Deck / patio", "Not sure", "Just exploring", "Thinking about a deck someday.", "9:12 PM"),
        ("David Kim", "(214) 555-0177", "Bathroom remodel", "$10k - $30k", "3-6 months",
         "Master bathroom: replace the tub with a walk-in shower and a new double vanity.", "6:40 AM"),
        ("Emily Carter", "(214) 555-0101", "Kitchen remodel", "$30k - $75k", "1-3 months",
         "We want to fully remodel our 1990s kitchen: new cabinets, quartz countertops, an island and new lighting.", "11:58 PM"),
    ]
    for nome, tel, tipo, orc, prazo, msg, hora in exemplos:
        registrar({"nome": nome, "email": "homeowner@example.com", "telefone": tel, "tipo": tipo,
                   "orcamento": orc, "prazo": prazo, "mensagem": msg}, hora)


def registrar(pedido: dict, hora: str | None = None) -> None:
    inicio = time.time()
    pedido["analise"] = analisar_pedido(pedido)  # <- aqui a IA trabalha
    pedido["segundos"] = max(1, round(time.time() - inicio))
    pedido["quando"] = hora or datetime.now().strftime("%-I:%M %p")
    pedidos = json.loads(ARQUIVO_PEDIDOS.read_text(encoding="utf-8")) if ARQUIVO_PEDIDOS.exists() else []
    pedidos.insert(0, pedido)
    salvar_pedidos(pedidos)
    # Num produto real: aqui o e-mail seria enviado de verdade (Gmail/SendGrid)
    # e a dona receberia um SMS para cada lead "hot" (Twilio).


# ---------------- Páginas ----------------

def pagina(nome_arquivo: str, conteudo: str = "") -> str:
    return (PASTA / nome_arquivo).read_text(encoding="utf-8").replace("{{CONTEUDO}}", conteudo)


def cartao(p: dict) -> str:
    a = p["analise"]
    perguntas = "".join(f"<li>{html.escape(q)}</li>" for q in a["questions_to_ask"])
    return f"""
    <article class="lead">
      <div class="lead-topo">
        <div><b>{html.escape(p['nome'])}</b><span>{html.escape(a['project_type'])}</span></div>
        <a class="ligar" href="tel:{html.escape(p['telefone'])}">Call {html.escape(p['telefone'])}</a>
      </div>
      <p class="resumo">{html.escape(a['summary'])}</p>
      <dl>
        <div><dt>Likely job size</dt><dd>{html.escape(a['estimated_range'])}</dd></div>
        <div><dt>Their budget</dt><dd>{html.escape(p['orcamento'])}</dd></div>
        <div><dt>Wants to start</dt><dd>{html.escape(p['prazo'])}</dd></div>
        <div><dt>Came in</dt><dd>{html.escape(p['quando'])}, answered in {p['segundos']}s</dd></div>
      </dl>
      <details><summary>Questions to ask on the call</summary><ul>{perguntas}</ul></details>
      <details><summary>The email they already received</summary><pre>{html.escape(a['reply_email'])}</pre></details>
    </article>"""


def montar_painel() -> str:
    pedidos = carregar_pedidos()
    partes = []
    for nivel, titulo, explicacao in GRUPOS:
        do_grupo = [p for p in pedidos if p["analise"]["lead_score"] == nivel]
        corpo = "".join(cartao(p) for p in do_grupo) or "<p class='nada'>Nothing here right now.</p>"
        partes.append(f"""
        <section class="grupo {nivel}">
          <h2>{titulo} <span class="conta">{len(do_grupo)}</span></h2>
          <p class="explica">{explicacao}</p>
          {corpo}
        </section>""")
    return pagina("painel.html", "".join(partes))


def montar_obrigado() -> str:
    pedidos = carregar_pedidos()
    email = pedidos[0]["analise"]["reply_email"] if pedidos else ""
    return pagina("obrigado.html", html.escape(email))


# ---------------- Servidor ----------------

class Servidor(BaseHTTPRequestHandler):
    def do_GET(self):
        rotas = {"/painel": montar_painel, "/obrigado": montar_obrigado}
        self._responder(rotas.get(self.path, lambda: pagina("site.html"))())

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        campos = parse_qs(self.rfile.read(tamanho).decode("utf-8"))
        carregar_pedidos()  # garante que o arquivo existe
        registrar({k: campos.get(k, [""])[0] for k in CAMPOS})
        self.send_response(303)
        self.send_header("Location", "/obrigado")
        self.end_headers()

    def log_message(self, *args):  # deixa o terminal limpo
        pass

    def _responder(self, conteudo: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(conteudo.encode("utf-8"))


if __name__ == "__main__":
    print("Abra no navegador: http://localhost:8000  (Ctrl+C para parar)")
    HTTPServer(("localhost", 8000), Servidor).serve_forever()
