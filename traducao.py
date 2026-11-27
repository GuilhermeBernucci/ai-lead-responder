"""
Versão em português do Brasil da demo (usada nos vídeos em PT).

Rode com IDIOMA=pt para ver tudo em português: páginas, chat, agenda e lembretes.
Sem a variável, a demo continua em inglês, como o cliente americano vê.
"""

import os
import re
from datetime import datetime

EM_PT = os.environ.get("IDIOMA", "en").strip().lower().startswith("pt")


def t(en: str, pt: str) -> str:
    """Escolhe o texto do idioma atual."""
    return pt if EM_PT else en


# Nomes dos serviços (a chave em inglês continua sendo o "código" interno)
SERVICOS_PT = {
    "Haircut + Beard": "Corte + barba",
    "Skin Fade": "Degradê",
    "Beard Trim": "Barba",
    "Kids Cut": "Corte infantil",
    "Haircut": "Corte",
}
DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# Preços em reais para a versão brasileira (os em dólar ficam no ia.py)
PRECOS_BRL = {"Haircut": 50, "Skin Fade": 60, "Beard Trim": 35, "Haircut + Beard": 80, "Kids Cut": 40}


def preco(nome_servico: str, preco_usd: int) -> int:
    return PRECOS_BRL.get(nome_servico, preco_usd) if EM_PT else preco_usd


def moeda(valor: int) -> str:
    """'$35' em inglês, 'R$ 50' em português (com ponto de milhar)."""
    return f"R$ {valor:,}".replace(",", ".") if EM_PT else f"${valor:,}"


_TEL_US = re.compile(r"\((\d{3})\)\s?(\d{3})-(\d{4})|\b(\d{3})-(\d{3})-(\d{4})\b")


def telefone(texto: str) -> str:
    """Em PT troca telefones americanos, (305) 555-0123, por brasileiros com DDD: (11) 98555-0123."""
    if not EM_PT:
        return texto
    return _TEL_US.sub(lambda m: f"(11) 98{m.group(2) or m.group(5)}-{m.group(3) or m.group(6)}", texto)


def servico(nome: str) -> str:
    return SERVICOS_PT.get(nome, nome) if EM_PT else nome


def hora(dt: datetime) -> str:
    """'3:00 PM' em inglês, '15:00' em português."""
    return f"{dt:%H:%M}" if EM_PT else f"{dt.hour % 12 or 12}:{dt:%M %p}"


def dia(dt: datetime, curto: bool = False) -> str:
    """'Friday, November 27' / 'Fri Nov 27' em inglês; 'sexta, 27 de nov' em português."""
    if EM_PT:
        return f"{DIAS_PT[dt.weekday()]}, {dt.day} de {MESES_PT[dt.month - 1]}"
    return f"{dt:%a %b} {dt.day}" if curto else f"{dt:%A, %B} {dt.day}"


def slot(texto_slot: str) -> str:
    """Horário interno 'Friday Nov 27 15:00' -> 'Friday, Nov 27 at 3:00 PM' / 'sexta, 27 de nov às 15:00'."""
    try:
        dt = datetime.strptime(f"{datetime.now().year} {texto_slot}", "%Y %A %b %d %H:%M")
    except ValueError:
        return texto_slot
    if EM_PT:
        return f"{dia(dt)} às {dt:%H:%M}"
    return f"{dt:%A, %b} {dt.day} at {hora(dt)}"


def duracao(minutos: int) -> str:
    """30 -> '30 min'; 60 -> '1 hr' / '1h'."""
    if minutos % 60:
        return f"{minutos} min"
    return f"{minutos // 60}h" if EM_PT else f"{minutos // 60} hr"


def lista(itens: list) -> str:
    """['a', 'b', 'c'] -> 'a, b or c' / 'a, b ou c'."""
    if len(itens) < 2:
        return "".join(itens)
    return ", ".join(itens[:-1]) + t(" or ", " ou ") + itens[-1]


