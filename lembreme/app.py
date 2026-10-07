"""Janela principal + popups no canto da tela + agendador."""
import ctypes
import queue
import re
import socket
import sys
import threading
import tkinter as tk
import winsound
from datetime import date, datetime, timedelta
from tkinter import ttk

import pystray
from tkcalendar import DateEntry

from . import icon
from .storage import Reminder, Store

PORT = 47819  # instância única
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
REPETIR = [("unica", "Não repetir"), ("diaria", "Todo dia"), ("semanal", "Toda semana"),
           ("mensal", "Todo mês"), ("anual", "Todo ano")]
REP_LABEL = dict(REPETIR) | {"unica": ""}

BG, CARD, CARD2, FG, MUTED, ACCENT, ERR, OK = (
    "#1e1f24", "#2a2c33", "#363944", "#f2f2f2", "#a0a3ab", "#4f8cff", "#ff6b6b", "#5fd38d")
HORAS = [f"{h:02d}:{m:02d}" for h in range(6, 24) for m in (0, 30)]


def work_area():
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    rc = RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0)  # SPI_GETWORKAREA
    return rc.l, rc.t, rc.r, rc.b


def fmt_when(dt: datetime, now: datetime) -> str:
    d = (dt.date() - now.date()).days
    if d == 0:
        return f"Hoje, {dt:%H:%M}"
    if d == 1:
        return f"Amanhã, {dt:%H:%M}"
    fmt = "%d/%m" if dt.year == now.year else "%d/%m/%Y"
    return f"{DIAS[dt.weekday()].capitalize()} {dt.strftime(fmt)}, {dt:%H:%M}"


def parse_hora(s: str):
    m = re.fullmatch(r"\s*(\d{1,2})\s*(?:[:h]\s*(\d{2})?)?\s*", s.lower())
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    return (h, mi) if h < 24 and mi < 60 else None


