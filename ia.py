"""
O "cérebro" do assistente de agendamento.

A cada mensagem do cliente, a IA recebe:
  - a conversa até agora
  - os serviços da barbearia (com preço e duração)
  - os horários livres para cada serviço
e devolve um "formulário" (JSON) com a resposta, os botões de opção e, quando tiver tudo, o agendamento.

Dois modos:
- MODO REAL: com a variável ANTHROPIC_API_KEY, quem conversa é o Claude.
- MODO DEMO: sem chave, regras simples de palavras-chave (para testar de graça).
"""

import json
import os
import re
from datetime import datetime, timedelta

import traducao as tr

# Duração em minutos: a agenda anda de 30 em 30, então corte + barba ocupa dois blocos
SERVICOS = {
    "Haircut": {"preco": 35, "minutos": 30},
    "Beard Trim": {"preco": 20, "minutos": 30},
    "Haircut + Beard": {"preco": 50, "minutos": 60},
}
FORMATO_SLOT = "%A %b %d %H:%M"  # ex.: "Friday Nov 27 15:30"
ABRE, FECHA = 9, 19  # seg a sáb, 9h às 19h

# A IA sempre devolve estes campos. Campo vazio ("") = ainda não sabemos.
ESQUEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
        "ready_to_book": {"type": "boolean"},
        "service": {"type": "string"},
        "slot": {"type": "string"},
        "customer_name": {"type": "string"},
        "phone": {"type": "string"},
    },
    "required": ["reply", "options", "ready_to_book", "service", "slot", "customer_name", "phone"],
    "additionalProperties": False,
}

INSTRUCOES = """You are the friendly booking assistant of "Black Crown Barbershop" in Miami, FL.
Chat with the customer by text, in a short, casual, friendly tone (1-3 sentences).
Reply in {idioma}.
Your goal: book an appointment. You need 4 things: service, time slot, name and phone.

Services (name: price, duration):
{servicos}

Available start times for each service (ONLY offer these, copy them exactly in the "slot" field):
{horarios}

Rules:
- If the service is unknown, ask which one and put the service names in "options".
- If the customer asks for a time that is already booked or closed, say so and put the 3 closest
  available start times for that service in "options" (same day first). Copy them exactly.
- Otherwise "options" is an empty list.
- Fill each field with what you know so far; use "" for unknown fields. "service" must be one of the names above.
- Set ready_to_book to true only when you have all 4 things and the customer agreed.
  In that case, the reply must confirm the appointment and say they'll get a text reminder.
- Answer questions about prices and services. Address: 120 Ocean Dr, Miami."""


