// Datas locais no formato "YYYY-MM-DDTHH:mm" (sem fuso) e regras de repetição.
const pad = n => String(n).padStart(2, '0');

const toLocal = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

function fromLocal(s) {
  const [, y, mo, d, h, mi] = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(s).map(Number);
  return new Date(y, mo - 1, d, h, mi);
}

const daysIn = (y, m) => new Date(y, m + 1, 0).getDate();
const clampDate = (y, m, day, h, mi) => new Date(y, m, Math.min(day, daysIn(y, m)), h, mi);

// próxima ocorrência; anchorDay mantém o "dia 31" mesmo depois de um mês curto
function nextOccurrence(due, recurrence, anchorDay) {
  const d = fromLocal(due);
  const day = anchorDay || d.getDate();
  switch (recurrence) {
    case 'diaria': d.setDate(d.getDate() + 1); return toLocal(d);
    case 'semanal': d.setDate(d.getDate() + 7); return toLocal(d);
    case 'mensal': {
      const m = d.getMonth() + 1;
      return toLocal(clampDate(d.getFullYear() + Math.floor(m / 12), m % 12, day, d.getHours(), d.getMinutes()));
    }
    case 'anual': return toLocal(clampDate(d.getFullYear() + 1, d.getMonth(), day, d.getHours(), d.getMinutes()));
    default: return null;
  }
}

// avança até passar de `now`
function nextAfter(due, recurrence, anchorDay, now) {
  let n = nextOccurrence(due, recurrence, anchorDay);
  while (n && fromLocal(n) <= now) n = nextOccurrence(n, recurrence, anchorDay);
  return n;
}

module.exports = { pad, toLocal, fromLocal, nextOccurrence, nextAfter };
