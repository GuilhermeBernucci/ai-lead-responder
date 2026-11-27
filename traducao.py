"""
Versão em português do Brasil da demo (usada nos vídeos em PT).

Rode com IDIOMA=pt para ver tudo em português: site, e-mail de resposta e painel.
Sem a variável, a demo continua em inglês, como o cliente americano vê.
Os valores do formulário (value="Roofing" etc.) continuam em inglês, só o texto visível muda.
"""

import os
import re

EM_PT = os.environ.get("IDIOMA", "en").strip().lower().startswith("pt")


def t(en: str, pt: str) -> str:
    """Escolhe o texto do idioma atual."""
    return pt if EM_PT else en


FRASES = {
    # site
    "Demo for a fictional business": "Demonstração para uma empresa fictícia",
    "Open the owner dashboard": "Abrir o painel do dono",
    "High-end residential and commercial construction and remodeling in Dallas. Free on-site estimates.":
        "Construção e reforma residencial e comercial de alto padrão em Dallas. Orçamento grátis no local.",
    "Vertex Build, home": "Vertex Build, início",
    "Main": "Principal",
    "Home": "Início",
    "About": "Sobre",
    "Projects": "Projetos",
    "Services": "Serviços",
    "Why us": "Diferenciais",
    "Contact": "Contato",
    "Request a quote": "Solicite um orçamento",
    "Building": "Construindo",
    "great achievements.": "grandes conquistas.",
    "Projects that bring together design, quality and innovation to turn your plans into reality.":
        "Projetos que unem design, qualidade e inovação para transformar seus sonhos em realidade.",
    "See our projects": "Conheça nossos projetos",
    "Why Vertex Build": "Por que a Vertex Build",
    "Quality": "Qualidade",
    "in every detail": "em cada detalhe",
    "Safety": "Segurança",
    "at every stage": "em todas as etapas",
    "Commitment": "Compromisso",
    "to your project": "com o seu projeto",
    "Excellence": "Excelência",
    "in residential and commercial work": "em obras residenciais e comerciais",
    "Our projects": "Nossos projetos",
    "Projects that": "Projetos que",
    "inspire.": "inspiram.",
    "From concept to handover, every build is planned to deliver the most in comfort, function and refinement.":
        "Do conceito à entrega, cada obra é pensada para oferecer o máximo em conforto, funcionalidade e sofisticação.",
    "See all projects": "Ver todos os projetos",
    "Luxury Residence": "Residencial Alto Padrão",
    "Corporate Commercial": "Comercial Corporativo",
    "Modern Residential": "Residencial Moderno",
    "months": "meses",
    "Modern house with a pool, lit at night": "Casa moderna com piscina, iluminada à noite",
    "Glass office building at dusk": "Prédio comercial de vidro ao entardecer",
    "Modern apartment building with glass balconies": "Prédio residencial moderno com sacadas de vidro",
    "About Vertex Build": "Sobre a Vertex Build",
    "More than building,": "Mais que construir,",
    "we deliver life projects.": "realizamos projetos de vida.",
    "Vertex Build is a construction company committed to excellence, delivering complete construction and engineering solutions, always focused on quality, innovation and client satisfaction.":
        "A Vertex Build é uma construtora comprometida com a excelência, entregando soluções completas em construção e engenharia, sempre com foco na qualidade, inovação e satisfação dos nossos clientes.",
    "Learn more about us": "Saiba mais sobre nós",
    "Complete construction solutions": "Soluções completas em construção",
    "Specialized, experienced team": "Equipe especializada e experiente",
    "On time and on budget, every time": "Compromisso com prazos e qualidade",
    "Free estimate": "Orçamento grátis",
    "Tell us about your project.": "Conte sobre o seu projeto.",
    "We reply in minutes.": "Respondemos em minutos.",
    "Kitchens, bathrooms, additions, roofs, decks and new builds across Dallas. Send the form and you'll hear back within minutes, not days.":
        "Cozinhas, banheiros, ampliações, telhados, decks e obras novas em toda Dallas. Envie o formulário e receba resposta em minutos, não em dias.",
    "4.9 on Google": "Nota 4,9 no Google",
    "212 reviews": "212 avaliações",
    "640+ projects": "Mais de 640 obras",
    "finished since 2009": "entregues desde 2009",
    "5-year warranty": "Garantia de 5 anos",
    "on all workmanship": "em toda a mão de obra",
    "Get a free estimate": "Peça um orçamento grátis",
    "Takes about a minute. No pressure, no spam.": "Leva cerca de um minuto. Sem pressão, sem spam.",
    "Your name": "Seu nome",
    "Phone": "Telefone",
    "Email": "E-mail",
    "Project type": "Tipo de obra",
    "Budget": "Orçamento",
    "Start": "Início",
    "Tell us about your project": "Conte sobre o seu projeto",
    "What would you like to build or change? Rough size, materials you like, anything that matters to you.":
        "O que você quer construir ou mudar? Tamanho aproximado, materiais que você gosta, o que for importante pra você.",
    "Send my estimate request": "Enviar meu pedido de orçamento",
    "You'll get an email from us right away, and a call to book your free on-site visit.":
        "Você recebe um e-mail nosso na hora, e uma ligação para marcar a visita gratuita.",
    "Let's build something": "Vamos construir algo",
    "extraordinary": "extraordinário",
    "together?": "juntos?",
    "Get in touch and request a no-obligation estimate.": "Entre em contato e solicite um orçamento sem compromisso.",
    "Building the future, today.": "Construindo o futuro, hoje.",
    "Social media": "Redes sociais",
    "Office": "Escritório",
    "Mon–Fri 7am–6pm": "Seg a sex, 7h às 18h",
    # opções do formulário e valores que aparecem no painel
    "Kitchen remodel": "Reforma de cozinha",
    "Bathroom remodel": "Reforma de banheiro",
    "Roofing": "Telhado",
    "Deck / patio": "Deck / varanda",
    "Home addition": "Ampliação da casa",
    "Repairs / other": "Reparos / outros",
    "Not sure": "Ainda não sei",
    "Under $10k": "Até R$ 50 mil",
    "$10k - $30k": "R$ 50 mil a R$ 150 mil",
    "$30k - $75k": "R$ 150 mil a R$ 400 mil",
    "$75k+": "Acima de R$ 400 mil",
    "ASAP": "O quanto antes",
    "1-3 months": "1 a 3 meses",
    "3-6 months": "3 a 6 meses",
    "Just exploring": "Só pesquisando",
    # obrigado
    "Request received · Vertex Build": "Pedido recebido · Vertex Build",
    "Request received": "Pedido recebido",
    "Thanks! We just sent this email to your inbox. Expect a call shortly to book your free on-site estimate.":
        "Obrigado! Acabamos de mandar este e-mail para você. Em breve ligamos para marcar o orçamento gratuito no local.",
    "From: Vertex Build · Subject: About your project": "De: Vertex Build · Assunto: Sobre o seu projeto",
    "Demo:": "Demonstração:",
    "see how this lead looks in the owner dashboard": "veja como este pedido aparece no painel do dono",
    "back to the website": "voltar para o site",
    # painel
    "Vertex Build · Leads": "Vertex Build · Pedidos",
    "Back to your website": "Voltar para o seu site",
    "Your leads, Dana": "Seus pedidos, Dana",
    "Every estimate request from your website lands here. Your assistant has already replied to each homeowner and sorted them by how ready they are to hire, so you know who to call first.":
        "Todo pedido de orçamento do seu site chega aqui. O assistente já respondeu cada cliente e separou todos pelo quanto estão prontos para contratar, então você sabe para quem ligar primeiro.",
    "How your assistant works": "Como o seu assistente funciona",
    "A homeowner fills in the estimate form on your website, day or night.": "O cliente preenche o formulário de orçamento no seu site, de dia ou de noite.",
    "Within seconds, the assistant emails them back so they know you're on it.": "Em segundos, o assistente responde por e-mail, e o cliente sabe que você já está cuidando.",
    "It reads the request and sorts the lead into Call today, Call this week or Keep in touch.":
        "Ele lê o pedido e coloca o cliente em Ligar hoje, Ligar esta semana ou Manter contato.",
    "You call, using the suggested questions. The price range helps you size the job before you go.":
        "Você liga usando as perguntas sugeridas. A faixa de preço ajuda a dimensionar a obra antes da visita.",
    "Call today": "Ligar hoje",
    "Call this week": "Ligar esta semana",
    "Keep in touch": "Manter contato",
    "Clear project, real budget, wants to start soon. These are the jobs you win by calling first.":
        "Projeto claro, orçamento real, quer começar logo. São as obras que você ganha ligando primeiro.",
    "A real project, but the budget or timeline is still open. A friendly call keeps you in the running.":
        "Projeto real, mas o orçamento ou o prazo ainda estão em aberto. Uma ligação simpática mantém você na disputa.",
    "Still exploring. They already got a reply; a follow-up email in a few weeks is enough for now.":
        "Ainda pesquisando. Já recebeu resposta; um e-mail de acompanhamento em algumas semanas basta por enquanto.",
    "Nothing here right now.": "Nada por aqui agora.",
    "Likely job size": "Tamanho provável da obra",
    "Their budget": "Orçamento do cliente",
    "Wants to start": "Quer começar",
    "Came in": "Chegou",
    "answered in": "respondido em",
    "Questions to ask on the call": "Perguntas para fazer na ligação",
    "The email they already received": "O e-mail que o cliente já recebeu",
    "Call": "Ligar",
}

