"""
O "cérebro" da automação: recebe o pedido de orçamento e devolve uma análise.

Dois modos:
- MODO REAL: se a variável ANTHROPIC_API_KEY existir, pergunta ao Claude.
- MODO DEMO: sem chave, usa regras simples (palavras-chave). Serve para você
  rodar e mostrar a ideia sem gastar nada.
"""

import json
import os

import traducao as tr

# O "formulário" que a IA é obrigada a preencher (structured output).
# Assim o resto do programa sempre recebe os mesmos campos.
ESQUEMA = {
    "type": "object",
    "properties": {
        # hot = pronto para fechar; warm = interessado; cold = só pesquisando
        "lead_score": {"type": "string", "enum": ["hot", "warm", "cold"]},
        "project_type": {"type": "string"},
        "estimated_range": {"type": "string"},
        "summary": {"type": "string"},
        "questions_to_ask": {"type": "array", "items": {"type": "string"}},
        "reply_email": {"type": "string"},
    },
    "required": ["lead_score", "project_type", "estimated_range", "summary",
                 "questions_to_ask", "reply_email"],
    "additionalProperties": False,
}

INSTRUCOES = """You work for "Vertex Build", a residential contractor in Dallas, Texas
(kitchen and bathroom remodels, additions, roofing, decks, general repairs).
A homeowner just requested an estimate on the website. Analyze it and return:
- lead_score: "hot" (clear project, budget and timeline within ~3 months),
  "warm" (real project but vague or later), or "cold" (just browsing, tiny job, or unclear).
- project_type: short name of the project, in English.
- estimated_range: a realistic Dallas-area price range, e.g. "$25,000 - $45,000".
- summary: one plain-English sentence for the business owner explaining the project
  and why you gave that lead_score.
- questions_to_ask: 2-3 short questions (in English) the contractor should ask on the call.
- reply_email: a warm, professional email to the homeowner, in English, signed
  "Vertex Build Team". Thank them, show you understood their project, and
  invite them to book a free on-site estimate at (214) 555-0182.
  Never promise an exact price or a start date."""


def analisar_pedido(pedido: dict) -> dict:
    """Função principal: escolhe o modo e devolve a análise como dicionário."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        resultado = _modo_demo(pedido)
        resultado["modo"] = "demo"
        return resultado

    resultado = _modo_real(pedido)
    resultado["modo"] = "ia"
    return resultado


def _modo_real(pedido: dict) -> dict:
    import anthropic  # só importa se for usar; o modo demo não precisa instalar nada

    texto_pedido = (
        f"Name: {pedido['nome']}\nProject type: {pedido['tipo']}\n"
        f"Budget: {pedido['orcamento']}\nTimeline: {pedido['prazo']}\n\n"
        f"Details:\n{pedido['mensagem']}"
    )
    client = anthropic.Anthropic()  # lê a ANTHROPIC_API_KEY automaticamente
    resposta = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        system=INSTRUCOES,
        messages=[{"role": "user", "content": texto_pedido}],
        # effort "low": tarefa simples = mais rápido e barato
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
        # Se o modelo recusar o pedido, a API tenta automaticamente outro modelo
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )

    if resposta.stop_reason == "refusal":
        return _modo_demo(pedido)

    texto = next(bloco.text for bloco in resposta.content if bloco.type == "text")
    return json.loads(texto)


# Faixas de preço aproximadas, só para o modo demo
PRECOS = {
    "Kitchen remodel": "$25,000 - $60,000",
    "Bathroom remodel": "$12,000 - $35,000",
    "Roofing": "$9,000 - $22,000",
    "Deck / patio": "$8,000 - $25,000",
    "Home addition": "$60,000 - $150,000",
    "Repairs / other": "$500 - $5,000",
}


def _modo_demo(pedido: dict) -> dict:
    """Imitação simples da IA, com regras fixas. Bem pior, mas funciona sem chave."""
    tipo = pedido["tipo"]
    pontos = 0
    if pedido["orcamento"] not in ("Not sure", ""):
        pontos += 1
    if pedido["prazo"] in ("ASAP", "1-3 months"):
        pontos += 1
    if len(pedido["mensagem"]) > 80:  # quem explica bem o projeto costuma estar mais decidido
        pontos += 1
    score = "hot" if pontos == 3 else "warm" if pontos >= 1 else "cold"

    primeiro_nome = pedido["nome"].split()[0] if pedido["nome"].strip() else tr.t("there", "tudo bem")
    if tr.EM_PT:
        return _modo_demo_pt(pedido, score, primeiro_nome)
    email = (
        f"Hi {primeiro_nome},\n\n"
        f"Thank you for contacting Vertex Build about your {tipo.lower()} project! "
        f"We'd love to help bring it to life.\n\n"
        f"The next step is a free on-site estimate. Call us at (214) 555-0182 or reply "
        f"to this email with a couple of times that work for you.\n\n"
        f"Best regards,\nVertex Build Team"
    )
    return {
        "lead_score": score,
        "project_type": tipo,
        "estimated_range": PRECOS.get(tipo, "$1,000 - $10,000"),
        "summary": (f"{tipo} with a budget of {pedido['orcamento']} and a start of "
                    f"'{pedido['prazo']}'. Scored {score} from budget, timeline and detail given."),
        "questions_to_ask": [
            "What's the approximate size of the area?",
            "Do you already have a design or materials in mind?",
        ],
        "reply_email": email,
    }


def _modo_demo_pt(pedido: dict, score: str, primeiro_nome: str) -> dict:
    """Mesma análise do modo demo, escrita em português (vídeos em PT)."""
    tipo = tr.frase(pedido["tipo"])
    nivel = {"hot": "quente", "warm": "morno", "cold": "frio"}[score]
    email = (
        f"Olá, {primeiro_nome}!\n\n"
        f"Obrigado por falar com a Vertex Build sobre o seu projeto de {tipo.lower()}! "
        f"Vamos adorar tirar essa ideia do papel.\n\n"
        f"O próximo passo é um orçamento grátis no local. Ligue para (214) 555-0182 ou responda "
        f"este e-mail com dois ou três horários que funcionem pra você.\n\n"
        f"Um abraço,\nEquipe Vertex Build"
    )
    return {
        "lead_score": score,
        "project_type": tipo,
        "estimated_range": PRECOS.get(pedido["tipo"], "$1,000 - $10,000"),
        "summary": (f"{tipo} com orçamento de {tr.frase(pedido['orcamento'])} e início em "
                    f"'{tr.frase(pedido['prazo'])}'. Classificado como {nivel} pelo orçamento, prazo e detalhes."),
        "questions_to_ask": [
            "Qual é o tamanho aproximado da área?",
            "Você já tem um projeto ou materiais em mente?",
        ],
        "reply_email": email,
    }
