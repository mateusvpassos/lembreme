const stack = document.getElementById('stack');
const shown = new Set();
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

// som curto sintetizado (dois tons), sem arquivo de áudio
let ctx;
function chime() {
  try {
    ctx ||= new AudioContext();
    const t = ctx.currentTime;
    [[880, 0], [1318.5, .14]].forEach(([f, dt]) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = f;
      g.gain.setValueAtTime(0, t + dt);
      g.gain.linearRampToValueAtTime(.22, t + dt + .015);
      g.gain.exponentialRampToValueAtTime(.001, t + dt + .9);
      o.connect(g).connect(ctx.destination);
      o.start(t + dt);
      o.stop(t + dt + 1);
    });
  } catch {}
}

function card(a) {
  const d = fromLocal(a.due);
  const el = document.createElement('div');
  el.className = 'card' + (a.late ? ' late' : '');
  el.dataset.key = a.key;
  el.innerHTML = `
    <div class="top"><img src="icon.png" alt=""><b>Lembreme</b><span>· ${a.late ? `${dayLabel(d).toLowerCase()} ` : ''}${hhmm(d)}</span>
      ${a.late ? '<span class="tag">atrasado</span>' : ''}
      <button class="close" data-a="done" title="Fechar">${icon('x', 14)}</button></div>
    <div class="msg" data-a="open" title="Abrir o Lembreme">${esc(a.message)}</div>
    <div class="meta">${a.recurrence !== 'unica' ? `<span class="badge">${icon('repeat', 11)}${REP[a.recurrence]}</span>` : ''}</div>
    <div class="row">
      <span class="lbl2">Adiar</span>
      <button data-a="snooze" data-m="10">10 min</button>
      <button data-a="snooze" data-m="60">1 h</button>
      <button data-a="snooze" data-m="${minutesToTomorrow9()}">Amanhã 9h</button>
      <button class="primary" data-a="done">${icon('check', 14)}Ok</button>
    </div>`;
  el.addEventListener('click', e => {
    const b = e.target.closest('[data-a]');
    if (!b) return;
    el.classList.add('out');
    setTimeout(() => api.popupAction(a.key, b.dataset.a, +b.dataset.m || 0), 180);
  });
  return el;
}

function minutesToTomorrow9() {
  const t = new Date();
  t.setDate(t.getDate() + 1);
  t.setHours(9, 0, 0, 0);
  return Math.round((t - Date.now()) / 60000);
}

api.onAlerts(alerts => {
  const keys = new Set(alerts.map(a => a.key));
  for (const el of [...stack.children]) if (!keys.has(el.dataset.key)) el.remove();
  let fresh = false;
  for (const a of alerts) {
    if (shown.has(a.key)) continue;
    shown.add(a.key);
    stack.append(card(a));
    fresh = true;
  }
  if (fresh) chime();
  requestAnimationFrame(() => api.popupSize(stack.scrollHeight));
});

new ResizeObserver(() => api.popupSize(stack.scrollHeight)).observe(stack);
