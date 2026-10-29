const $ = s => document.querySelector(s);
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

const state = {
  list: [],
  tab: 'next',
  editing: null,       // id em edição
  rep: 'unica',
  type: 'outro',
  typeManual: false,   // escolhido à mão: para de sugerir pelo texto
  filter: 'all',
  selected: null
};

const msgEl = $('#f-msg'), dateEl = $('#f-date'), timeEl = $('#f-time');

// ---------- formulário ----------
const QUICK = [
  { label: 'Em 10 min', at: () => addMin(10) },
  { label: 'Em 1 hora', at: () => addMin(60) },
  { label: 'Hoje 18:00', at: () => at(0, 18) },
  { label: 'Amanhã 09:00', at: () => at(1, 9) },
  { label: 'Segunda 09:00', at: () => at((8 - new Date().getDay()) % 7 || 7, 9) }
];
function addMin(m) {
  const d = new Date(Date.now() + m * 60000);
  d.setSeconds(0, 0);
  return d;
}
function at(days, h) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(h, 0, 0, 0);
  return d;
}

function buildForm() {
  $('#quick').innerHTML = QUICK.map((q, i) => `<button data-q="${i}" tabindex="-1">${q.label}</button>`).join('');
  $('#quick').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    setWhen(QUICK[+b.dataset.q].at());
    msgEl.focus();
  });

  const SEG = { unica: 'Uma vez', diaria: 'Diário', semanal: 'Semanal', mensal: 'Mensal', anual: 'Anual' };
  $('#f-rep').innerHTML = Object.entries(SEG).map(([k, v]) => `<button data-rep="${k}" title="${REP[k]}">${v}</button>`).join('');
  $('#f-rep').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (b) setRep(b.dataset.rep);
  });

  $('#f-type').innerHTML = Object.entries(TYPES).map(([k, t]) =>
    `<button data-type="${k}" style="--c:${t.color}">${icon(t.icon, 14)}${t.label}</button>`).join('');
  $('#f-type').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    state.typeManual = true;
    setType(b.dataset.type);
  });
  msgEl.addEventListener('input', () => {
    if (state.typeManual) return;
    setType(guessType(msgEl.value) || 'outro', true);
  });

  for (const el of [msgEl, dateEl, timeEl]) {
    el.addEventListener('input', () => { clearErr(); updateSummary(); });
    el.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
  }
  // clicar em qualquer parte do campo abre o seletor nativo
  for (const f of document.querySelectorAll('.field')) {
    f.addEventListener('click', () => { try { f.querySelector('input').showPicker(); } catch {} });
  }
  $('#btn-save').addEventListener('click', submit);
  $('#btn-cancel').addEventListener('click', resetForm);
  $('#btn-new').addEventListener('click', resetForm);
}

function setWhen(d) {
  dateEl.value = toLocal(d).slice(0, 10);
  timeEl.value = hhmm(d);
  updateSummary();
}
function setType(k, auto = false) {
  state.type = k;
  for (const b of $('#f-type').children) b.classList.toggle('on', b.dataset.type === k);
  $('#type-note').textContent = auto && k !== 'outro' ? '· sugerido pelo texto' : '';
}
function setRep(k) {
  state.rep = k;
  for (const b of $('#f-rep').children) b.classList.toggle('on', b.dataset.rep === k);
  updateSummary();
}

function formDue() {
  if (!dateEl.value || !timeEl.value) return null;
  return `${dateEl.value}T${timeEl.value}`;
}

function updateSummary() {
  const el = $('#summary');
  const due = formDue();
  // destaca o atalho que corresponde ao horário escolhido
  for (const b of $('#quick').children) b.classList.toggle('on', due === toLocal(QUICK[+b.dataset.q].at()));
  if (!due) {
    el.className = 'summary warn';
    el.innerHTML = `${icon('alert')}<div>Escolha o dia e a hora.</div>`;
    return;
  }
  const d = fromLocal(due), now = new Date();
  if (d <= now && state.rep === 'unica') {
    el.className = 'summary warn';
    el.innerHTML = `${icon('alert')}<div>Esse horário já passou. Escolha um horário futuro.</div>`;
    return;
  }
  const what = msgEl.value.trim() ? `<b>“${esc(msgEl.value.trim())}”</b>` : 'O aviso';
  const quando = `${dayLabel(d, now).toLowerCase().replace(/^(seg|ter|qua|qui|sex|sáb|dom)/, m => DIAS[DIAS_C.indexOf(m)])} às ${hhmm(d)}`;
  const rep = repeatPhrase(state.rep, d);
  el.className = 'summary';
  el.innerHTML = `${icon('bellRing')}<div>${what} vai aparecer no canto da tela <b>${quando}</b> (${relative(d, now)})${rep ? ` ${rep}` : ''}.</div>`;
}

