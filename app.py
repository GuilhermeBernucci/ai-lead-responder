"""
Kit de agendamento com IA para barbearias e salões.

- http://localhost:8000/         -> site da barbearia (fictícia) com o chat e a agenda online
- http://localhost:8000/painel   -> painel do dono: horários marcados + lembretes, explicados passo a passo
- http://localhost:8000/agenda   -> o dono configura horário de funcionamento, dias e serviços (duração e preço)
- http://localhost:8000/planos   -> página de preços (o que VOCÊ vende para a barbearia)
"""

import html
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import agenda
import traducao as tr
from ia import responder

PASTA = Path(__file__).parent
DIAS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DIAS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def hora_en(dt):
    """"3:00 PM" sem zero à esquerda; o %-I do strftime não funciona no Windows."""
    return f"{dt.hour % 12 or 12}:{dt:%M %p}"


# ---------------- Textos de horário de funcionamento ----------------

def _hora_curta(texto: str) -> str:
    """'08:00' -> '8am' / '8h'; '20:30' -> '8:30pm' / '20h30'."""
    h, m = (int(x) for x in texto.split(":"))
    if tr.EM_PT:
        return f"{h}h" + (f"{m:02d}" if m else "")
    return f"{h % 12 or 12}" + (f":{m:02d}" if m else "") + ("am" if h < 12 else "pm")


def _dias_texto(dias: list) -> str:
    """[0,1,2,3,4,5] -> 'Mon–Sat' / 'Seg a sáb'; dias soltos viram lista."""
    nomes = DIAS_PT if tr.EM_PT else DIAS_EN
    dias = sorted(dias)
    if not dias:
        return ""
    if dias == list(range(dias[0], dias[-1] + 1)) and len(dias) > 2:
        return f"{nomes[dias[0]]} a {nomes[dias[-1]].lower()}" if tr.EM_PT else f"{nomes[dias[0]]}–{nomes[dias[-1]]}"
    return ", ".join(nomes[d] for d in dias)


def horario_funcionamento() -> str:
    c = agenda.carregar_config()
    faixa = tr.t(f"{_hora_curta(c['abre'])}–{_hora_curta(c['fecha'])}", f"{_hora_curta(c['abre'])} às {_hora_curta(c['fecha'])}")
    return f"{_dias_texto(c['dias'])}, {faixa}"


def dias_fechados() -> str:
    fechados = [d for d in range(7) if d not in agenda.carregar_config()["dias"]]
    if not fechados:
        return tr.t("Open every day", "Aberto todos os dias")
    nomes = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    nomes_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    lista = [(nomes_pt if tr.EM_PT else nomes)[d] for d in fechados]
    return tr.t(f"{tr.lista(lista)} closed", f"{tr.lista(lista)}: fechado")


# ---------------- Lembretes e painel ----------------

def lembretes(agendamento: dict) -> list:
    """Os SMS que o sistema manda para este cliente: (quando, para quê, texto)."""
    nome = agendamento["customer_name"].split()[0]
    servico = agendamento["service"]
    inicio = agenda.para_data(agendamento["slot"])
    return [
        (inicio - timedelta(hours=24), tr.t("Reminder", "Lembrete"), tr.t("cuts no-shows", "evita faltas"),
         tr.t(f"Hi {nome}! Reminder: your {servico} at Black Crown is tomorrow at {tr.hora(inicio)}. Reply C to cancel.",
              f"Oi, {nome}! Lembrete: seu horário ({servico.lower()}) na Black Crown é amanhã às {tr.hora(inicio)}. Responda C para cancelar.")),
        (inicio - timedelta(hours=2), tr.t("Heads-up", "Aviso"), tr.t("keeps you on time", "garante a pontualidade"),
         tr.t(f"See you soon, {nome}! Your {servico} is in 2 hours. 120 Ocean Dr.",
              f"Até já, {nome}! Seu horário ({servico.lower()}) é daqui a 2 horas. 120 Ocean Dr.")),
        (inicio + timedelta(weeks=4), tr.t("Rebooking", "Retorno"), tr.t("brings them back", "traz o cliente de volta"),
         tr.t(f"Hey {nome}, it's been 4 weeks since your last {servico}. Want me to book your next one?",
              f"E aí, {nome}? Já faz 4 semanas desde o seu último horário ({servico.lower()}). Quer que eu marque o próximo?")),
    ]


def loja_fechada(horario: str) -> bool:
    """True se o agendamento foi feito com a barbearia fechada, ex.: '2:14 AM'."""
    try:
        feito = datetime.strptime(horario, "%I:%M %p")
    except ValueError:
        return False
    abre, fecha = agenda.abre_fecha(feito)
    return not (abre <= feito < fecha)


