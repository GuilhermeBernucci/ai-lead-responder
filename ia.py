"""
O "cérebro" da automação: recebe o pedido do cliente e devolve uma análise.

Dois modos:
- MODO REAL: se a variável ANTHROPIC_API_KEY existir, pergunta ao Claude.
- MODO DEMO: sem chave, usa regras simples (palavras-chave). Serve para você
  rodar e mostrar a ideia sem gastar nada.
"""

import json
import os

# O "formulário" que a IA é obrigada a preencher. Pedir JSON com um esquema
# fixo (structured output) garante que o resto do programa sempre recebe os
# mesmos campos, em vez de um texto solto difícil de usar.
ESQUEMA = {
    "type": "object",
    "properties": {
        "urgency": {"type": "string", "enum": ["emergency", "high", "normal"]},
        "service_type": {"type": "string"},
        "summary_pt": {"type": "string"},
        "estimated_price": {"type": "string"},
        "reply_email": {"type": "string"},
    },
    "required": ["urgency", "service_type", "summary_pt", "estimated_price", "reply_email"],
    "additionalProperties": False,
}

INSTRUCOES = """You work for "Rapid Flow Plumbing", a small plumbing company in Austin, Texas.
A potential customer just sent a request through the website. Analyze it and return:
- urgency: "emergency" (active leak, flooding, no water, sewage backup, gas smell),
  "high" (needs service within 1-2 days), or "normal".
- service_type: short name of the service, in English.
- summary_pt: one-sentence summary IN BRAZILIAN PORTUGUESE for the business owner.
- estimated_price: a realistic US price range for this service, e.g. "$150 - $350".
- reply_email: a warm, professional reply email to the customer, in English, signed
  "Rapid Flow Plumbing Team". For emergencies, tell them to call (512) 555-0147 now.
  Never promise an exact price or a specific arrival time."""


def analisar_pedido(nome: str, mensagem: str) -> dict:
    """Função principal: escolhe o modo e devolve a análise como dicionário."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        resultado = _modo_demo(nome, mensagem)
        resultado["modo"] = "demo"
        return resultado

    resultado = _modo_real(nome, mensagem)
    resultado["modo"] = "ia"
    return resultado


def _modo_real(nome: str, mensagem: str) -> dict:
    import anthropic  # só importa se for usar; o modo demo não precisa instalar nada

    client = anthropic.Anthropic()  # lê a ANTHROPIC_API_KEY automaticamente
    resposta = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        system=INSTRUCOES,
        messages=[{"role": "user", "content": f"Customer name: {nome}\n\nRequest:\n{mensagem}"}],
        # effort "low": tarefa simples, então pedimos menos "pensamento" = mais rápido e barato
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
        # Se o modelo recusar o pedido, a API tenta automaticamente outro modelo
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )

    if resposta.stop_reason == "refusal":
        return _modo_demo(nome, mensagem)

    texto = next(bloco.text for bloco in resposta.content if bloco.type == "text")
    return json.loads(texto)


def _modo_demo(nome: str, mensagem: str) -> dict:
    """Imitação simples da IA, só com palavras-chave. Bem pior, mas funciona sem chave."""
    texto = mensagem.lower()
    primeiro_nome = nome.split()[0] if nome.strip() else "there"

    if any(p in texto for p in ["flood", "burst", "leaking everywhere", "no water", "sewage", "gas"]):
        urgencia, servico, preco = "emergency", "Emergency leak repair", "$250 - $600"
    elif any(p in texto for p in ["water heater", "no hot water", "clog", "toilet"]):
        urgencia, servico, preco = "high", "Repair service", "$150 - $400"
    else:
        urgencia, servico, preco = "normal", "General plumbing service", "$100 - $300"

    extra = (
        "Since this sounds like an emergency, please call us right now at (512) 555-0147 "
        "and, if you can, shut off the main water valve.\n\n"
        if urgencia == "emergency"
        else ""
    )
    email = (
        f"Hi {primeiro_nome},\n\n"
        f"Thank you for reaching out to Rapid Flow Plumbing! We received your request "
        f"and a technician will contact you shortly to schedule a visit.\n\n"
        f"{extra}"
        f"Best regards,\nRapid Flow Plumbing Team"
    )
    return {
        "urgency": urgencia,
        "service_type": servico,
        "summary_pt": f"{nome} pediu: {mensagem[:90]}",
        "estimated_price": preco,
        "reply_email": email,
    }