function showErr(text, field) {
  $('#err-msg').textContent = text;
  (field?.closest('.field') || field)?.classList.add('invalid');
  field?.focus();
}
function clearErr() {
  $('#err-msg').textContent = '';
  for (const el of document.querySelectorAll('.invalid')) el.classList.remove('invalid');
}

async function submit() {
  clearErr();
  const message = msgEl.value.trim();
  if (!message) return showErr('Escreva o que lembrar.', msgEl);
  const due = formDue();
  if (!due) return showErr('Escolha dia e hora.', dateEl.value ? timeEl : dateEl);
  const res = await api.save({ id: state.editing, message, due, recurrence: state.rep, type: state.type });
  if (res.error) return showErr(res.error, res.error.includes('horário') ? timeEl : msgEl);
  const d = fromLocal(due);
  toast(`${state.editing ? 'Alterado' : 'Criado'} · ${dayLabel(d)} às ${hhmm(d)}`);
  state.tab = 'next';
  resetForm();
}

function resetForm() {
  state.editing = null;
  state.selected = null;
  msgEl.value = '';
  const d = new Date();
  d.setHours(d.getHours() + 1, 0, 0, 0);
  dateEl.min = toLocal(new Date()).slice(0, 10);
  setWhen(d);
  setRep('unica');
  state.typeManual = false;
  setType('outro');
  clearErr();
  $('#composer').classList.remove('editing');
  $('#form-title').textContent = 'Novo lembrete';
  $('#btn-save span').textContent = 'Adicionar lembrete';
  $('#btn-save .ic').outerHTML = icon('plus');
  $('#btn-cancel').classList.add('hidden');
  $('#btn-new').classList.add('hidden');
  render();
  msgEl.focus();
}

function loadIntoForm(r, asCopy = false) {
  state.editing = asCopy ? null : r.id;
  state.selected = asCopy ? null : r.id;
  msgEl.value = r.message;
  let d = fromLocal(r.due);
  if (asCopy && d <= new Date()) d = at(1, d.getHours());
  setWhen(d);
  setRep(asCopy ? 'unica' : r.recurrence);
  state.typeManual = true;
  setType(r.type || 'outro');
  clearErr();
  $('#composer').classList.toggle('editing', !asCopy);
  $('#form-title').textContent = asCopy ? 'Novo lembrete (cópia)' : 'Editando lembrete';
  $('#btn-save span').textContent = asCopy ? 'Adicionar lembrete' : 'Salvar alterações';
  $('#btn-save .ic').outerHTML = icon(asCopy ? 'plus' : 'check');
  $('#btn-cancel').classList.toggle('hidden', asCopy);
  $('#btn-new').classList.toggle('hidden', asCopy);
  render();
  msgEl.focus();
  msgEl.select();
}

// ---------- lista ----------
function groupOf(d, now) {
  const diff = dayDiff(d, now);
  if (d <= now) return ['late', 'Atrasados'];
  if (diff === 0) return ['today', 'Hoje'];
  if (diff === 1) return ['tomorrow', 'Amanhã'];
  if (diff < 7) return ['week', 'Próximos 7 dias'];
  return ['later', 'Mais adiante'];
}

