const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, screen, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { toLocal, fromLocal, nextAfter } = require('./shared/recur');
const { TYPES, guessType } = require('./renderer/types');

app.setName('Lembreme');
app.setAppUserModelId('com.mateusvpassos.lembreme');
// desenvolvimento/testes: pasta de dados separada
if (process.env.LEMBREME_DATA) app.setPath('userData', process.env.LEMBREME_DATA);

const ICON = path.join(__dirname, 'renderer', 'icon.png');
const startHidden = process.argv.includes('--oculto');
const dataFile = () => path.join(app.getPath('userData'), 'lembretes.json');
const uniq = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const REP_LABEL = { diaria: 'Todo dia', semanal: 'Toda semana', mensal: 'Todo mês', anual: 'Todo ano' };

let win, tray, popup;
let quitting = false;
let db = { reminders: [], settings: {} };
let alerts = [];

// log simples em %APPDATA%\Lembreme\lembreme.log (diagnóstico de inicialização)
function log(...a) {
  try {
    const f = path.join(app.getPath('userData'), 'lembreme.log');
    if (fs.existsSync(f) && fs.statSync(f).size > 256 * 1024) fs.renameSync(f, f + '.1');
    fs.appendFileSync(f, `${new Date().toISOString()} ${a.map(x => x?.stack || (typeof x === 'string' ? x : JSON.stringify(x))).join(' ')}
`);
  } catch {}
}
process.on('uncaughtException', e => log('ERRO', e));
process.on('unhandledRejection', e => log('ERRO (promise)', e));

// ---------- dados ----------
function load() {
  if (!fs.existsSync(dataFile())) {
    db = { reminders: migrateFromPython(), settings: {} };
    save();
  } else {
    try {
      db = JSON.parse(fs.readFileSync(dataFile(), 'utf8'));
    } catch (e) {
      // arquivo corrompido: guarda uma cópia em vez de sobrescrever os lembretes
      const bak = dataFile() + '.corrompido-' + Date.now();
      fs.copyFileSync(dataFile(), bak);
      log('lembretes.json ilegível, cópia em', bak, e);
      db = { reminders: [], settings: {} };
      save();
    }
  }
  db.reminders ||= [];
  db.settings ||= {};
  // lembretes antigos ganham um tipo sugerido pelo texto
  let touched = false;
  for (const r of db.reminders) {
    if (!r.type) { r.type = guessType(r.message) || 'outro'; touched = true; }
  }
  if (touched) save();
}

function save() {
  const f = dataFile();
  fs.writeFileSync(f + '.tmp', JSON.stringify(db, null, 1));
  fs.renameSync(f + '.tmp', f);
}

// a primeira versão (Python) guardava em lembreme.db na mesma pasta
function migrateFromPython() {
  const old = path.join(app.getPath('userData'), 'lembreme.db');
  if (!fs.existsSync(old)) return [];
  try {
    const { DatabaseSync } = require('node:sqlite');
    const rows = new DatabaseSync(old, { readOnly: true })
      .prepare('SELECT message, due, recurrence, anchor_day, active, created FROM reminders').all();
    return rows.map(r => ({
      id: uniq(), message: r.message, due: r.due.slice(0, 16), recurrence: r.recurrence,
      anchorDay: r.anchor_day || null, done: !r.active, created: r.created
    }));
  } catch (e) {
    console.error('migração falhou', e);
    return [];
  }
}

function changed() {
  save();
  win?.webContents.send('changed', db.reminders);
  updateTray();
}

function validate(r) {
  if (!r.message?.trim()) return 'Escreva o que lembrar.';
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(r.due || '')) return 'Escolha dia e hora.';
  if (!['unica', ...Object.keys(REP_LABEL)].includes(r.recurrence)) return 'Repetição inválida.';
  if (r.recurrence === 'unica' && fromLocal(r.due) <= new Date()) return 'Esse horário já passou.';
  if (r.type && !TYPES[r.type]) return 'Tipo inválido.';
  return null;
}

// ---------- agendador ----------
function tick() {
  const now = new Date();
  let fired = false;
  for (const r of db.reminders) {
    if (r.done || fromLocal(r.due) > now) continue;
    alerts.push({
      key: uniq(), id: r.id, message: r.message, due: r.due, recurrence: r.recurrence, type: r.type,
      late: now - fromLocal(r.due) > 2 * 60_000
    });
    if (r.recurrence === 'unica') {
      r.done = true;
      r.doneAt = toLocal(now);
    } else {
      r.due = nextAfter(r.due, r.recurrence, r.anchorDay, now);
    }
    fired = true;
  }
  if (fired) {
    changed();
    showAlerts();
  }
}