# Textos fixos das páginas HTML. A mais longa é trocada primeiro.
FRASES = {
    # site
    "Black Crown Barbershop": "Barbearia Black Crown",
    "Demo for a fictional business": "Demonstração para uma empresa fictícia",
    "Open the owner dashboard": "Abrir o painel do dono",
    "See plans": "Ver planos",
    "Services": "Serviços",
    "Barbers": "Barbeiros",
    "Visit": "Endereço",
    "Sharp cuts on Ocean Drive": "Cortes afiados na Ocean Drive",
    "Classic cuts, skin fades and hot-towel beard work since 2014. Tell our assistant what you want and when, and you're booked in seconds, even at 2am.":
        "Cortes clássicos, degradês e barba com toalha quente desde 2014. Diga ao nosso assistente o que você quer e quando, e seu horário fica marcado em segundos, até às 2 da manhã.",
    "Mon–Sat, 9am–7pm · Walk-ins welcome when chairs are free": "Seg a sáb, 9h às 19h · Sem hora marcada quando tiver cadeira livre",
    "Book your cut": "Agende seu corte",
    "Replies instantly, day or night": "Responde na hora, de dia ou de noite",
    "Hey! What can we do for you, and when works for you?": "Oi! O que vamos fazer hoje, e qual horário fica bom pra você?",
    "A skin fade on Friday at 3pm": "Um degradê na sexta às 15h",
    "A haircut tomorrow at 3pm": "Um corte amanhã às 15h",
    "Scissor, clipper or fade, wash and style · 30 min": "Tesoura, máquina ou degradê, lavagem e finalização · 30 min",
    "Shape, line-up and hot towel · 30 min": "Desenho, contorno e toalha quente · 30 min",
    "The full reset · 1 hr": "O pacote completo · 1h",
    "typing…": "digitando…",
    "Walk-ins welcome when chairs are free": "Sem hora marcada quando tiver cadeira livre",
    # agenda online no site
    "Book online": "Agende online",
    "Pick a service, a day and an open time. Then just send your name and phone in the chat.":
        "Escolha o serviço, o dia e um horário livre. Depois é só mandar seu nome e telefone no chat.",
    "Service": "Serviço",
    "Day": "Dia",
    "Time": "Horário",
    "Open": "Livre",
    "Booked": "Ocupado",
    # agenda do dono
    "Black Crown · My schedule": "Black Crown · Minha agenda",
    "My schedule": "Minha agenda",
    "Your appointments": "Seus horários",
    "Your website": "Seu site",
    "Set your hours and what you offer. How long each service takes decides which times clients can book, both on your website and in the chat.":
        "Defina seu horário e o que você faz. O tempo de cada serviço decide quais horários o cliente pode marcar, no site e no chat.",
    "How much is a beard trim?": "Quanto custa a barba?",
    "Send": "Enviar",
    "Scissor or clipper, wash and style": "Tesoura ou máquina, lavagem e finalização",
    "Bald to blended, razor-finished line-up": "Do zero ao esfumado, acabamento na navalha",
    "Shape, line-up and hot towel": "Desenho, contorno e toalha quente",
    "The full reset, about an hour": "O pacote completo, cerca de uma hora",
    "Ages 12 and under": "Até 12 anos",
    "Your barbers": "Seus barbeiros",
    "Owner. 15 years behind the chair, fades and tapers.": "Dono. 15 anos de cadeira, especialista em degradê.",
    "Beard specialist and the steadiest straight razor in Miami Beach.": "Especialista em barba e a navalha mais firme de Miami Beach.",
    "Textured hair, designs and kids who don't sit still.": "Cabelo crespo, desenhos e criança que não para quieta.",
    "What clients say": "O que os clientes dizem",
    "Booked at midnight from my couch, got a reminder the day before, cleanest fade I've had.":
        "Marquei à meia-noite do sofá, recebi lembrete na véspera, melhor degradê que já fiz.",
    "Jay fixed a beard two other shops gave up on. On time, no waiting around.":
        "O Jay arrumou uma barba que duas barbearias desistiram. No horário, sem espera.",
    "My son actually likes getting his hair cut now. Luis is great with kids.":
        "Meu filho agora gosta de cortar o cabelo. O Luis é ótimo com criança.",
    "Google review": "avaliação no Google",
    "Hours": "Horário",
    "Mon–Sat 9am–7pm": "Seg a sáb, 9h às 19h",
    "Sunday closed": "Domingo fechado",
    "Call": "Telefone",
    "Classic cuts, skin fades and beard work on Ocean Drive, Miami. Book in seconds by chat.":
        "Cortes clássicos, degradês e barba na Ocean Drive, Miami. Agende em segundos pelo chat.",
    "Booking chat": "Chat de agendamento",
    "Type a message": "Digite uma mensagem",
    "Message": "Mensagem",
    "5 stars": "5 estrelas",
    "Couldn't reach the shop. Check your connection and send again, or call (305) 555-0123.":
        "Não consegui falar com a barbearia. Confira sua conexão e envie de novo, ou ligue para (305) 555-0123.",
    # painel
    "Black Crown Dashboard": "Painel Black Crown",
    "Back to your website": "Voltar para o seu site",
    "Good morning, Marcus": "Bom dia, Marcus",
    "This is your booking assistant's report. Everything below was booked by the chat on your website, with no calls and no back-and-forth texts.":
        "Este é o relatório do seu assistente de agendamento. Tudo abaixo foi marcado pelo chat do seu site, sem ligação e sem troca de mensagens.",
    "How your assistant works": "Como o seu assistente funciona",
    "A client opens your website and tells the chat what they want and when.": "O cliente abre o seu site e diz no chat o que quer e quando.",
    "The assistant offers only times that are really free, then asks for a name and phone number.":
        "O assistente oferece só horários realmente livres e depois pede nome e telefone.",
    "The appointment shows up here, on the right day and time.": "O horário aparece aqui, no dia e na hora certos.",
    "Reminder texts go out on their own. Open any appointment to see exactly what will be sent and when.":
        "Os lembretes saem sozinhos. Abra qualquer horário para ver exatamente o que vai ser enviado e quando.",
    "Tip: share your booking link": "Dica: divulgue o seu link de agendamento",
    "Put your website link in your Instagram bio and Google profile. Every client who books there skips the phone, and you keep cutting.":
        "Coloque o link do seu site na bio do Instagram e no perfil do Google. Cada cliente que marca por lá não precisa ligar, e você continua cortando.",
    # planos
    "AI Booking Assistant Plans": "Planos do assistente de agendamento",
    "AI Booking Assistant for Barbershops & Salons": "Assistente de agendamento com IA para barbearias e salões",
    "Never miss a booking while you're cutting. Fewer no-shows. More repeat clients.":
        "Nunca perca um agendamento enquanto está cortando. Menos faltas. Mais clientes voltando.",
    "/month": "/mês",
    "/year": "/ano",
    "24/7 AI booking chat on your site": "Chat de agendamento com IA 24h no seu site",
    "Owner calendar dashboard": "Painel de agenda para o dono",
    "SMS reminders (24h + 2h)": "Lembretes por SMS (24h + 2h antes)",
    "Everything in Starter": "Tudo do Starter",
    "\"Time for your next cut\" rebooking texts": "Mensagens de \"hora do próximo corte\"",
    "Instagram & Google booking link": "Link de agendamento no Instagram e no Google",
    "AI replies to Google reviews": "IA responde às avaliações do Google",
    "BEST VALUE": "MELHOR CUSTO",
    "Pro Annual": "Pro Anual",
    "Everything in Pro": "Tudo do Pro",
    "2 months free": "2 meses grátis",
    "FREE professional website": "Site profissional GRÁTIS",
    "for your shop, built with your services, prices, photos and reviews, with the AI booking chat already inside.":
        "para a sua barbearia, feito com seus serviços, preços, fotos e avaliações, já com o chat de agendamento com IA.",
    "back to demo": "voltar para a demonstração",
    # preços fixos das páginas, em reais
    "$35": "R$ 50", "$40": "R$ 60", "$20": "R$ 35", "$50": "R$ 80", "$25": "R$ 40",
    "$49": "R$ 119", "$99": "R$ 199", "$990": "R$ 1.999",  # planos no Brasil
}
FRASES.update(SERVICOS_PT)