def pagina(nome_arquivo: str, conteudo: str = "", extras: dict = None) -> str:
    """Lê o HTML, traduz os textos fixos e depois coloca as partes que mudam ({{...}})."""
    doc = tr.pagina((PASTA / nome_arquivo).read_text(encoding="utf-8")).replace("{{CONTEUDO}}", conteudo)
    for chave, valor in (extras or {}).items():
        doc = doc.replace("{{" + chave + "}}", valor)
    return doc


def montar_site() -> str:
    itens = "".join(
        f"""<div class="item"><div><span class="nome">{html.escape(nome)}</span><small>{tr.duracao(s['minutos'])}</small></div>"""
        f"""<span class="pontos"></span><b>{tr.moeda(s['preco'])}</b></div>"""
        for nome, s in agenda.servicos().items())
    return pagina("site.html", extras={"SERVICOS": itens, "HORARIO": html.escape(horario_funcionamento()),
                                       "HORARIO_RODAPE": html.escape(horario_funcionamento()) + "<br>" + html.escape(dias_fechados())})


def montar_painel() -> str:
    marcados = sorted(agenda.carregar_agenda(), key=lambda a: agenda.para_data(a["slot"]))
    servicos = agenda.servicos()
    total = sum(servicos.get(a["service"], {}).get("preco", 0) for a in marcados)
    fora_do_horario = sum(1 for a in marcados if loja_fechada(a.get("booked_at", "")))

    partes = [f"""
    <p class="editar"><a href="/agenda">{tr.t('Edit hours and services', 'Editar horários e serviços')}</a></p>
    <section class="numeros" aria-label="{tr.t('This week at a glance', 'Resumo da semana')}">
      <div><strong>{len(marcados)}</strong><span>{tr.t('appointments booked by your assistant', 'horários marcados pelo seu assistente')}</span></div>
      <div><strong>{tr.moeda(total)}</strong><span>{tr.t('in services on the calendar', 'em serviços na agenda')}</span></div>
      <div><strong>{len(marcados) * 3}</strong><span>{tr.t("text messages scheduled, so you don't have to send them", 'mensagens programadas, que você não precisa mandar')}</span></div>
      <div><strong>{fora_do_horario}</strong><span>{tr.t('booked while the shop was closed', 'marcados com a barbearia fechada')}</span></div>
    </section>"""]

    if not marcados:
        partes.append("<p class='vazio'>" + tr.t("No appointments yet. Open your website and book a test appointment in the chat to see it appear here.", "Nenhum horário ainda. Abra o seu site e marque um horário de teste no chat para ver ele aparecer aqui.") + "</p>")

    dia_atual = None
    for a in marcados:
        inicio = agenda.para_data(a["slot"])
        if inicio.date() != dia_atual:
            if dia_atual is not None:
                partes.append("</div>")
            dia_atual = inicio.date()
            partes.append(f"<h3 class='dia'>{tr.dia(inicio)}</h3><div class='lista'>")

        passos = []
        for quando, nome, motivo, texto in lembretes(a):
            estado = "sent" if quando < datetime.now() else "scheduled"
            passos.append(f"""<li class="{estado}"><b>{nome}</b> · {tr.dia(quando, curto=True)}, {tr.hora(quando)}
              <span class="motivo">{motivo}</span><q>{html.escape(texto)}</q></li>""")

        servico = servicos.get(a["service"], {"minutos": agenda.BLOCO, "preco": 0})
        fim = inicio + timedelta(minutes=servico["minutos"])
        partes.append(f"""
        <article class="horario">
          <time>{tr.hora(inicio)}<small>{tr.t('until', 'até')} {tr.hora(fim)}</small></time>
          <div class="info">
            <b>{html.escape(a['customer_name'])}</b> · {html.escape(a['service'])} · {tr.moeda(servico['preco'])}
            <span class="tel">{html.escape(tr.telefone(a['phone']))}</span>
            <details><summary>{tr.t('What happens next with this client', 'O que acontece agora com este cliente')}</summary><ol class="linha">{''.join(passos)}</ol></details>
          </div>
        </article>""")
    if dia_atual is not None:
        partes.append("</div>")
    return pagina("painel.html", "".join(partes))


# ---------------- Agenda do dono (/agenda) ----------------

