"""Janela principal + popups no canto da tela + agendador."""
import ctypes
import queue
import socket
import sys
import threading
import tkinter as tk
import winsound
from datetime import datetime, timedelta
from tkinter import ttk

import pystray

from . import icon

from .parser import ParseError, describe, parse
from .storage import Reminder, Store

PORT = 47819  # instância única
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

BG, CARD, FG, MUTED, ACCENT, ERR = "#1e1f24", "#2a2c33", "#f2f2f2", "#a0a3ab", "#4f8cff", "#ff6b6b"


def work_area():
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    rc = RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0)  # SPI_GETWORKAREA
    return rc.l, rc.t, rc.r, rc.b


def fmt_when(dt: datetime, now: datetime) -> str:
    d = (dt.date() - now.date()).days
    if d == 0:
        return f"hoje {dt:%H:%M}"
    if d == 1:
        return f"amanhã {dt:%H:%M}"
    return f"{DIAS[dt.weekday()]} {dt:%d/%m/%Y %H:%M}"


class Popup(tk.Toplevel):
    def __init__(self, app: "App", r: Reminder, now: datetime):
        super().__init__(app.root)
        self.app, self.r = app, r
        s = app.scale
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(bg=ACCENT)

        body = tk.Frame(self, bg=CARD, padx=int(14 * s), pady=int(12 * s))
        body.pack(fill="both", expand=True, padx=(int(4 * s), 0))

        tk.Label(body, text="⏰ Lembreme", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(body, text=r.message, bg=CARD, fg=FG, font=("Segoe UI Semibold", 13),
                 wraplength=int(320 * s), justify="left").pack(anchor="w", pady=(int(2 * s), int(2 * s)))
        info = f"{r.due:%d/%m %H:%M}"
        if now - r.due > timedelta(minutes=2):
            info += "  ·  atrasado"
        if r.recurrence != "unica":
            info += f"  ·  {r.recurrence}"
        tk.Label(body, text=info, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        btns = tk.Frame(body, bg=CARD)
        btns.pack(fill="x", pady=(int(10 * s), 0))
        for label, delta in (("+10 min", timedelta(minutes=10)), ("+1 h", timedelta(hours=1)),
                             ("Amanhã", timedelta(days=1))):
            self._btn(btns, label, lambda d=delta: self.snooze(d), CARD).pack(side="left", padx=(0, int(6 * s)))
        self._btn(btns, "OK", self.close, ACCENT).pack(side="right")

        self.width = int(370 * s)
        self.update_idletasks()
        self._fade(0.0)

    def _btn(self, parent, text, cmd, bg):
        b = tk.Label(parent, text=text, bg=bg if bg == ACCENT else "#3a3d46", fg=FG,
                     font=("Segoe UI", 9, "bold" if bg == ACCENT else "normal"),
                     padx=int(10 * self.app.scale), pady=int(4 * self.app.scale), cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        return b

    def _fade(self, a):
        a = min(a + 0.1, 0.97)
        self.attributes("-alpha", a)
        if a < 0.97:
            self.after(20, self._fade, a)

    def snooze(self, delta):
        self.app.store.add(self.r.message, datetime.now().replace(second=0, microsecond=0) + delta)
        self.app.refresh()
        self.close()

    def close(self):
        self.app.popups.remove(self)
        self.destroy()
        self.app.layout_popups()


class App:
    def __init__(self, start_hidden: bool, server: socket.socket):
        self.store = Store()
        self.popups: list[Popup] = []
        self.cmds: queue.Queue = queue.Queue()

        self.root = root = tk.Tk()
        self.scale = root.winfo_fpixels("1i") / 96
        root.title("Lembreme")
        root.configure(bg=BG)
        root.geometry(f"{int(640 * self.scale)}x{int(480 * self.scale)}")
        root.minsize(int(480 * self.scale), int(320 * self.scale))
        root.protocol("WM_DELETE_WINDOW", root.withdraw)  # fechar = esconder na bandeja
        root.iconbitmap(str(icon.ensure_ico()))

        self.tray = pystray.Icon("lembreme", icon.draw(64), "Lembreme", pystray.Menu(
            pystray.MenuItem("Abrir", lambda: self.cmds.put("show"), default=True),
            pystray.MenuItem("Testar popup", lambda: self.cmds.put("test")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: self.cmds.put("quit")),
        ))
        self.tray.run_detached()

        self._build()
        self.refresh()
        threading.Thread(target=self._listen, args=(server,), daemon=True).start()

        if start_hidden:
            root.withdraw()
        root.after(500, self.tick)
        root.after(300, self._poll_cmds)

    # ---------- UI ----------
    def _build(self):
        s, root = self.scale, self.root
        st = ttk.Style(root)
        st.theme_use("clam")
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=FG,
                     rowheight=int(26 * s), borderwidth=0, font=("Segoe UI", 10))
        st.configure("Treeview.Heading", background=BG, foreground=MUTED, borderwidth=0,
                     font=("Segoe UI", 9))
        st.map("Treeview", background=[("selected", ACCENT)])

        pad = int(14 * s)
        top = tk.Frame(root, bg=BG, padx=pad, pady=pad)
        top.pack(fill="x")
        tk.Label(top, text="Novo lembrete", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        self.entry = tk.Entry(top, bg=CARD, fg=FG, insertbackground=FG, relief="flat",
                              font=("Segoe UI", 12))
        self.entry.pack(fill="x", ipady=int(6 * s), pady=(int(4 * s), 0))
        self.entry.bind("<KeyRelease>", lambda e: self.preview())
        self.entry.bind("<Return>", lambda e: self.add())
        self.entry.focus_set()

        self.prev = tk.Label(top, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w", justify="left")
        self.prev.pack(fill="x", pady=(int(4 * s), 0))
        self._hint()

        mid = tk.Frame(root, bg=BG, padx=pad)
        mid.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(mid, columns=("q", "r", "m"), show="headings", selectmode="extended")
        for col, title, w, stretch in (("q", "Quando", 150, False), ("r", "Repete", 80, False),
                                       ("m", "Lembrete", 300, True)):
            self.tree.heading(col, text=title, anchor="w")
            self.tree.column(col, width=int(w * s), stretch=stretch, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Delete>", lambda e: self.delete())

        bot = tk.Frame(root, bg=BG, padx=pad, pady=pad)
        bot.pack(fill="x")
        for text, cmd in (("Excluir", self.delete), ("Testar popup", self.test_popup)):
            tk.Button(bot, text=text, command=cmd, bg=CARD, fg=FG, activebackground=ACCENT,
                      relief="flat", padx=int(10 * s)).pack(side="left", padx=(0, int(6 * s)))
        tk.Button(bot, text="Sair", command=self.quit, bg=CARD, fg=FG, activebackground=ERR,
                  relief="flat", padx=int(10 * s)).pack(side="right")

    def _hint(self):
        self.prev.config(fg=MUTED, text='Ex.: "amanhã 8h ligar dentista" · "10/10 9:00 pagar luz mensal" · '
                                        '"em 30 min tirar bolo" · "toda segunda 7h academia" · "todo dia 5 pagar aluguel"')

    def preview(self):
        txt = self.entry.get().strip()
        if not txt:
            return self._hint()
        try:
            self.prev.config(fg=ACCENT, text="→ " + describe(parse(txt)))
        except ParseError as e:
            self.prev.config(fg=ERR, text=str(e))

    def add(self):
        try:
            p = parse(self.entry.get())
        except ParseError as e:
            self.prev.config(fg=ERR, text=str(e))
            return
        self.store.add(p.message, p.when, p.recurrence, p.anchor_day)
        self.entry.delete(0, "end")
        self.prev.config(fg=ACCENT, text="✓ Salvo: " + describe(p))
        self.refresh()

    def delete(self):
        for iid in self.tree.selection():
            self.store.delete(int(iid))
        self.refresh()

    def refresh(self):
        now = datetime.now()
        self.tree.delete(*self.tree.get_children())
        for r in self.store.active():
            rep = "" if r.recurrence == "unica" else r.recurrence
            self.tree.insert("", "end", iid=str(r.id), values=(fmt_when(r.due, now), rep, r.message))
        nxt = self.store.active()[:1]
        tip = f"Lembreme · próximo: {fmt_when(nxt[0].due, now)} {nxt[0].message}" if nxt else "Lembreme"
        self.tray.title = tip[:127]

    # ---------- popups ----------
    def show_popup(self, r: Reminder, now: datetime):
        self.popups.append(Popup(self, r, now))
        self.layout_popups()
        winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)

    def layout_popups(self):
        l, t, rgt, b = work_area()
        m = int(12 * self.scale)
        y = b - m
        for p in self.popups:
            p.update_idletasks()
            h = p.winfo_reqheight()
            y -= h
            p.geometry(f"{p.width}x{h}+{rgt - p.width - m}+{y}")
            y -= m

    def test_popup(self):
        now = datetime.now().replace(second=0, microsecond=0)
        self.show_popup(Reminder(0, "Teste: assim aparece o lembrete", now, "unica", None), now)

    # ---------- agendador ----------
    def tick(self):
        now = datetime.now()
        fired = self.store.due(now)
        for r in fired:
            self.store.fire(r, now)
            self.show_popup(r, now)
        if fired or now.second < 10:
            self.refresh()
        self.root.after(10_000, self.tick)

    # ---------- instância única ----------
    def _listen(self, server):
        while True:
            conn, _ = server.accept()
            with conn:
                if conn.recv(16) == b"show":
                    self.cmds.put("show")

    def _poll_cmds(self):
        while not self.cmds.empty():
            cmd = self.cmds.get()
            if cmd == "show":
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.entry.focus_set()
            elif cmd == "test":
                self.test_popup()
            elif cmd == "quit":
                return self.quit()
        self.root.after(300, self._poll_cmds)

    def quit(self):
        self.tray.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("lembreme")  # ícone próprio na barra
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    server = socket.socket()
    try:
        server.bind(("127.0.0.1", PORT))
        server.listen()
    except OSError:
        # já está rodando: pede pra mostrar a janela e sai
        with socket.create_connection(("127.0.0.1", PORT), timeout=2) as c:
            c.sendall(b"show")
        return

    App("--oculto" in sys.argv, server).run()