_padrao = re.compile("|".join(
    (r"\b" if k[0].isalnum() else "") + re.escape(k) + (r"\b" if k[-1].isalnum() else "")
    for k in sorted(FRASES, key=len, reverse=True)))


def frase(texto: str) -> str:
    return telefone(_padrao.sub(lambda m: FRASES[m.group(0)], texto)) if EM_PT else texto


def pagina(doc: str) -> str:
    """Traduz o texto visível de uma página HTML (sem mexer em CSS, links ou classes)."""
    if not EM_PT:
        return doc
    doc = doc.replace('<html lang="en">', '<html lang="pt-BR">')
    partes = re.split(r"(<style\b.*?</style>|<script\b.*?</script>)", doc, flags=re.S)
    for i, parte in enumerate(partes):
        if parte.startswith("<style"):
            continue
        if parte.startswith("<script"):  # só as frases conhecidas dentro de aspas
            partes[i] = re.sub(r'"([^"\n]*)"', lambda m: '"' + frase(m.group(1)) + '"', parte)
            continue
        # re.sub(r"\s+", " ") junta textos que no HTML estão quebrados em várias linhas
        parte = re.sub(r">([^<]+)<", lambda m: ">" + frase(re.sub(r"\s+", " ", m.group(1))) + "<", parte)
        parte = re.sub(r'((?:placeholder|aria-label|content|title|alt)=")([^"]*)"',
                       lambda m: m.group(1) + frase(m.group(2)) + '"', parte)
        partes[i] = parte
    return "".join(partes)