_padrao = re.compile("|".join(
    (r"\b" if k[0].isalnum() else "") + re.escape(k) + (r"\b" if k[-1].isalnum() else "")
    for k in sorted(FRASES, key=len, reverse=True)))


_TEL_US = re.compile(r"\((\d{3})\)\s?(\d{3})-(\d{4})|\b(\d{3})-(\d{3})-(\d{4})\b")


def telefone(texto: str) -> str:
    """Em PT troca telefones americanos, (214) 555-0182, por brasileiros com DDD: (11) 98555-0182."""
    if not EM_PT:
        return texto
    return _TEL_US.sub(lambda m: f"(11) 98{m.group(2) or m.group(5)}-{m.group(3) or m.group(6)}", texto)


_HORA_US = re.compile(r"\b(\d{1,2}):(\d{2}) (AM|PM)\b")


def horario(texto: str) -> str:
    """Em PT troca '9:50 PM' por '21:50'."""
    if not EM_PT:
        return texto
    return _HORA_US.sub(lambda m: f"{int(m.group(1)) % 12 + (12 if m.group(3) == 'PM' else 0):02d}:{m.group(2)}", texto)


def frase(texto: str) -> str:
    return horario(telefone(_padrao.sub(lambda m: FRASES[m.group(0)], texto))) if EM_PT else texto


def pagina(doc: str) -> str:
    """Traduz o texto visível de uma página HTML (sem mexer em CSS, links, classes ou valores do formulário)."""
    if not EM_PT:
        return doc
    doc = doc.replace('<html lang="en">', '<html lang="pt-BR">')
    partes = re.split(r"(<style\b.*?</style>|<script\b.*?</script>|<pre\b.*?</pre>)", doc, flags=re.S)
    for i, parte in enumerate(partes):
        if parte.startswith(("<style", "<script", "<pre")):
            continue  # o e-mail (<pre>) já vem escrito em português pelo ia.py
        parte = re.sub(r">([^<]+)<", lambda m: ">" + frase(m.group(1)) + "<", parte)
        parte = re.sub(r'((?:placeholder|aria-label|content|title|alt)=")([^"]*)"',
                       lambda m: m.group(1) + frase(m.group(2)) + '"', parte)
        partes[i] = parte
    return "".join(partes)
