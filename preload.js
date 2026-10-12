const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  list: () => ipcRenderer.invoke('list'),
  save: r => ipcRenderer.invoke('save', r),
  remove: id => ipcRenderer.invoke('remove', id),
  restore: r => ipcRenderer.invoke('restore', r),
  clearDone: () => ipcRenderer.invoke('clear-done'),
  settings: () => ipcRenderer.invoke('settings'),
  setLogin: on => ipcRenderer.invoke('set-login', on),
  testPopup: () => ipcRenderer.send('test-popup'),
  onChanged: cb => ipcRenderer.on('changed', (_, list) => cb(list)),
  onSettings: cb => ipcRenderer.on('settings', (_, s) => cb(s)),
  // popup
  onAlerts: cb => ipcRenderer.on('alerts', (_, a) => cb(a)),
  popupSize: h => ipcRenderer.send('popup-size', h),
  popupAction: (key, action, minutes) => ipcRenderer.send('popup-action', key, action, minutes)
});
