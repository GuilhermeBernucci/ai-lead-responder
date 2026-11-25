"""
O "servidor": um mini site que roda no seu computador.

- http://localhost:8000/        -> página que o CLIENTE vê (pedido de orçamento)
- http://localhost:8000/painel  -> painel que o DONO vê (pedidos analisados pela IA)

Usa só bibliotecas que já vêm com o Python. Num produto real, usaríamos um
framework (Flask/FastAPI) e um banco de dados de verdade.
"""

import html
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from ia import analisar_pedido

PASTA = Path(__file__).parent
ARQUIVO_PEDIDOS = PASTA / "pedidos.json"  # nosso "banco de dados" simples
CORES = {"hot": "#d92d20", "warm": "#f79009", "cold": "#667085"}
ORDEM = {"hot": 0, "warm": 1, "cold": 2}  # quentes primeiro no painel


def carregar_pedidos() -> list:
    if ARQUIVO_PEDIDOS.exists():
        return json.loads(ARQUIVO_PEDIDOS.read_text(encoding="utf-8"))
    return []


def salvar_pedido(pedido: dict) -> None:
    pedidos = carregar_pedidos()
    pedidos.insert(0, pedido)
    ARQUIVO_PEDIDOS.write_text(json.dumps(pedidos, indent=2, ensure_ascii=False), encoding="utf-8")


def montar_painel() -> str:
    pedidos = sorted(carregar_pedidos(), key=lambda p: ORDEM.get(p["analise"]["lead_score"], 9))
    cartoes = []
    for p in pedidos:
        a = p["analise"]
        cor = CORES.get(a["lead_score"], "#667085")
        perguntas = "".join(f"<li>{html.escape(q)}</li>" for q in a["questions_to_ask"])
        cartoes.append(f"""
        <div class="card">
          <div class="topo">
            <span class="tag" style="background:{cor}">{a['lead_score'].upper()} LEAD</span>
            <b>{html.escape(p['nome'])}</b> · {html.escape(p['telefone'])} · {p['quando']}
          </div>
          <p><b>Resumo:</b> {html.escape(a['summary_pt'])}</p>
          <p><b>Projeto:</b> {html.escape(a['project_type'])} · <b>Faixa de preço:</b> {html.escape(a['estimated_range'])}</p>
          <p><b>Perguntar na ligação:</b></p><ul>{perguntas}</ul>
          <details><summary>E-mail enviado ao cliente (modo: {a.get('modo')})</summary>
            <pre>{html.escape(a['reply_email'])}</pre></details>
        </div>""")
    lista = "".join(cartoes) or "<p>Nenhum pedido ainda. Envie um pela página do cliente.</p>"
    modelo = (PASTA / "pagina.html").read_text(encoding="utf-8")
    return modelo.replace("{{CONTEUDO}}", f"<h1>Painel do dono</h1><a href='/'>← página do cliente</a>{lista}")


class Servidor(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/painel":
            self._responder(montar_painel())
        else:
            self._responder((PASTA / "formulario.html").read_text(encoding="utf-8"))

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        campos = parse_qs(self.rfile.read(tamanho).decode("utf-8"))
        pedido = {k: campos.get(k, [""])[0]
                  for k in ["nome", "email", "telefone", "tipo", "orcamento", "prazo", "mensagem"]}

        pedido["analise"] = analisar_pedido(pedido)  # <- aqui a IA trabalha
        pedido["quando"] = datetime.now().strftime("%d/%m %H:%M")
        salvar_pedido(pedido)
        # Num produto real, aqui o e-mail seria enviado de verdade (ex.: Gmail, SendGrid)
        # e o dono receberia um SMS para cada lead "hot".

        self.send_response(303)  # redireciona para o painel
        self.send_header("Location", "/painel")
        self.end_headers()

    def _responder(self, conteudo: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(conteudo.encode("utf-8"))


if __name__ == "__main__":
    print("Abra no navegador: http://localhost:8000  (Ctrl+C para parar)")
    HTTPServer(("localhost", 8000), Servidor).serve_forever()