// ---------- popup no canto ----------
const POPUP_W = 404;

function showAlerts() {
  if (!alerts.length) {
    popup?.hide();
    return;
  }
  if (!popup) {
    popup = new BrowserWindow({
      width: POPUP_W, height: 200, frame: false, transparent: true, resizable: false, movable: false,
      skipTaskbar: true, alwaysOnTop: true, focusable: false, show: false, hasShadow: false,
      backgroundColor: '#00000000',
      webPreferences: { preload: path.join(__dirname, 'preload.js'), autoplayPolicy: 'no-user-gesture-required' }
    });
    popup.setAlwaysOnTop(true, 'screen-saver');
    popup.loadFile(path.join(__dirname, 'renderer', 'popup.html'));
    popup.webContents.once('did-finish-load', () => popup.webContents.send('alerts', alerts));
    popup.on('closed', () => { popup = null; });
    return;
  }
  popup.webContents.send('alerts', alerts);
}

ipcMain.on('popup-size', (_, h) => {
  if (!popup) return;
  const wa = screen.getPrimaryDisplay().workArea;
  const height = Math.min(Math.ceil(h), wa.height);
  popup.setBounds({ x: wa.x + wa.width - POPUP_W, y: wa.y + wa.height - height, width: POPUP_W, height });
  if (alerts.length && !popup.isVisible()) popup.showInactive();
});

ipcMain.on('popup-action', (_, key, action, minutes) => {
  const a = alerts.find(x => x.key === key);
  alerts = alerts.filter(x => x.key !== key);
  if (a && action === 'snooze') {
    const due = new Date(Date.now() + minutes * 60_000);
    due.setSeconds(0, 0);
    db.reminders.push({ id: uniq(), message: a.message, type: a.type, due: toLocal(due), recurrence: 'unica', created: toLocal(new Date()) });
    changed();
  }
  if (a && action === 'open') showWindow();
  showAlerts();
});

function testPopup() {
  const now = new Date();
  alerts.push({ key: uniq(), id: null, message: 'Teste: é assim que o lembrete aparece', type: 'conta', due: toLocal(now), recurrence: 'unica', late: false });
  showAlerts();
}

// ---------- janela ----------
function createWindow() {
  win = new BrowserWindow({
    width: 1000, height: 760, minWidth: 800, minHeight: 600,
    title: 'Lembreme', icon: ICON, show: false,
    backgroundColor: '#0d0e13',
    titleBarStyle: 'hidden',
    titleBarOverlay: { color: '#0d0e13', symbolColor: '#8b90a4', height: 40 },
    webPreferences: { preload: path.join(__dirname, 'preload.js') }
  });
  win.removeMenu();
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.once('ready-to-show', () => { if (!startHidden) win.show(); });
  // fechar só esconde: continua avisando pela bandeja
  win.on('close', e => {
    if (quitting) return;
    e.preventDefault();
    win.hide();
  });
  // desligar/reiniciar o Windows: sai de verdade (antes o "esconder" bloqueava o desligamento)
  win.on('query-session-end', () => { quitting = true; log('fim de sessão do Windows'); });
  win.on('session-end', () => { quitting = true; app.quit(); });
}

function showWindow() {
  if (!win) return;
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
}

// ---------- bandeja ----------
function updateTray() {
  if (!tray) return;
  const now = new Date();
  const next = db.reminders.filter(r => !r.done).sort((a, b) => a.due.localeCompare(b.due))[0];
  let tip = 'Lembreme';
  if (next) {
    const d = fromLocal(next.due);
    const day = d.toDateString() === now.toDateString() ? 'hoje' : d.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' });
    tip += `\nPróximo: ${day} ${next.due.slice(11)} · ${next.message}`;
  }
  tray.setToolTip(tip.slice(0, 127));
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Abrir Lembreme', click: showWindow },
    { label: 'Testar aviso', click: testPopup },
    { label: 'Sobre o Lembreme', click: () => { showWindow(); win?.webContents.send('about'); } },
    { type: 'separator' },
    {
      label: 'Iniciar com o Windows', type: 'checkbox', checked: loginEnabled(), enabled: app.isPackaged,
      click: i => setLogin(i.checked)
    },
    { type: 'separator' },
    { label: 'Sair', click: () => { quitting = true; app.quit(); } }
  ]));
}