class Chip(tk.Label):
    """Botão plano; com `selected` vira azul."""

    def __init__(self, parent, text, cmd, primary=False, **kw):
        super().__init__(parent, text=text, cursor="hand2", font=("Segoe UI", 10, "bold" if primary else "normal"),
                         padx=12, pady=5, **kw)
        self.primary = primary
        self.bind("<Button-1>", lambda e: cmd())
        self.bind("<Enter>", lambda e: self._paint(hover=True))
        self.bind("<Leave>", lambda e: self._paint())
        self.selected = False
        self._paint()

    def select(self, on: bool):
        self.selected = on
        self._paint()

    def _paint(self, hover=False):
        if self.primary or self.selected:
            self.config(bg="#6a9dff" if hover else ACCENT, fg="white")
        else:
            self.config(bg="#454956" if hover else CARD2, fg=FG)


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

        tk.Label(body, text="🔔 Lembreme", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(body, text=r.message, bg=CARD, fg=FG, font=("Segoe UI Semibold", 13),
                 wraplength=int(320 * s), justify="left").pack(anchor="w", pady=(int(2 * s), int(2 * s)))
        info = f"{r.due:%d/%m %H:%M}"
        if now - r.due > timedelta(minutes=2):
            info += "  ·  atrasado"
        if r.recurrence != "unica":
            info += f"  ·  {REP_LABEL[r.recurrence].lower()}"
        tk.Label(body, text=info, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        btns = tk.Frame(body, bg=CARD)
        btns.pack(fill="x", pady=(int(10 * s), 0))
        tk.Label(btns, text="Adiar:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        for label, delta in (("10 min", timedelta(minutes=10)), ("1 h", timedelta(hours=1)),
                             ("amanhã", timedelta(days=1))):
            Chip(btns, label, lambda d=delta: self.snooze(d)).pack(side="left", padx=(0, int(4 * s)))
        Chip(btns, "OK", self.close, primary=True).pack(side="right")

        self.width = int(380 * s)
        self.update_idletasks()
        self._fade(0.0)

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
        self.editing: int | None = None
        self.recurrence = "unica"

        self.root = root = tk.Tk()
        self.scale = root.winfo_fpixels("1i") / 96
        root.title("Lembreme")
        root.configure(bg=BG)
        root.geometry(f"{int(680 * self.scale)}x{int(720 * self.scale)}")
        root.minsize(int(560 * self.scale), int(520 * self.scale))
        root.protocol("WM_DELETE_WINDOW", root.withdraw)  # fechar = esconder na bandeja
        root.iconbitmap(str(icon.ensure_ico()))

        self.tray = pystray.Icon("lembreme", icon.draw(64), "Lembreme", pystray.Menu(
            pystray.MenuItem("Abrir", lambda: self.cmds.put("show"), default=True),
            pystray.MenuItem("Testar popup", lambda: self.cmds.put("test")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: self.cmds.put("quit")),
        ))
        self.tray.run_detached()

        self._style()
        self._build()
        self.clear_form()
        self.refresh()
        threading.Thread(target=self._listen, args=(server,), daemon=True).start()

        if start_hidden:
            root.withdraw()
        root.after(500, self.tick)
        root.after(300, self._poll_cmds)

    # ---------- UI ----------
    def _style(self):
        s, root = self.scale, self.root
        st = ttk.Style(root)
        st.theme_use("clam")
        flat = dict(bordercolor=CARD, lightcolor=CARD, darkcolor=CARD)
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=FG,
                     rowheight=int(32 * s), borderwidth=0, font=("Segoe UI", 10), **flat)
        st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # sem borda branca
        st.configure("Treeview.Heading", background=CARD, foreground=MUTED, borderwidth=0, relief="flat",
                     font=("Segoe UI", 9), padding=(8, 6), **flat)
        st.map("Treeview.Heading", background=[("active", CARD)])
        st.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
        st.configure("TCombobox", fieldbackground=CARD2, background=CARD2, foreground=FG, arrowcolor=FG,
                     selectbackground=CARD2, selectforeground=FG, padding=6, **flat)
        st.map("TCombobox", fieldbackground=[("readonly", CARD2)], background=[("active", "#454956")])
        st.configure("DateEntry", fieldbackground=CARD2, background=CARD2, foreground=FG, arrowcolor=FG, padding=6,
                     **flat)
        root.option_add("*TCombobox*Listbox.background", CARD2)
        root.option_add("*TCombobox*Listbox.foreground", FG)
        root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    def _label(self, parent, text, **kw):
        return tk.Label(parent, text=text, bg=kw.pop("bg", CARD), fg=kw.pop("fg", MUTED),
                        font=kw.pop("font", ("Segoe UI", 9, "bold")), **kw)

    def _build(self):
        s, root = self.scale, self.root
        pad = int(16 * s)
        gap = int(6 * s)

        # ----- formulário -----
        form = tk.Frame(root, bg=CARD, padx=pad, pady=pad)
        form.pack(fill="x", padx=pad, pady=(pad, 0))

        self.form_title = tk.Label(form, text="Novo lembrete", bg=CARD, fg=FG, font=("Segoe UI Semibold", 13))
        self.form_title.pack(anchor="w")

        self._label(form, "O QUE LEMBRAR?").pack(anchor="w", pady=(int(10 * s), int(3 * s)))
        self.msg = tk.Entry(form, bg=CARD2, fg=FG, insertbackground=FG, relief="flat", font=("Segoe UI", 12))
        self.msg.pack(fill="x", ipady=int(7 * s), ipadx=int(6 * s))
        self.msg.bind("<Return>", lambda e: self.save())

        self._label(form, "QUANDO?").pack(anchor="w", pady=(int(12 * s), int(3 * s)))
        quick = tk.Frame(form, bg=CARD)
        quick.pack(fill="x")
        for text, fn in (("Em 10 min", lambda: self.quick(minutes=10)),
                         ("Em 1 hora", lambda: self.quick(hours=1)),
                         ("Hoje 18:00", lambda: self.quick(day=0, hm="18:00")),
                         ("Amanhã 09:00", lambda: self.quick(day=1, hm="09:00"))):
            Chip(quick, text, fn).pack(side="left", padx=(0, gap))

        when = tk.Frame(form, bg=CARD)
        when.pack(fill="x", pady=(gap, 0))
        self._label(when, "Dia", font=("Segoe UI", 10), fg=FG).pack(side="left", padx=(0, gap))
        self.date = DateEntry(
            when, locale="pt_BR", date_pattern="dd/mm/yyyy", width=11, font=("Segoe UI", 11),
            mindate=date.today(), showweeknumbers=False, firstweekday="sunday",
            background=ACCENT, foreground="white", headersbackground=CARD, headersforeground=MUTED,
            normalbackground=CARD2, normalforeground=FG, weekendbackground=CARD2, weekendforeground=FG,
            othermonthbackground=CARD, othermonthwebackground=CARD, othermonthforeground=MUTED,
            othermonthweforeground=MUTED, selectbackground=ACCENT, bordercolor=CARD, disableddaybackground=CARD,
            disableddayforeground="#5c606b")
        self.date.pack(side="left")
        self._label(when, "Hora", font=("Segoe UI", 10), fg=FG).pack(side="left", padx=(pad, gap))
        self.hora = ttk.Combobox(when, values=HORAS, width=6, font=("Segoe UI", 11))
        self.hora.pack(side="left")

        self._label(form, "REPETIR?").pack(anchor="w", pady=(int(12 * s), int(3 * s)))
        rep = tk.Frame(form, bg=CARD)
        rep.pack(fill="x")
        self.rep_chips = {}
        for key, text in REPETIR:
            c = Chip(rep, text, lambda k=key: self.set_recurrence(k))
            c.pack(side="left", padx=(0, gap))
            self.rep_chips[key] = c

        actions = tk.Frame(form, bg=CARD)
        actions.pack(fill="x", pady=(int(14 * s), 0))
        self.status = tk.Label(actions, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 10), anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self.save_btn = Chip(actions, "+ Adicionar", self.save, primary=True)
        self.save_btn.pack(side="right")
        self.cancel_btn = Chip(actions, "Cancelar", self.clear_form)

        # ----- lista -----
        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", padx=pad, pady=(pad, int(4 * s)))
        self.list_title = tk.Label(head, text="Próximos", bg=BG, fg=FG, font=("Segoe UI Semibold", 12))
        self.list_title.pack(side="left")
        tk.Label(head, text="duplo clique para editar", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")

        bot = tk.Frame(root, bg=BG)
        bot.pack(side="bottom", fill="x", padx=pad, pady=pad)
        self.edit_btn = Chip(bot, "Editar", self.edit)
        self.del_btn = Chip(bot, "Excluir", self.delete)
        self.edit_btn.pack(side="left", padx=(0, gap))
        self.del_btn.pack(side="left", padx=(0, gap))
        Chip(bot, "Testar popup", self.test_popup).pack(side="right")
        tk.Label(bot, text="Fechar a janela mantém o Lembreme na bandeja", bg=BG, fg="#6f737c",
                 font=("Segoe UI", 8)).pack(side="right", padx=gap)
        box = tk.Frame(root, bg=CARD)
        box.pack(fill="both", expand=True, padx=pad)
        self.tree = ttk.Treeview(box, columns=("q", "m", "r"), show="headings", selectmode="extended")
        for col, title, w, stretch in (("q", "Quando", 150, False), ("m", "Lembrete", 280, True),
                                       ("r", "Repete", 110, False)):
            self.tree.heading(col, text=title, anchor="w")
            self.tree.column(col, width=int(w * s), stretch=stretch, anchor="w")
        self.tree.tag_configure("late", foreground=ERR)
        self.tree.tag_configure("today", foreground="#9cc0ff")
        self.tree.pack(fill="both", expand=True, padx=int(4 * s), pady=int(4 * s))
        self.tree.bind("<Delete>", lambda e: self.delete())
        self.tree.bind("<Double-1>", lambda e: self.edit())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._sel_changed())
        self.empty = tk.Label(box, text="Nenhum lembrete ainda.\nCrie o primeiro aí em cima ☝",
                              bg=CARD, fg=MUTED, font=("Segoe UI", 11))

        self._sel_changed()

    def _sel_changed(self):
        on = bool(self.tree.selection())
        for b in (self.edit_btn, self.del_btn):
            b.config(fg=FG if on else "#6f737c")

    # ---------- formulário ----------
    def set_recurrence(self, key):
        self.recurrence = key
        for k, c in self.rep_chips.items():
            c.select(k == key)

    def quick(self, minutes=0, hours=0, day=None, hm=None):
        if day is None:
            dt = datetime.now() + timedelta(minutes=minutes, hours=hours)
            self.date.set_date(dt.date())
            self.hora.set(f"{dt:%H:%M}")
        else:
            self.date.set_date(date.today() + timedelta(days=day))
            self.hora.set(hm)
        self.msg.focus_set()

    def clear_form(self):
        self.editing = None
        self.msg.delete(0, "end")
        self.date.set_date(date.today())
        nxt = datetime.now() + timedelta(hours=1)
        self.hora.set(f"{nxt.hour:02d}:00")
        self.set_recurrence("unica")
        self.form_title.config(text="Novo lembrete")
        self.save_btn.config(text="+ Adicionar")
        self.cancel_btn.pack_forget()
        self.msg.focus_set()

    def _flash(self, text, color):
        self.status.config(text=text, fg=color)
        self.root.after(4000, lambda: self.status.cget("text") == text and self.status.config(text=""))

    def save(self):
        msg = self.msg.get().strip()
        if not msg:
            self.msg.focus_set()
            return self._flash("Escreva o que lembrar.", ERR)
        hm = parse_hora(self.hora.get())
        if not hm:
            return self._flash("Hora inválida. Use 09:00, 9h ou 9.", ERR)
        due = datetime.combine(self.date.get_date(), datetime.min.time()).replace(hour=hm[0], minute=hm[1])
        if due <= datetime.now() and self.recurrence == "unica":
            return self._flash("Esse horário já passou.", ERR)

        if self.editing:
            self.store.update(self.editing, msg, due, self.recurrence, due.day)
            done = "✓ Alterado"
        else:
            self.store.add(msg, due, self.recurrence, due.day)
            done = "✓ Criado"
        self.clear_form()
        self.refresh()
        self._flash(f"{done}: {fmt_when(due, datetime.now())}", OK)

    def edit(self):
        sel = self.tree.selection()
        if not sel or not (r := self.store.get(int(sel[0]))):
            return
        self.editing = r.id
        self.msg.delete(0, "end")
        self.msg.insert(0, r.message)
        self.date.config(mindate=min(r.due.date(), date.today()))
        self.date.set_date(r.due.date())
        self.hora.set(f"{r.due:%H:%M}")
        self.set_recurrence(r.recurrence)
        self.form_title.config(text="Editando lembrete")
        self.save_btn.config(text="Salvar")
        self.cancel_btn.pack(side="right", padx=(0, int(6 * self.scale)))
        self.msg.focus_set()

    def delete(self):
        for iid in self.tree.selection():
            self.store.delete(int(iid))
            if self.editing == int(iid):
                self.clear_form()
        self.refresh()

    def refresh(self):
        now = datetime.now()
        items = self.store.active()
        self.tree.delete(*self.tree.get_children())
        for r in items:
            tag = "late" if r.due <= now else "today" if r.due.date() == now.date() else ""
            self.tree.insert("", "end", iid=str(r.id), tags=(tag,),
                             values=(fmt_when(r.due, now), r.message, REP_LABEL[r.recurrence]))
        self.list_title.config(text=f"Próximos ({len(items)})" if items else "Próximos")
        if items:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        self._sel_changed()
        tip = f"Lembreme · próximo: {fmt_when(items[0].due, now)} {items[0].message}" if items else "Lembreme"
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
                self.msg.focus_set()
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