def montar_config(aviso: str = "") -> str:
    c = agenda.carregar_config()
    nomes_dias = DIAS_PT if tr.EM_PT else DIAS_EN
    dias = "".join(
        f"""<label class="dia-check"><input type="checkbox" name="dias" value="{i}" {'checked' if i in c['dias'] else ''}>{nomes_dias[i]}</label>"""
        for i in range(7))

    def linha(i, s=None):
        s = s or {"nome": "", "minutos": "", "preco": ""}
        novo = s["nome"] == ""
        remover = "" if novo else (f"""<label class="remover"><input type="checkbox" name="remover_{i}" value="1">"""
                                   f"""{tr.t('Remove', 'Remover')}</label>""")
        return f"""
        <tr class="{'novo' if novo else ''}">
          <td><input name="nome_{i}" value="{html.escape(str(s['nome']))}" placeholder="{tr.t('New service, e.g. Eyebrows', 'Novo serviço, ex.: Sobrancelha')}" aria-label="{tr.t('Service name', 'Nome do serviço')}"></td>
          <td><input name="minutos_{i}" type="number" min="5" max="480" step="5" value="{s['minutos']}" aria-label="{tr.t('Minutes', 'Minutos')}"></td>
          <td><input name="preco_{i}" type="number" min="0" step="1" value="{s['preco']}" aria-label="{tr.t('Price', 'Preço')}"></td>
          <td>{remover}</td>
        </tr>"""

    linhas = "".join(linha(i, s) for i, s in enumerate(c["servicos"])) + linha(len(c["servicos"]))

    # Prévia: como o cliente vê o próximo dia aberto, de 30 em 30 minutos
    dia = agenda.amanha()
    ocupados = agenda.blocos_ocupados()
    previa = ""
    for nome, s in agenda.servicos().items():
        chips = "".join(f"""<span class="chip {'livre' if livre else 'ocupado'}">{tr.hora(h)}</span>"""
                        for h, livre in agenda.horarios_do_dia(dia, s["minutos"], ocupados))
        previa += f"""<div class="previa-servico"><b>{html.escape(nome)} · {tr.duracao(s['minutos'])}</b><div class="chips">{chips}</div></div>"""

    moeda = tr.t("$", "R$")
    conteudo = f"""
    {f'<p class="aviso">{aviso}</p>' if aviso else ''}
    <form method="post" action="/agenda" class="config">
      <section class="bloco">
        <h2>{tr.t('Opening hours', 'Horário de funcionamento')}</h2>
        <div class="horas">
          <label>{tr.t('Opens at', 'Abre às')} <input type="time" name="abre" value="{c['abre']}" step="1800" required></label>
          <label>{tr.t('Closes at', 'Fecha às')} <input type="time" name="fecha" value="{c['fecha']}" step="1800" required></label>
        </div>
        <p class="dica-campo">{tr.t('Clients can book every 30 minutes, from opening until a service fits before closing.', 'O cliente pode marcar de 30 em 30 minutos, da abertura até o último horário em que o serviço termina antes de fechar.')}</p>
        <h3>{tr.t('Days you work', 'Dias de atendimento')}</h3>
        <div class="dias">{dias}</div>
      </section>

      <section class="bloco">
        <h2>{tr.t('Services', 'Serviços')}</h2>
        <p class="dica-campo">{tr.t('How long each job takes is what blocks your calendar. A 60-minute service takes two 30-minute slots.', 'O tempo de cada serviço é o que ocupa a sua agenda. Um serviço de 60 minutos ocupa dois horários de 30.')}</p>
        <table>
          <thead><tr><th>{tr.t('Service', 'Serviço')}</th><th>{tr.t('Minutes', 'Minutos')}</th><th>{tr.t('Price', 'Preço')} ({moeda})</th><th></th></tr></thead>
          <tbody>{linhas}</tbody>
        </table>
        <p class="dica-campo">{tr.t('Fill in the last row to add a new service.', 'Preencha a última linha para incluir um serviço novo.')}</p>
      </section>

      <button>{tr.t('Save my schedule', 'Salvar minha agenda')}</button>
    </form>

    <section class="bloco previa">
      <h2>{tr.t('What clients see', 'Como o cliente vê')} · {tr.dia(dia)}</h2>
      <p class="dica-campo">{tr.t('Open times in light, booked or too late in dark.', 'Horários livres em destaque; ocupados ou que não cabem antes de fechar, apagados.')}</p>
      {previa}
    </section>"""
    return pagina("agenda.html", conteudo)


