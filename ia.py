"""
O "cérebro" do assistente de agendamento.

A cada mensagem do cliente, a IA recebe:
  - a conversa até agora
  - os serviços da barbearia
  - os horários livres
e devolve um "formulário" (JSON) com a resposta e, quando tiver tudo, o agendamento.

Dois modos:
- MODO REAL: com a variável ANTHROPIC_API_KEY, quem conversa é o Claude.
- MODO DEMO: sem chave, regras simples de palavras-chave (para testar de graça).
"""

import json
import os
import re

SERVICOS = {
    "Haircut": {"preco": 35, "minutos": 30},
    "Skin Fade": {"preco": 40, "minutos": 45},
    "Beard Trim": {"preco": 20, "minutos": 20},
    "Haircut + Beard": {"preco": 50, "minutos": 60},
    "Kids Cut": {"preco": 25, "minutos": 30},
}

# A IA sempre devolve estes campos. Campo vazio ("") = ainda não sabemos.
ESQUEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "ready_to_book": {"type": "boolean"},
        "service": {"type": "string"},
        "slot": {"type": "string"},
        "customer_name": {"type": "string"},
        "phone": {"type": "string"},
    },
    "required": ["reply", "ready_to_book", "service", "slot", "customer_name", "phone"],
    "additionalProperties": False,
}

INSTRUCOES = """You are the friendly booking assistant of "Fresh Cuts Barbershop" in Miami, FL.
Chat with the customer by text, in a short, casual, friendly tone (1-3 sentences).
Your goal: book an appointment. You need 4 things: service, time slot, name and phone.

Services (name: price):
{servicos}

Available slots (ONLY offer these, copy them exactly in the "slot" field):
{horarios}

Rules:
- If the customer asks for a time that is not available, offer the 2-3 closest available slots.
- Fill each field with what you know so far; use "" for unknown fields.
- Set ready_to_book to true only when you have all 4 things and the customer agreed.
  In that case, the reply must confirm the appointment and say they'll get a text reminder.
- Answer questions about prices and services. Address: 120 Ocean Dr, Miami."""


def responder(conversa: list, horarios_livres: list) -> dict:
    """conversa = [{"role": "user"/"assistant", "content": "..."}]"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _modo_real(conversa, horarios_livres)
    return _modo_demo(conversa, horarios_livres)


def _modo_real(conversa: list, horarios_livres: list) -> dict:
    import anthropic

    servicos = "\n".join(f"- {n}: ${s['preco']}" for n, s in SERVICOS.items())
    client = anthropic.Anthropic()
    resposta = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        system=INSTRUCOES.format(servicos=servicos, horarios="\n".join(horarios_livres[:30])),
        messages=conversa,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resposta.stop_reason == "refusal":
        return _modo_demo(conversa, horarios_livres)
    texto = next(b.text for b in resposta.content if b.type == "text")
    return json.loads(texto)


# ---------------- MODO DEMO (regras simples) ----------------

PALAVRAS_SERVICO = [  # a ordem importa: o mais específico primeiro
    ("Haircut + Beard", ["cut and beard", "haircut and beard", "cut + beard", "both"]),
    ("Skin Fade", ["fade"]),
    ("Beard Trim", ["beard"]),
    ("Kids Cut", ["kid", "son", "child"]),
    ("Haircut", ["haircut", "cut", "trim"]),
]
DIAS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _modo_demo(conversa: list, horarios_livres: list) -> dict:
    # Junta tudo que o cliente já disse e procura as informações
    falas = [m["content"] for m in conversa if m["role"] == "user"]
    texto = " ".join(falas).lower()

    servico = next((nome for nome, palavras in PALAVRAS_SERVICO
                    if any(p in texto for p in palavras)), "")

    # Horário: procura dia da semana e hora (ex.: "friday 3pm")
    dia = next((d for d in DIAS if d in texto), "")
    if "tomorrow" in texto and horarios_livres:
        dia = horarios_livres[0].split()[0].lower()  # simplificação para a demo
    hora = re.search(r"\b(\d{1,2})\s*(am|pm)\b", texto)
    slot = ""
    candidatos = [h for h in horarios_livres if not dia or h.lower().startswith(dia)]
    if hora:
        h = int(hora.group(1)) % 12 + (12 if hora.group(2) == "pm" else 0)
        alvo = f"{h:02d}:00"
        slot = next((c for c in candidatos if alvo in c), "")

    nome_match = re.search(r"(?:my name is|i'm|i am|name:)\s+([a-z]+)", texto)
    nome = nome_match.group(1).title() if nome_match else ""
    tel_match = re.search(r"(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", texto)
    telefone = tel_match.group(1) if tel_match else ""

    if not servico:
        lista = ", ".join(f"{n} (${s['preco']})" for n, s in SERVICOS.items())
        reply = f"Hey! 👋 Welcome to Fresh Cuts. What can we do for you today? We offer: {lista}."
    elif not slot:
        sugestoes = ", ".join(candidatos[:3] or horarios_livres[:3])
        reply = (f"Nice, a {servico}! That time isn't open, but I have: {sugestoes}. Which one works?"
                 if hora else f"Nice, a {servico}! I have: {sugestoes}. Which one works for you?")
    elif not nome or not telefone:
        reply = f"Got it: {servico} on {slot}. What's your name and phone number so I can lock it in?"
    else:
        reply = (f"You're all set, {nome}! ✅ {servico} on {slot}. "
                 f"We'll text you a reminder at {telefone}. See you at 120 Ocean Dr!")

    return {"reply": reply, "ready_to_book": bool(servico and slot and nome and telefone),
            "service": servico, "slot": slot, "customer_name": nome, "phone": telefone}
