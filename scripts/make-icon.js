// Gera renderer/icon.png (512x512) a partir de assets/icon.svg usando o próprio Electron.
// Uso: npm run icon
const { app, BrowserWindow } = require('electron');
const fs = require('fs');
const path = require('path');

app.whenReady().then(async () => {
  const svg = fs.readFileSync(path.join(__dirname, '..', 'assets', 'icon.svg'), 'utf8');
  const win = new BrowserWindow({ show: false, width: 512, height: 512, transparent: true, frame: false });
  const html = `<html><body style="margin:0;background:transparent">${svg.replace('<svg ', '<svg width="512" height="512" ')}</body></html>`;
  await win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  await new Promise(r => setTimeout(r, 300));
  const img = await win.webContents.capturePage({ x: 0, y: 0, width: 512, height: 512 });
  fs.writeFileSync(path.join(__dirname, '..', 'renderer', 'icon.png'), img.resize({ width: 512, height: 512 }).toPNG());
  console.log('renderer/icon.png gerado');
  app.quit();
});