// atalho na pasta Inicializar (o mesmo método do Transcritor; a chave Run não estava sendo executada)
const startupLnk = () => path.join(app.getPath('appData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'Lembreme.lnk');
const loginEnabled = () => app.isPackaged && fs.existsSync(startupLnk());
function setLogin(on) {
  if (!app.isPackaged) return;
  app.setLoginItemSettings({ openAtLogin: false, args: ['--oculto'] }); // remove a chave Run antiga
  if (on) {
    shell.writeShortcutLink(startupLnk(), 'create', {
      target: process.execPath, args: '--oculto', cwd: path.dirname(process.execPath),
      icon: process.execPath, iconIndex: 0, appUserModelId: 'com.mateusvpassos.lembreme', description: 'Lembreme'
    });
  } else {
    fs.rmSync(startupLnk(), { force: true });
  }
  log('iniciar com o Windows:', on);
  db.settings.openAtLogin = on;
  save();
  updateTray();
  win?.webContents.send('settings', settings());
}
const settings = () => ({ openAtLogin: loginEnabled(), packaged: app.isPackaged });

// no login a bandeja do Windows pode ainda não estar pronta: tenta de novo
function createTray(attempt = 1) {
  try {
    tray = new Tray(nativeImage.createFromPath(ICON).resize({ width: 32, height: 32, quality: 'best' }));
    tray.on('click', showWindow);
    updateTray();
  } catch (e) {
    log('bandeja falhou, tentativa', attempt, e);
    if (attempt < 10) setTimeout(() => createTray(attempt + 1), 5000);
  }
}

// ---------- IPC da janela ----------
ipcMain.handle('list', () => db.reminders);
ipcMain.handle('save', (_, r) => {
  const err = validate(r);
  if (err) return { error: err };
  const anchorDay = +r.due.slice(8, 10);
  const existing = r.id && db.reminders.find(x => x.id === r.id);
  if (existing) {
    Object.assign(existing, { message: r.message.trim(), type: r.type || 'outro', due: r.due, recurrence: r.recurrence, anchorDay, done: false, doneAt: undefined });
  } else {
    db.reminders.push({ id: uniq(), message: r.message.trim(), type: r.type || 'outro', due: r.due, recurrence: r.recurrence, anchorDay, created: toLocal(new Date()) });
  }
  changed();
  return { ok: true };
});
ipcMain.handle('remove', (_, id) => {
  const r = db.reminders.find(x => x.id === id);
  db.reminders = db.reminders.filter(x => x.id !== id);
  changed();
  return r;
});
ipcMain.handle('restore', (_, r) => {
  if (r && !db.reminders.some(x => x.id === r.id)) db.reminders.push(r);
  changed();
});
ipcMain.handle('clear-done', () => {
  db.reminders = db.reminders.filter(x => !x.done);
  changed();
});
ipcMain.handle('settings', () => settings());

// ---------- sobre ----------
const REPO = 'https://github.com/mateusvpassos/lembreme';
// instalado, LICENSE e avisos ficam em resources/ (extraResources); rodando do código, na raiz
const resFile = (packaged, dev) => app.isPackaged ? path.join(process.resourcesPath, packaged) : path.join(__dirname, dev);
ipcMain.handle('about', () => ({ version: app.getVersion(), electron: process.versions.electron }));
ipcMain.handle('notices', () => [resFile('LICENSE.txt', 'LICENSE'), resFile('THIRD-PARTY-NOTICES.md', 'THIRD-PARTY-NOTICES.md')]
  .map(f => { try { return fs.readFileSync(f, 'utf8'); } catch { return ''; } })
  .join('\n\n' + '─'.repeat(60) + '\n\n'));
ipcMain.handle('open-link', (_, which) => {
  const url = { repo: REPO, issues: REPO + '/issues/new/choose' }[which];
  if (url) shell.openExternal(url);
});
ipcMain.handle('set-login', (_, on) => setLogin(on));
ipcMain.on('test-popup', testPopup);

// ---------- início ----------
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', showWindow);
  app.whenReady().then(() => {
    log('iniciando', process.argv.slice(1).join(' '));
    load();
    // liga o "iniciar com o Windows" na primeira execução e migra quem usava a chave Run
    if (app.isPackaged && db.settings.openAtLogin !== false && !fs.existsSync(startupLnk())) setLogin(true);
    createWindow();
    createTray();
    tick();
    setInterval(tick, 10_000);
    setInterval(updateTray, 60_000);
  });
  app.on('window-all-closed', () => {}); // continua na bandeja
  app.on('before-quit', () => { quitting = true; log('saindo'); });
}