function itemHtml(r, now) {
  const d = fromLocal(r.due);
  const cls = r.done ? 'done' : d <= now ? 'late' : dayDiff(d, now) === 0 ? 'today' : '';
  const t = TYPES[r.type] || TYPES.outro;
  const rep = r.recurrence !== 'unica' ? `<span class="badge">${icon('repeat', 11)}${REP[r.recurrence]}</span>` : '';
  const rel = r.done ? `avisado ${dayLabel(d, now).toLowerCase()} às ${hhmm(d)}` : relative(d, now);
  const acts = r.done
    ? `<button data-act="copy" title="Criar de novo">${icon('copy')}</button>`
    : `<button data-act="edit" title="Editar">${icon('pencil')}</button>`;
  return `
    <div class="item ${cls} ${state.selected === r.id ? 'selected' : ''}" data-id="${r.id}" tabindex="0">
      <div class="when-col"><span class="t">${hhmm(d)}</span><span class="d">${dayLabel(d, now)}</span></div>
      <div class="type-tile" style="--c:${t.color}" title="${t.label}">${icon(t.icon, 15)}</div>
      <div class="body"><div class="msg" title="${esc(r.message)}">${esc(r.message)}</div><div class="meta">${r.type && r.type !== 'outro' ? `<span class="type-name" style="--c:${t.color}">${t.label}</span>` : ''}${rep}<span>${rel}</span></div></div>
      <div class="acts">${acts}<button data-act="del" class="danger" title="Excluir (Delete)">${icon('trash')}</button></div>
    </div>`;
}

function render() {
  const now = new Date();
  const allNext = state.list.filter(r => !r.done).sort((a, b) => a.due.localeCompare(b.due));
  const allDone = state.list.filter(r => r.done).sort((a, b) => (b.doneAt || b.due).localeCompare(a.doneAt || a.due));
  renderFilters(state.tab === 'next' ? allNext : allDone);
  const pass = r => state.filter === 'all' || (r.type || 'outro') === state.filter;
  const next = allNext.filter(pass), done = allDone.filter(pass);
  $('#count-next').textContent = allNext.length || '';
  $('#count-done').textContent = allDone.length || '';
  for (const t of document.querySelectorAll('.tab')) t.classList.toggle('on', t.dataset.tab === state.tab);
  $('#btn-clear').classList.toggle('hidden', state.tab !== 'done' || !done.length);

  const box = $('#items');
  if (state.tab === 'next') {
    if (!next.length) {
      box.innerHTML = `<div class="empty"><img src="icon.png" alt=""><b>Nada pendente</b><span>Crie um lembrete ao lado e ele aparece aqui.</span></div>`;
    } else {
      const groups = new Map();
      for (const r of next) {
        const [k, title] = groupOf(fromLocal(r.due), now);
        if (!groups.has(k)) groups.set(k, { title, items: [] });
        groups.get(k).items.push(r);
      }
      box.innerHTML = [...groups].map(([k, g]) =>
        `<div class="group ${k}"><div class="group-title">${g.title}</div>${g.items.map(r => itemHtml(r, now)).join('')}</div>`).join('');
    }
  } else {
    box.innerHTML = done.length
      ? `<div class="group"><div class="group-title">Já avisados</div>${done.slice(0, 100).map(r => itemHtml(r, now)).join('')}</div>`
      : `<div class="empty"><img src="icon.png" alt=""><b>Nenhum concluído</b><span>Lembretes que já tocaram (e não repetem) ficam aqui.</span></div>`;
  }

  // pílula do próximo na barra de título
  const pill = $('#next-pill');
  if (allNext.length) {
    const d = fromLocal(allNext[0].due);
    pill.innerHTML = `${icon('bell', 13)}<span>Próximo: <b>${esc(allNext[0].message)}</b> · ${dayLabel(d, now).toLowerCase()} ${hhmm(d)}</span>`;
    pill.classList.remove('hidden');
  } else pill.classList.add('hidden');
}

// filtro por tipo (só aparecem os tipos que existem na aba)
function renderFilters(items) {
  const counts = {};
  for (const r of items) counts[r.type || 'outro'] = (counts[r.type || 'outro'] || 0) + 1;
  const used = Object.keys(TYPES).filter(k => counts[k]);
  if (state.filter !== 'all' && !counts[state.filter]) state.filter = 'all';
  const box = $('#filters');
  box.classList.toggle('hidden', used.length < 2);
  box.innerHTML = `<button data-f="all" class="${state.filter === 'all' ? 'on' : ''}">Todos <span class="count">${items.length}</span></button>` +
    used.map(k => `<button data-f="${k}" style="--c:${TYPES[k].color}" class="${state.filter === k ? 'on' : ''}">${icon(TYPES[k].icon, 13)}${TYPES[k].label} <span class="count">${counts[k]}</span></button>`).join('');
}
$('#filters').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  state.filter = b.dataset.f;
  render();
});

