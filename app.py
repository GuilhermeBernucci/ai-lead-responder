"""
O "servidor": um mini site que roda no seu computador.

- http://localhost:8000/        -> página que o CLIENTE vê (formulário de orçamento)
- http://localhost:8000/painel  -> painel que o DONO vê (pedidos analisados pela IA)

Usa só bibliotecas que já vêm com o Python, para você não precisar instalar nada
para testar. Num produto real, usaríamos um framework (Flask/FastAPI) e um banco
de dados de verdade.
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
CORES = {"emergency": "#d92d20", "high": "#f79009", "normal": "#12b76a"}


def carregar_pedidos() -> list:
    if ARQUIVO_PEDIDOS.exists():
        return json.loads(ARQUIVO_PEDIDOS.read_text(encoding="utf-8"))
    return []


def salvar_pedido(pedido: dict) -> None:
    pedidos = carregar_pedidos()
    pedidos.insert(0, pedido)  # o mais novo primeiro
    ARQUIVO_PEDIDOS.write_text(json.dumps(pedidos, indent=2, ensure_ascii=False), encoding="utf-8")


def montar_painel() -> str:
    cartoes = []
    for p in carregar_pedidos():
        a = p["analise"]
        cor = CORES.get(a["urgency"], "#667085")
        cartoes.append(f"""
        <div class="card">
          <div class="topo">
            <span class="tag" style="background:{cor}">{a['urgency'].upper()}</span>
            <b>{html.escape(p['nome'])}</b> · {html.escape(p['email'])} · {p['quando']}
          </div>
          <p><b>Resumo:</b> {html.escape(a['summary_pt'])}</p>
          <p><b>Serviço:</b> {html.escape(a['service_type'])} · <b>Preço estimado:</b> {html.escape(a['estimated_price'])}</p>
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
        nome = campos.get("nome", [""])[0]
        email = campos.get("email", [""])[0]
        mensagem = campos.get("mensagem", [""])[0]

        analise = analisar_pedido(nome, mensagem)  # <- aqui a IA trabalha
        salvar_pedido({
            "nome": nome, "email": email, "mensagem": mensagem,
            "quando": datetime.now().strftime("%d/%m %H:%M"), "analise": analise,
        })
        # Num produto real, aqui o e-mail seria enviado de verdade (ex.: Gmail, SendGrid)
        # e o dono receberia um SMS se a urgência fosse "emergency".

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
