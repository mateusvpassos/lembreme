from datetime import datetime

import pytest

from lembreme.parser import ParseError, next_occurrence, parse

NOW = datetime(2026, 10, 7, 14, 30)  # quarta


@pytest.mark.parametrize("txt, when, msg, rec", [
    ("amanhã 8h ligar dentista", datetime(2026, 10, 8, 8, 0), "ligar dentista", "unica"),
    ("me lembra de pagar luz 10/10 9:00 mensal", datetime(2026, 10, 10, 9, 0), "pagar luz", "mensal"),
    ("em 30 min tirar bolo", datetime(2026, 10, 7, 15, 0), "tirar bolo", "unica"),
    ("daqui 2 horas varal", datetime(2026, 10, 7, 16, 30), "varal", "unica"),
    ("toda segunda 7h academia", datetime(2026, 10, 12, 7, 0), "academia", "semanal"),
    ("todo dia 5 pagar aluguel", datetime(2026, 11, 5, 9, 0), "pagar aluguel", "mensal"),
    ("todo dia 22h remédio", datetime(2026, 10, 7, 22, 0), "remédio", "diaria"),
    ("10h reunião", datetime(2026, 10, 8, 10, 0), "reunião", "unica"),
    ("16:45 buscar filho", datetime(2026, 10, 7, 16, 45), "buscar filho", "unica"),
    ("sexta às 18 cerveja", datetime(2026, 10, 9, 18, 0), "cerveja", "unica"),
    ("quarta 10h pão", datetime(2026, 10, 14, 10, 0), "pão", "unica"),
    ("05/01 renovar CNH", datetime(2027, 1, 5, 9, 0), "renovar CNH", "unica"),
    ("dia 20 IPVA", datetime(2026, 10, 20, 9, 0), "IPVA", "unica"),
    ("pagar 15 boletos hoje 20h30", datetime(2026, 10, 7, 20, 30), "pagar 15 boletos", "unica"),
])
def test_parse(txt, when, msg, rec):
    p = parse(txt, NOW)
    assert (p.when, p.message, p.recurrence) == (when, msg, rec)


@pytest.mark.parametrize("txt", ["comprar leite", "amanhã 8h", "32/10 x", "25h x"])
def test_erros(txt):
    with pytest.raises(ParseError):
        parse(txt, NOW)


def test_mensal_dia_31_nao_deriva():
    d = datetime(2026, 1, 31, 9, 0)
    d = next_occurrence(d, "mensal", 31)
    assert d.day == 28
    d = next_occurrence(d, "mensal", 31)
    assert d.day == 31
