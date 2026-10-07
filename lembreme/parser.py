"""Interpreta frases em português tipo "amanhã 8h ligar dentista"."""
import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# mapa 1:1 (mesmo comprimento) para que os spans do regex valham no texto original
_ACENTOS = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç", "aaaaaeeeeiiiiooooouuuuc")

WEEKDAYS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
_WD = "|".join(WEEKDAYS)

RECURRENCES = ("unica", "diaria", "semanal", "mensal", "anual")


class ParseError(ValueError):
    pass


@dataclass
class Parsed:
    when: datetime
    message: str
    recurrence: str = "unica"
    anchor_day: int | None = None  # dia original p/ recorrência mensal


def _norm(s: str) -> str:
    return s.lower().translate(_ACENTOS)


class _Text:
    """Texto original + versão normalizada; trechos consumidos viram espaço."""

    def __init__(self, s: str):
        self.orig = s
        self.norm = _norm(s)

    def take(self, pattern: str):
        m = re.search(pattern, self.norm)
        if m:
            a, b = m.span()
            self.orig = self.orig[:a] + " " * (b - a) + self.orig[b:]
            self.norm = self.norm[:a] + " " * (b - a) + self.norm[b:]
        return m

    def rest(self) -> str:
        msg = " ".join(self.orig.split())
        msg = re.sub(r"^(?:(?:de|que|pra|para|a|as|às)\s+)+", "", msg, flags=re.I)
        msg = re.sub(r"\s+(?:de|as|às|a|no|na|em)$", "", msg, flags=re.I)
        return msg.strip(" ,.-")


def _clamp_day(y: int, m: int, d: int) -> date:
    return date(y, m, min(d, calendar.monthrange(y, m)[1]))


def _add_months(d: date, n: int, anchor: int) -> date:
    m = d.month - 1 + n
    return _clamp_day(d.year + m // 12, m % 12 + 1, anchor)


def next_occurrence(dt: datetime, recurrence: str, anchor_day: int | None = None) -> datetime | None:
    if recurrence == "diaria":
        return dt + timedelta(days=1)
    if recurrence == "semanal":
        return dt + timedelta(days=7)
    if recurrence == "mensal":
        return datetime.combine(_add_months(dt.date(), 1, anchor_day or dt.day), dt.time())
    if recurrence == "anual":
        return datetime.combine(_clamp_day(dt.year + 1, dt.month, anchor_day or dt.day), dt.time())
    return None


def parse(text: str, now: datetime | None = None) -> Parsed:
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    t = _Text(" " + text.strip() + " ")
    t.take(r"^\s*(?:me\s+)?lembr(?:a|ar|e|ete)\b(?:\s+(?:de|que))?")

    recurrence = "unica"
    day: date | None = None
    weekday: int | None = None
    month_day: int | None = None
    hm: time | None = None

    # --- recorrência (algumas já trazem a data) ---
    if m := t.take(rf"\btod[ao]s?\s+(?:as\s+|os\s+)?({_WD})s?(?:-feiras?)?\b"):
        recurrence, weekday = "semanal", WEEKDAYS.index(m.group(1))
    elif m := t.take(r"\btodo\s+dia\s+(\d{1,2})\b"):
        recurrence, month_day = "mensal", int(m.group(1))
    elif t.take(r"\b(?:todo\s+dia|todos\s+os\s+dias|diariamente|diari[ao])\b"):
        recurrence = "diaria"
    elif t.take(r"\b(?:toda\s+semana|semanalmente|semanal)\b"):
        recurrence = "semanal"
    elif t.take(r"\b(?:todo\s+mes|mensalmente|mensal)\b"):
        recurrence = "mensal"
    elif t.take(r"\b(?:todo\s+ano|anualmente|anual)\b"):
        recurrence = "anual"

    # --- relativo: "em 2h", "daqui 10 minutos" ---
    if m := t.take(r"\b(?:em|daqui(?:\s+a)?)\s+(\d+)\s*(minutos?|mins?|m|horas?|h|dias?|d)\b"):
        n, unit = int(m.group(1)), m.group(2)[0]
        delta = {"m": timedelta(minutes=n), "h": timedelta(hours=n), "d": timedelta(days=n)}[unit]
        msg = t.rest()
        if not msg:
            raise ParseError("Faltou o texto do lembrete.")
        when = now + delta
        return Parsed(when, msg, recurrence, when.day)

    # --- data ---
    if m := t.take(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b"):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        year = (int(y) + 2000 if len(y) == 2 else int(y)) if y else now.year
        try:
            day = date(year, mo, d)
        except ValueError:
            raise ParseError(f"Data inválida: {m.group(0).strip()}")
        if not y and day < now.date():
            day = day.replace(year=now.year + 1)
    elif m := t.take(r"\b(depois\s+de\s+amanha|amanha|hoje)\b"):
        day = now.date() + timedelta(days={"hoje": 0, "amanha": 1}.get(m.group(1), 2))
    elif weekday is None and (m := t.take(rf"\b(?:n[ao]\s+)?({_WD})(?:-feira)?\b")):
        weekday = WEEKDAYS.index(m.group(1))
    elif month_day is None and (m := t.take(r"\bdia\s+(\d{1,2})\b")):
        month_day = int(m.group(1))

    # --- hora: 9h, 9h30, 09:00, às 9 ---
    if m := t.take(r"\b(?:as\s+|a\s+)?(\d{1,2})(?::(\d{2})|h(\d{2})?)\b"):
        h, mi = int(m.group(1)), int(m.group(2) or m.group(3) or 0)
    elif m := t.take(r"\bas\s+(\d{1,2})\b"):
        h, mi = int(m.group(1)), 0
    else:
        h = mi = None
    if h is not None:
        if h > 23 or mi > 59:
            raise ParseError("Hora inválida.")
        hm = time(h, mi)

    msg = t.rest()
    if not msg:
        raise ParseError("Faltou o texto do lembrete.")

    if day is None and weekday is None and month_day is None and hm is None and recurrence == "unica":
        raise ParseError('Não entendi quando. Ex.: "amanhã 8h ...", "10/10 9:00 ...", "em 30 min ..."')

    hm_eff = hm or time(9, 0)

    if weekday is not None:
        ahead = (weekday - now.weekday()) % 7
        day = now.date() + timedelta(days=ahead)
        if datetime.combine(day, hm_eff) <= now:
            day += timedelta(days=7)
    elif month_day is not None:
        if not 1 <= month_day <= 31:
            raise ParseError("Dia inválido.")
        day = _clamp_day(now.year, now.month, month_day)
        if datetime.combine(day, hm_eff) <= now:
            day = _add_months(day, 1, month_day)
    elif day is None:
        day = now.date()
        if datetime.combine(day, hm_eff) <= now:
            day += timedelta(days=1)

    when = datetime.combine(day, hm_eff)
    return Parsed(when, msg, recurrence, month_day or when.day)


def describe(p: Parsed) -> str:
    dias = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    s = f"{dias[p.when.weekday()]} {p.when:%d/%m/%Y %H:%M}"
    if p.recurrence != "unica":
        s += f" · {p.recurrence}"
    return f"{s} · {p.message}"