def responder(conversa: list, livres: dict) -> dict:
    """conversa = [{"role": "user"/"assistant", "content": "..."}]; livres = {serviço: [horários livres]}"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _modo_real(conversa, livres)
    return _modo_demo(conversa, livres)


def _modo_real(conversa: list, livres: dict) -> dict:
    import anthropic

    servicos = "\n".join(f"- {n}: ${s['preco']}, {s['minutos']} min" for n, s in SERVICOS.items())
    horarios = "\n\n".join(f"{n}:\n" + "\n".join(livres.get(n, [])[:40]) for n in SERVICOS)
    client = anthropic.Anthropic()
    resposta = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        system=INSTRUCOES.format(idioma=tr.t("English", "Brazilian Portuguese"), servicos=servicos, horarios=horarios),
        messages=conversa,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resposta.stop_reason == "refusal":
        return _modo_demo(conversa, livres)
    texto = next(b.text for b in resposta.content if b.type == "text")
    return json.loads(texto)


# ---------------- MODO DEMO (regras simples) ----------------

PALAVRAS_SERVICO = [  # a ordem importa: o mais específico primeiro
    ("Haircut + Beard", ["cut and beard", "haircut and beard", "cut + beard", "both",
                         "corte e barba", "corte + barba", "cabelo e barba"]),
    ("Beard Trim", ["beard", "barba"]),
    ("Haircut", ["haircut", "cut", "trim", "fade", "corte", "cortar", "degradê", "degrade", "cabelo"]),
]
DIAS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DIAS_PT = {"segunda": 0, "terça": 1, "terca": 1, "quarta": 2, "quinta": 3,
           "sexta": 4, "sábado": 5, "sabado": 5, "domingo": 6}


def para_data(slot: str) -> datetime:
    agora = datetime.now()
    data = datetime.strptime(f"{agora.year} {slot}", f"%Y {FORMATO_SLOT}")
    if data < agora - timedelta(days=60):  # virada de ano
        data = data.replace(year=agora.year + 1)
    return data


def primeiro_dia_util(a_partir: datetime) -> datetime:
    dia = a_partir
    while dia.weekday() == 6:  # domingo fechado
        dia += timedelta(days=1)
    return dia


def _servico(fala: str) -> str:
    return next((nome for nome, palavras in PALAVRAS_SERVICO if any(p in fala for p in palavras)), "")


def _dia(fala: str):
    """Data pedida na fala: 'friday'/'sexta' -> próxima sexta; 'tomorrow'/'amanhã' -> próximo dia útil."""
    amanha = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    if "tomorrow" in fala or "amanhã" in fala or "amanha" in fala:
        return primeiro_dia_util(amanha)
    semana = next((i for i, d in enumerate(DIAS) if d in fala), None)
    if semana is None:
        semana = next((i for pt, i in DIAS_PT.items() if pt in fala), None)
    if semana is None:
        return None
    return amanha + timedelta(days=(semana - amanha.weekday()) % 7)


def _hora(fala: str):
    """(hora, minuto) pedidos: '3pm', '3:30 pm', '15h', '15h30', '15:30'."""
    fala = re.sub(r"·\s*\d+\s*(?:min|hr|h)\b", "", fala)  # "Corte + barba · 1h" é duração, não horário
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", fala)
    if m:
        return int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0), int(m.group(2) or 0)
    m = re.search(r"\b(\d{1,2})\s*h\s*(\d{2})?\b", fala) or re.search(r"\b(\d{1,2}):(\d{2})\b", fala)
    if m:
        return int(m.group(1)), int(m.group(2) or 0)
    return None


def _ultimo(falas: list, achar):
    """Procura da mensagem mais recente para a mais antiga (o cliente pode mudar de ideia)."""
    for fala in reversed(falas):
        achado = achar(fala)
        if achado:
            return achado
    return None


def _mais_proximos(alvo: datetime, livres: list, quantos: int = 3) -> list:
    """Horários livres mais perto do pedido: primeiro no mesmo dia, depois os seguintes."""
    mesmo_dia = [s for s in livres if para_data(s).date() == alvo.date()]
    if mesmo_dia:
        perto = sorted(mesmo_dia, key=lambda s: abs(para_data(s) - alvo))[:quantos]
        return sorted(perto, key=para_data)  # mostra em ordem de horário
    return [s for s in livres if para_data(s) > alvo][:quantos]


def _modo_demo(conversa: list, livres: dict) -> dict:
    falas = [m["content"].lower() for m in conversa if m["role"] == "user"]
    texto = " ".join(falas)

    servico = _ultimo(falas, _servico) or ""
    livres_servico = livres.get(servico, [])

    # 1) O cliente tocou num botão de horário? Então o horário vem exato.
    slot = _ultimo(falas, lambda f: next((s for s in livres_servico if tr.slot(s).lower() in f), None)) or ""

    # 2) Senão, monta o horário pedido a partir do dia e da hora que ele escreveu
    pedido = None
    if not slot:
        dia, hora = _ultimo(falas, _dia), _ultimo(falas, _hora)
        if hora:
            base = dia or primeiro_dia_util(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            pedido = base.replace(hour=hora[0], minute=hora[1])
            exato = pedido.strftime(FORMATO_SLOT)
            if exato in livres_servico:
                slot = exato
        elif dia:
            pedido = dia.replace(hour=ABRE)

    nome_match = re.search(r"(?:my name is|i'm|i am|name:|meu nome é|me chamo|sou o|sou a)\s+([a-zà-ú]+)", texto)
    nome = nome_match.group(1).title() if nome_match else ""
    # EUA: (305) 555-0199 · Brasil: (11) 98765-4321
    tel_match = re.search(r"(\(?\d{2,3}\)?[\s.-]?9?\d{3,4}[\s.-]?\d{4})", texto)
    telefone = tel_match.group(1) if tel_match else ""

    opcoes = []
    if not servico:
        opcoes = [f"{tr.servico(n)} · {tr.duracao(s['minutos'])}" for n, s in SERVICOS.items()]
        lista = ", ".join(f"{tr.servico(n)} ({tr.duracao(s['minutos'])}, {tr.moeda(tr.preco(n, s['preco']))})"
                          for n, s in SERVICOS.items())
        reply = tr.t(f"Hey! 👋 Welcome to Black Crown. What would you like? {lista}.",
                     f"Oi! 👋 Bem-vindo à Black Crown. O que você quer fazer? {lista}.")
    elif not slot:
        nome_servico = tr.servico(servico)
        duracao = tr.duracao(SERVICOS[servico]["minutos"])
        if pedido and _hora(texto):
            proximos = _mais_proximos(pedido, livres_servico)
            opcoes = [tr.slot(s) for s in proximos]
            # Mesmo dia: só a hora ("14:30"). Outro dia: dia e hora ("segunda, 30 de nov às 09:00")
            horas = tr.lista([tr.hora(para_data(s)) if para_data(s).date() == pedido.date() else tr.slot(s)
                              for s in proximos])
            fechado = not (ABRE <= pedido.hour < FECHA) or pedido.weekday() == 6
            if fechado:
                reply = tr.t(f"We're closed at that time. The closest open times for a {nome_servico} ({duracao}) are {horas}. Which one works?",
                             f"Nesse horário a barbearia está fechada. Os horários livres mais próximos para {nome_servico.lower()} ({duracao}) são {horas}. Qual fica melhor?")
            else:
                reply = tr.t(f"Sorry, {tr.slot(pedido.strftime(FORMATO_SLOT))} is already booked. "
                             f"The closest open times for a {nome_servico} ({duracao}) are {horas}. Which one works?",
                             f"Poxa, {tr.slot(pedido.strftime(FORMATO_SLOT))} já está ocupado. "
                             f"Os horários livres mais próximos para {nome_servico.lower()} ({duracao}) são {horas}. Qual fica melhor?")
        else:
            proximos = _mais_proximos(pedido, livres_servico) if pedido else livres_servico[:3]
            opcoes = [tr.slot(s) for s in proximos]
            reply = tr.t(f"Nice, a {nome_servico} ({duracao})! Here are the next open times. Which one works for you?",
                         f"Boa, {nome_servico.lower()} ({duracao})! Esses são os próximos horários livres. Qual fica bom pra você?")
    elif not nome or not telefone:
        reply = tr.t(f"Got it: {tr.servico(servico)} on {tr.slot(slot)}. What's your name and phone number so I can lock it in?",
                     f"Fechado: {tr.servico(servico).lower()} para {tr.slot(slot)}. Qual o seu nome e telefone pra eu confirmar?")
    else:
        reply = tr.t(f"You're all set, {nome}! ✅ {tr.servico(servico)} on {tr.slot(slot)}. "
                     f"We'll text you a reminder at {telefone}. See you at 120 Ocean Dr!",
                     f"Tudo certo, {nome}! ✅ {tr.servico(servico)} para {tr.slot(slot)}. "
                     f"Vamos mandar um lembrete para {telefone}. Te esperamos na 120 Ocean Dr!")

    return {"reply": reply, "options": opcoes, "ready_to_book": bool(servico and slot and nome and telefone),
            "service": servico, "slot": slot, "customer_name": nome, "phone": telefone}
