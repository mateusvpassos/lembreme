// Formatação de datas em português (janela e popup).
const pad2 = n => String(n).padStart(2, '0');
const DIAS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
const DIAS_C = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const REP = { unica: 'Não repetir', diaria: 'Todo dia', semanal: 'Toda semana', mensal: 'Todo mês', anual: 'Todo ano' };

const toLocal = d => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
function fromLocal(s) {
  const [, y, mo, d, h, mi] = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(s).map(Number);
  return new Date(y, mo - 1, d, h, mi);
}
const startOfDay = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());
const dayDiff = (a, b) => Math.round((startOfDay(a) - startOfDay(b)) / 864e5);
const hhmm = d => `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;

// "Hoje", "Amanhã", "Ontem", "Sáb, 18 out"
function dayLabel(d, now = new Date()) {
  const diff = dayDiff(d, now);
  if (diff === 0) return 'Hoje';
  if (diff === 1) return 'Amanhã';
  if (diff === -1) return 'Ontem';
  const y = d.getFullYear() !== now.getFullYear() ? ` ${d.getFullYear()}` : '';
  const wd = DIAS_C[d.getDay()];
  return `${wd[0].toUpperCase() + wd.slice(1)}, ${d.getDate()} ${MESES[d.getMonth()]}${y}`;
}

// "em 25 min", "em 3 h", "em 2 dias", "há 10 min"
function relative(d, now = new Date()) {
  const min = Math.round((d - now) / 60000);
  const abs = Math.abs(min);
  let s;
  if (abs < 1) return 'agora';
  if (abs < 60) s = `${abs} min`;
  else if (abs < 60 * 24) {
    const h = Math.floor(abs / 60), m = abs % 60;
    s = m && h < 10 ? `${h} h ${m} min` : `${h} h`;
  } else {
    const days = Math.abs(dayDiff(d, now));
    s = days === 1 ? '1 dia' : `${days} dias`;
  }
  return min > 0 ? `em ${s}` : `há ${s}`;
}

// frase do resumo: "e depois todo mês no dia 10"
function repeatPhrase(rep, d) {
  switch (rep) {
    case 'diaria': return `e depois todo dia às ${hhmm(d)}`;
    case 'semanal': return `e depois ${d.getDay() % 6 ? 'toda' : 'todo'} ${DIAS[d.getDay()]}`;
    case 'mensal': return `e depois todo dia ${d.getDate()} de cada mês${d.getDate() > 28 ? ' (ou o último dia, em meses mais curtos)' : ''}`;
    case 'anual': return `e depois todo ano em ${d.getDate()} de ${MESES[d.getMonth()]}`;
    default: return '';
  }
}
