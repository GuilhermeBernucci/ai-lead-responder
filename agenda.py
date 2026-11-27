"""
A agenda da barbearia: o que o dono configura e os horários que o cliente pode escolher.

O dono edita em /agenda:
  - que horas abre e fecha (ex.: 08:00 às 20:00)
  - em que dias da semana atende
  - os serviços: nome, quanto tempo leva (minutos) e preço

A agenda do cliente anda de 30 em 30 minutos (08:00, 08:30, 09:00 ... até o fechamento).
Um serviço de 60 minutos ocupa dois blocos; um de 45 ocupa dois também (arredonda para cima).

Cada idioma tem os seus arquivos (a demo em inglês e a em português não se misturam):
  configuracao-en.json / configuracao-pt.json  -> o que o dono configurou
  agendamentos-en.json / agendamentos-pt.json  -> os horários marcados
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import traducao as tr

PASTA = Path(__file__).parent
IDIOMA = "pt" if tr.EM_PT else "en"
ARQUIVO_CONFIG = PASTA / f"configuracao-{IDIOMA}.json"
ARQUIVO_AGENDA = PASTA / f"agendamentos-{IDIOMA}.json"
FORMATO_SLOT = "%A %b %d %H:%M"  # ex.: "Friday Nov 27 15:30" (formato interno, sempre em inglês)
BLOCO = 30  # minutos

PADRAO = {
    "abre": "08:00",
    "fecha": "20:00",
    "dias": [0, 1, 2, 3, 4, 5],  # 0 = segunda ... 6 = domingo
    "servicos": [
        {"nome": tr.t("Haircut", "Corte"), "minutos": 30, "preco": 50 if tr.EM_PT else 35},
        {"nome": tr.t("Beard Trim", "Barba"), "minutos": 30, "preco": 35 if tr.EM_PT else 20},
        {"nome": tr.t("Haircut + Beard", "Corte e barba"), "minutos": 60, "preco": 80 if tr.EM_PT else 50},
    ],
}


# ---------------- Configuração do dono ----------------

def carregar_config() -> dict:
    if not ARQUIVO_CONFIG.exists():
        salvar_config(PADRAO)
    return json.loads(ARQUIVO_CONFIG.read_text(encoding="utf-8"))


def salvar_config(config: dict) -> None:
    ARQUIVO_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def servicos() -> dict:
    """{nome: {"minutos": 30, "preco": 50}} na ordem em que o dono cadastrou."""
    return {s["nome"]: {"minutos": int(s["minutos"]), "preco": s["preco"]} for s in carregar_config()["servicos"]}


def _hora_config(texto: str) -> tuple:
    h, m = texto.split(":")
    return int(h), int(m)


def abre_fecha(dia: datetime) -> tuple:
    config = carregar_config()
    (ha, ma), (hf, mf) = _hora_config(config["abre"]), _hora_config(config["fecha"])
    base = dia.replace(hour=0, minute=0, second=0, microsecond=0)
    return base.replace(hour=ha, minute=ma), base.replace(hour=hf, minute=mf)


def atende(dia: datetime) -> bool:
    return dia.weekday() in carregar_config()["dias"]


def proximo_dia_aberto(a_partir: datetime) -> datetime:
    dia = a_partir.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(7):
        if atende(dia):
            return dia
        dia += timedelta(days=1)
    return a_partir


def amanha() -> datetime:
    return proximo_dia_aberto(datetime.now() + timedelta(days=1))


# ---------------- Horários marcados ----------------

def para_data(slot: str) -> datetime:
    agora = datetime.now()
    data = datetime.strptime(f"{agora.year} {slot}", f"%Y {FORMATO_SLOT}")
    if data < agora - timedelta(days=60):  # virada de ano
        data = data.replace(year=agora.year + 1)
    return data


def criar_exemplos() -> list:
    """Alguns clientes de exemplo. Amanhã às 15:00 já está ocupado: é o horário que a demo pede no chat."""
    nomes = list(servicos())
    corte, barba, combo = nomes[0], nomes[min(1, len(nomes) - 1)], nomes[min(2, len(nomes) - 1)]
    clientes = [("Andre", corte, 0, 10), ("Chris", barba, 0, 11), ("Maria", corte, 0, 14),
                ("Kevin", combo, 0, 15), ("Tyler", corte, 1, 13), ("Omar", combo, 2, 17)]
    dias = [amanha()]
    while len(dias) < 3:
        dias.append(proximo_dia_aberto(dias[-1] + timedelta(days=1)))
    exemplos = []
    for i, (nome, servico, d, hora) in enumerate(clientes):
        exemplos.append({"service": servico, "slot": dias[d].replace(hour=hora).strftime(FORMATO_SLOT),
                         "customer_name": nome, "phone": "(305) 555-01" + str(10 + i),
                         "booked_at": "2:14 AM" if nome == "Kevin" else "earlier"})
    return exemplos


def carregar_agenda() -> list:
    if not ARQUIVO_AGENDA.exists():
        salvar_agenda(criar_exemplos())
    return json.loads(ARQUIVO_AGENDA.read_text(encoding="utf-8"))


def salvar_agenda(lista: list) -> None:
    ARQUIVO_AGENDA.write_text(json.dumps(lista, indent=2, ensure_ascii=False), encoding="utf-8")


def blocos(minutos: int) -> int:
    return max(1, math.ceil(minutos / BLOCO))


def blocos_ocupados() -> set:
    """Cada agendamento ocupa blocos de 30 min conforme a duração do serviço."""
    duracoes = servicos()
    ocupados = set()
    for a in carregar_agenda():
        inicio = para_data(a["slot"])
        for b in range(blocos(duracoes.get(a["service"], {}).get("minutos", BLOCO))):
            ocupados.add(inicio + timedelta(minutes=BLOCO * b))
    return ocupados


# ---------------- Horários para o cliente ----------------

def horarios_do_dia(dia: datetime, minutos: int, ocupados: set = None) -> list:
    """Todos os horários do dia de 30 em 30 min: [(datetime, livre?)]. Só começa se der para terminar até o fechamento."""
    if not atende(dia):
        return []
    ocupados = blocos_ocupados() if ocupados is None else ocupados
    abre, fecha = abre_fecha(dia)
    lista, inicio = [], abre
    while inicio + timedelta(minutes=minutos) <= fecha:
        partes = [inicio + timedelta(minutes=BLOCO * b) for b in range(blocos(minutos))]
        livre = inicio > datetime.now() and not any(p in ocupados for p in partes)
        lista.append((inicio, livre))
        inicio += timedelta(minutes=BLOCO)
    return lista


def dias_abertos(quantos: int = 6) -> list:
    dias, dia = [], amanha()
    while len(dias) < quantos:
        if atende(dia):
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def horarios_livres(minutos: int, quantos_dias: int = 6) -> list:
    ocupados = blocos_ocupados()
    return [h.strftime(FORMATO_SLOT) for dia in dias_abertos(quantos_dias)
            for h, livre in horarios_do_dia(dia, minutos, ocupados) if livre]


def livres_por_servico() -> dict:
    return {nome: horarios_livres(s["minutos"]) for nome, s in servicos().items()}