$('#items').addEventListener('click', e => {
  const it = e.target.closest('.item');
  if (!it) return;
  const r = state.list.find(x => x.id === it.dataset.id);
  const act = e.target.closest('button')?.dataset.act;
  if (act === 'del') return del(r);
  if (r.done) return loadIntoForm(r, true);
  loadIntoForm(r);
});
$('#items').addEventListener('keydown', e => {
  const it = e.target.closest('.item');
  if (!it) return;
  const r = state.list.find(x => x.id === it.dataset.id);
  if (e.key === 'Delete') del(r);
  if (e.key === 'Enter') loadIntoForm(r, r.done);
});

async function del(r) {
  const removed = await api.remove(r.id);
  if (state.editing === r.id) resetForm();
  toast(`Excluído · ${r.message}`, { label: 'Desfazer', run: () => api.restore(removed) });
}

for (const t of document.querySelectorAll('.tab')) {
  t.addEventListener('click', () => { state.tab = t.dataset.tab; render(); });
}
$('#btn-test').addEventListener('click', () => api.testPopup());
$('#btn-clear').addEventListener('click', async () => {
  const done = state.list.filter(r => r.done);
  await api.clearDone();
  toast(`${done.length} concluído(s) apagado(s)`, { label: 'Desfazer', run: async () => { for (const r of done) await api.restore(r); } });
});

// ---------- iniciar com o Windows ----------
function applySettings(s) {
  $('#opt-login').checked = s.openAtLogin;
  $('#opt-login').disabled = !s.packaged;
  $('#login-wrap').classList.toggle('disabled', !s.packaged);
  if (!s.packaged) $('#login-wrap').title = 'Disponível na versão instalada';
}
$('#opt-login').addEventListener('change', e => api.setLogin(e.target.checked));
api.onSettings(applySettings);

// ---------- toasts ----------
function toast(text, action) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = `${icon('check')}<span>${esc(text)}</span>${action ? `<button>${icon('undo', 13)}${action.label}</button>` : ''}`;
  const close = () => { el.classList.add('out'); setTimeout(() => el.remove(), 220); };
  if (action) el.querySelector('button').addEventListener('click', () => { action.run(); close(); });
  $('#toasts').append(el);
  setTimeout(close, action ? 6000 : 2600);
}

// ---------- sobre ----------
const about = $('#about');
async function openAbout() {
  const a = await api.about();
  $('#about-version').textContent = a.version;
  showNotices(false);
  about.classList.remove('hidden');
  about.querySelector('.m-close').focus();
}
const closeAbout = () => about.classList.add('hidden');
async function showNotices(on) {
  if (on && !$('#about-notices').textContent) $('#about-notices').textContent = await api.notices();
  $('#about-main').classList.toggle('hidden', on);
  $('#about-notices').classList.toggle('hidden', !on);
  $('#about-licenses span').textContent = on ? 'Voltar' : 'Licenças completas';
}
$('#btn-about').addEventListener('click', openAbout);
api.onAbout(openAbout);
about.querySelector('.m-close').addEventListener('click', closeAbout);
about.addEventListener('pointerdown', e => { if (e.target === about) closeAbout(); });
$('#about-licenses').addEventListener('click', () => showNotices($('#about-notices').classList.contains('hidden')));
for (const b of about.querySelectorAll('[data-link]')) b.addEventListener('click', () => api.openLink(b.dataset.link));

// ---------- atalhos ----------
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !about.classList.contains('hidden')) { closeAbout(); return; }
  if (e.ctrlKey && e.key.toLowerCase() === 'n') { e.preventDefault(); resetForm(); }
  if (e.key === 'Escape' && (state.editing || state.selected)) resetForm();
});

// ---------- início ----------
hydrateIcons();
buildForm();
api.onChanged(list => { state.list = list; render(); updateSummary(); });
(async () => {
  state.list = await api.list();
  applySettings(await api.settings());
  resetForm();
})();
setInterval(() => { render(); updateSummary(); }, 30_000);