def salvar_config_do_form(campos: dict) -> str:
    """Valida o formulário do dono e salva. Devolve a mensagem para mostrar no topo."""
    def um(nome, padrao=""):
        return campos.get(nome, [padrao])[0].strip()

    abre, fecha = um("abre"), um("fecha")
    if not abre or not fecha or abre >= fecha:
        return tr.t("The closing time must be after the opening time.", "O horário de fechar precisa ser depois do de abrir.")
    dias = sorted(int(d) for d in campos.get("dias", []))
    if not dias:
        return tr.t("Pick at least one day.", "Escolha pelo menos um dia de atendimento.")

    servicos, i = [], 0
    while f"nome_{i}" in campos or f"minutos_{i}" in campos:
        nome, minutos, preco = um(f"nome_{i}"), um(f"minutos_{i}"), um(f"preco_{i}", "0")
        if nome and not um(f"remover_{i}"):
            try:
                minutos, preco = int(minutos), int(float(preco or 0))
            except ValueError:
                return tr.t(f"Check the minutes and price of {nome}.", f"Confira os minutos e o preço de {nome}.")
            if not 5 <= minutos <= 480:
                return tr.t(f"{nome}: use between 5 and 480 minutes.", f"{nome}: use entre 5 e 480 minutos.")
            if any(s["nome"].lower() == nome.lower() for s in servicos):
                return tr.t(f"{nome} appears twice.", f"{nome} aparece duas vezes.")
            servicos.append({"nome": nome, "minutos": minutos, "preco": preco})
        i += 1
    if not servicos:
        return tr.t("Keep at least one service.", "Deixe pelo menos um serviço.")

    agenda.salvar_config({"abre": abre, "fecha": fecha, "dias": dias, "servicos": servicos})
    return ""


def horarios_json(servico: str) -> str:
    """Horários de 30 em 30 min dos próximos dias para o site do cliente."""
    s = agenda.servicos().get(servico)
    if not s:
        return json.dumps({"dias": []})
    ocupados = agenda.blocos_ocupados()
    dias = []
    for dia in agenda.dias_abertos(6):
        horarios = [{"rotulo": tr.hora(h), "livre": livre,
                     "mensagem": f"{servico} · {tr.slot(h.strftime(agenda.FORMATO_SLOT))}"}
                    for h, livre in agenda.horarios_do_dia(dia, s["minutos"], ocupados)]
        dias.append({"rotulo": tr.dia(dia), "horarios": horarios})
    return json.dumps({"dias": dias}, ensure_ascii=False)


# ---------------- Servidor ----------------

class Servidor(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        consulta = parse_qs(url.query)
        if url.path == "/horarios":
            return self._enviar(horarios_json(consulta.get("servico", [""])[0]), "application/json")
        if url.path == "/agenda":
            aviso = tr.t("Saved! Your website and chat already use the new schedule.",
                         "Salvo! O site e o chat já estão usando a agenda nova.") if "salvo" in consulta else ""
            return self._enviar(montar_config(aviso), "text/html")
        rotas = {"/painel": montar_painel, "/planos": lambda: pagina("planos.html")}
        self._enviar(rotas.get(url.path, montar_site)(), "text/html")

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho).decode("utf-8")

        if self.path == "/agenda":  # o dono salvou a agenda
            erro = salvar_config_do_form(parse_qs(corpo, keep_blank_values=True))
            if erro:
                return self._enviar(montar_config(erro), "text/html")
            self.send_response(303)
            self.send_header("Location", "/agenda?salvo=1")
            self.end_headers()
            return

        # /chat: o navegador manda a conversa, a IA responde
        conversa = json.loads(corpo)["conversa"]
        livres = agenda.livres_por_servico()
        resultado = responder(conversa, livres)

        # Nunca confiamos cegamente na IA: só agenda se o horário existir e estiver livre para esse serviço
        if resultado["ready_to_book"] and resultado["slot"] in livres.get(resultado["service"], []):
            marcados = agenda.carregar_agenda()
            novo = {k: resultado[k] for k in ["service", "slot", "customer_name", "phone"]}
            novo["booked_at"] = hora_en(datetime.now())
            marcados.append(novo)
            agenda.salvar_agenda(marcados)
            # Num produto real: aqui programaríamos os SMS de verdade (ex.: Twilio)
        elif resultado["ready_to_book"]:
            resultado["reply"] = tr.t("That slot was just taken. Pick another time and I'll book it.",
                                      "Esse horário acabou de ser ocupado. Escolha outro que eu marco pra você.")
            resultado["ready_to_book"] = False

        self._enviar(json.dumps(resultado), "application/json")

    def log_message(self, *args):  # deixa o terminal limpo
        pass

    def _enviar(self, conteudo: str, tipo: str):
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.end_headers()
        self.wfile.write(conteudo.encode("utf-8"))


if __name__ == "__main__":
    print("Abra no navegador: http://localhost:8000  (Ctrl+C para parar)")
    HTTPServer(("localhost", 8000), Servidor).serve_forever()
