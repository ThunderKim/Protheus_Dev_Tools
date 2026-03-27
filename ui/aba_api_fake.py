"""
ui/aba_api_fake.py
==================
Aba de API Fake: sobe um servidor HTTP local que responde com
o JSON configurado pelo usuario para qualquer endpoint definido.

Recursos:
  - Porta configuravel
  - Multiplos endpoints (metodo + path + JSON de resposta)
  - Status code configuravel por endpoint
  - Delay de resposta configuravel (simula latencia)
  - Log em tempo real de todas as requisicoes recebidas
  - Servidor roda em thread separada, nao trava a UI
"""

import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import socket


# ── Cores do tema ─────────────────────────────────────────
BG        = "#0d0d1a"
BG_PANEL  = "#13131f"
BG_ENTRY  = "#1a1a2e"
BG_LOG    = "#050510"
FG        = "#e0e0f0"
FG_DIM    = "#6b6b8a"
FG_GREEN  = "#4ade80"
FG_YELLOW = "#fbbf24"
FG_RED    = "#f87171"
FG_BLUE   = "#60a5fa"
FG_PURPLE = "#a78bfa"
ACCENT    = "#7c3aed"
FONT      = ("Consolas", 9)
FONT_BOLD = ("Consolas", 9, "bold")
FONT_BIG  = ("Consolas", 11, "bold")
FONT_MONO = ("Consolas", 10)

METODOS   = ["GET", "POST", "PUT", "PATCH", "DELETE", "ANY"]
STATUS_CODES = ["200", "201", "204", "400", "401", "403", "404", "409", "422", "500", "503"]


# ══════════════════════════════════════════════════════════
#  HANDLER HTTP
# ══════════════════════════════════════════════════════════

class _FakeHandler(BaseHTTPRequestHandler):
    """Handler generico que responde com o JSON configurado."""

    # Preenchido pela AbaApiFake antes de subir o servidor
    endpoints: list = []       # [{metodo, path, status, delay, body}]
    log_callback = None        # funcao(str) para enviar log a UI

    def log_message(self, fmt, *args):
        """Silencia o log padrao do BaseHTTPRequestHandler."""
        pass

    def _responder(self):
        path_req   = urlparse(self.path).path
        metodo_req = self.command.upper()

        # Busca endpoint mais especifico primeiro (metodo exato antes de ANY)
        match = None
        for ep in self.endpoints:
            ep_path   = ep["path"] if ep["path"].startswith("/") else "/" + ep["path"]
            ep_metodo = ep["metodo"].upper()
            if ep_path == path_req and (ep_metodo == metodo_req or ep_metodo == "ANY"):
                if match is None or ep_metodo == metodo_req:
                    match = ep

        ts = time.strftime("%H:%M:%S")

        if match is None:
            status  = 404
            body    = json.dumps({"error": "endpoint nao configurado", "path": path_req})
            log_msg = f"[{ts}]  {metodo_req:6s}  {path_req}  →  404  (sem match)"
            log_cor = FG_RED
        else:
            delay = float(match.get("delay", 0))
            if delay > 0:
                time.sleep(delay)
            status  = int(match.get("status", 200))
            body    = match.get("body", "{}")
            log_msg = f"[{ts}]  {metodo_req:6s}  {path_req}  →  {status}"
            log_cor = FG_GREEN if status < 400 else FG_YELLOW

        body_bytes = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body_bytes)

        if self.log_callback:
            self.log_callback(log_msg, log_cor)

    def do_OPTIONS(self):
        """CORS pre-flight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        ts = time.strftime("%H:%M:%S")
        path_req = urlparse(self.path).path
        if self.log_callback:
            self.log_callback(f"[{ts}]  OPTIONS  {path_req}  →  204 (CORS)", FG_DIM)

    do_GET    = _responder
    do_POST   = _responder
    do_PUT    = _responder
    do_PATCH  = _responder
    do_DELETE = _responder


# ══════════════════════════════════════════════════════════
#  ABA
# ══════════════════════════════════════════════════════════

class AbaApiFake(tk.Frame):
    """Aba com servidor HTTP fake configuravel."""

    def __init__(self, notebook: ttk.Notebook, atualizar_rodape) -> None:
        super().__init__(notebook, bg=BG)
        notebook.add(self, text="  🌐 API Fake  ")

        self.atualizar_rodape = atualizar_rodape
        self._servidor: HTTPServer | None = None
        self._thread:   threading.Thread | None = None
        self._endpoints: list[dict] = []   # lista de endpoints configurados

        self._construir()

    # ══════════════════════════════════════════════════════
    #  CONSTRUCAO DA UI
    # ══════════════════════════════════════════════════════

    def _construir(self) -> None:
        # Layout principal: esquerda (config) | direita (log)
        paned = tk.PanedWindow(self, orient="horizontal",
            bg=BG, sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        esq = tk.Frame(paned, bg=BG)
        dir = tk.Frame(paned, bg=BG)
        paned.add(esq, minsize=480)
        paned.add(dir, minsize=320)

        self._construir_esquerda(esq)
        self._construir_direita(dir)

    # ── Painel esquerdo ───────────────────────────────────

    def _construir_esquerda(self, parent) -> None:
        # Titulo
        tk.Label(parent, text="API Fake — Servidor HTTP Local",
            bg=BG, fg=FG, font=FONT_BIG,
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(parent,
            text="Configure endpoints e suba um servidor HTTP na sua maquina.",
            bg=BG, fg=FG_DIM, font=FONT,
        ).pack(anchor="w", pady=(0, 8))

        # ── Linha de porta + botao ────────────────────────
        frame_ctrl = tk.Frame(parent, bg=BG)
        frame_ctrl.pack(fill="x", pady=(0, 8))

        tk.Label(frame_ctrl, text="Porta:", bg=BG, fg=FG, font=FONT,
        ).pack(side="left")

        self.entry_porta = tk.Entry(frame_ctrl, width=7,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            relief="flat", font=FONT_MONO, bd=4)
        self.entry_porta.insert(0, "8080")
        self.entry_porta.pack(side="left", padx=(4, 16))

        self.lbl_url = tk.Label(frame_ctrl,
            text="http://localhost:8080", bg=BG, fg=FG_DIM, font=FONT)
        self.lbl_url.pack(side="left")

        self.btn_toggle = tk.Button(frame_ctrl,
            text="  ▶  INICIAR  ",
            bg="#059669", fg="white", font=FONT_BOLD,
            relief="flat", cursor="hand2",
            activebackground="#047857",
            command=self._toggle_servidor)
        self.btn_toggle.pack(side="right")

        self.lbl_status = tk.Label(frame_ctrl,
            text="● Parado", bg=BG, fg=FG_RED, font=FONT)
        self.lbl_status.pack(side="right", padx=(0, 12))

        self.entry_porta.bind("<KeyRelease>", self._atualizar_url_label)

        # ── Separador ─────────────────────────────────────
        tk.Frame(parent, bg=BG_ENTRY, height=1).pack(fill="x", pady=(0, 8))

        # ── Formulario de novo endpoint ───────────────────
        tk.Label(parent, text="Adicionar Endpoint",
            bg=BG, fg=FG_PURPLE, font=FONT_BOLD,
        ).pack(anchor="w")

        # Metodo + Path
        frame_mp = tk.Frame(parent, bg=BG)
        frame_mp.pack(fill="x", pady=(4, 0))

        tk.Label(frame_mp, text="Metodo:", bg=BG, fg=FG, font=FONT,
        ).pack(side="left")
        self.combo_metodo = ttk.Combobox(frame_mp, values=METODOS,
            width=7, font=FONT, state="readonly")
        self.combo_metodo.set("GET")
        self.combo_metodo.pack(side="left", padx=(4, 16))

        tk.Label(frame_mp, text="Path:", bg=BG, fg=FG, font=FONT,
        ).pack(side="left")
        self.entry_path = tk.Entry(frame_mp,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            relief="flat", font=FONT_MONO, bd=4, width=28)
        self.entry_path.insert(0, "/api/exemplo")
        self.entry_path.pack(side="left", padx=(4, 0), fill="x", expand=True)

        # Status + Delay
        frame_sd = tk.Frame(parent, bg=BG)
        frame_sd.pack(fill="x", pady=(6, 0))

        tk.Label(frame_sd, text="Status:", bg=BG, fg=FG, font=FONT,
        ).pack(side="left")
        self.combo_status = ttk.Combobox(frame_sd, values=STATUS_CODES,
            width=5, font=FONT, state="readonly")
        self.combo_status.set("200")
        self.combo_status.pack(side="left", padx=(4, 16))

        tk.Label(frame_sd, text="Delay (s):", bg=BG, fg=FG, font=FONT,
        ).pack(side="left")
        self.entry_delay = tk.Entry(frame_sd, width=6,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            relief="flat", font=FONT_MONO, bd=4)
        self.entry_delay.insert(0, "0")
        self.entry_delay.pack(side="left", padx=(4, 0))

        tk.Label(frame_sd,
            text="  (0 = sem atraso)", bg=BG, fg=FG_DIM, font=FONT,
        ).pack(side="left")

        # Editor JSON
        tk.Label(parent, text="JSON de Retorno:",
            bg=BG, fg=FG, font=FONT,
        ).pack(anchor="w", pady=(8, 2))

        frame_json = tk.Frame(parent, bg=BG)
        frame_json.pack(fill="both", expand=True)

        self.txt_json = tk.Text(frame_json,
            bg=BG_LOG, fg=FG_GREEN,
            insertbackground=FG_GREEN,
            font=FONT_MONO, relief="flat", bd=6,
            undo=True, wrap="none", height=10)
        self.txt_json.insert("1.0", json.dumps(
            {"status": "ok", "mensagem": "resposta da API fake"}, indent=2))
        sv_j = ttk.Scrollbar(frame_json, orient="vertical",   command=self.txt_json.yview)
        sh_j = ttk.Scrollbar(frame_json, orient="horizontal", command=self.txt_json.xview)
        self.txt_json.configure(yscrollcommand=sv_j.set, xscrollcommand=sh_j.set)
        sv_j.pack(side="right",  fill="y")
        sh_j.pack(side="bottom", fill="x")
        self.txt_json.pack(fill="both", expand=True)

        # Botoes do formulario
        frame_btns = tk.Frame(parent, bg=BG)
        frame_btns.pack(fill="x", pady=(6, 0))

        tk.Button(frame_btns, text="  ✚  ADICIONAR ENDPOINT  ",
            bg=ACCENT, fg="white", font=FONT_BOLD,
            relief="flat", cursor="hand2",
            activebackground="#6d28d9",
            command=self._adicionar_endpoint,
        ).pack(side="left")

        tk.Button(frame_btns, text="🗑 Formatar JSON",
            bg=BG_ENTRY, fg=FG, font=FONT,
            relief="flat", cursor="hand2",
            command=self._formatar_json,
        ).pack(side="left", padx=(8, 0))

        # ── Lista de endpoints configurados ───────────────
        tk.Frame(parent, bg=BG_ENTRY, height=1).pack(fill="x", pady=(10, 6))
        tk.Label(parent, text="Endpoints Configurados",
            bg=BG, fg=FG_PURPLE, font=FONT_BOLD,
        ).pack(anchor="w")

        frame_lista = tk.Frame(parent, bg=BG)
        frame_lista.pack(fill="x", pady=(4, 0))

        self.tree_ep = ttk.Treeview(frame_lista,
            columns=("metodo", "path", "status", "delay"),
            show="headings", height=5, selectmode="browse")

        for col, lbl, w in [
            ("metodo", "Metodo",  70),
            ("path",   "Path",   200),
            ("status", "Status",  60),
            ("delay",  "Delay(s)", 70),
        ]:
            self.tree_ep.heading(col, text=lbl)
            self.tree_ep.column(col, width=w, minwidth=50)

        self.tree_ep.tag_configure("ep", background=BG_PANEL, foreground=FG)
        sv_ep = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree_ep.yview)
        self.tree_ep.configure(yscrollcommand=sv_ep.set)
        sv_ep.pack(side="right", fill="y")
        self.tree_ep.pack(fill="x")
        self.tree_ep.bind("<<TreeviewSelect>>", self._selecionar_endpoint)

        frame_ep_btns = tk.Frame(parent, bg=BG)
        frame_ep_btns.pack(fill="x", pady=(4, 0))

        tk.Button(frame_ep_btns, text="✏ Editar selecionado",
            bg=BG_ENTRY, fg=FG, font=FONT,
            relief="flat", cursor="hand2",
            command=self._editar_endpoint,
        ).pack(side="left")

        tk.Button(frame_ep_btns, text="🗑 Remover selecionado",
            bg="#4a1010", fg="white", font=FONT,
            relief="flat", cursor="hand2",
            command=self._remover_endpoint,
        ).pack(side="left", padx=(6, 0))

        tk.Button(frame_ep_btns, text="Limpar todos",
            bg=BG_ENTRY, fg=FG_DIM, font=FONT,
            relief="flat", cursor="hand2",
            command=self._limpar_endpoints,
        ).pack(side="right")

    # ── Painel direito (log) ──────────────────────────────

    def _construir_direita(self, parent) -> None:
        frame_topo = tk.Frame(parent, bg=BG)
        frame_topo.pack(fill="x", pady=(4, 6))

        tk.Label(frame_topo, text="Log de Requisicoes",
            bg=BG, fg=FG_PURPLE, font=FONT_BOLD,
        ).pack(side="left")

        tk.Button(frame_topo, text="🗑 Limpar",
            bg=BG_ENTRY, fg=FG_DIM, font=FONT,
            relief="flat", cursor="hand2",
            command=self._limpar_log,
        ).pack(side="right")

        # Resumo de requisicoes
        frame_res = tk.Frame(parent, bg=BG_PANEL)
        frame_res.pack(fill="x", pady=(0, 6))

        self.lbl_total   = tk.Label(frame_res, text="Total: 0",
            bg=BG_PANEL, fg=FG, font=FONT)
        self.lbl_total.pack(side="left", padx=8, pady=4)

        self.lbl_ok      = tk.Label(frame_res, text="2xx: 0",
            bg=BG_PANEL, fg=FG_GREEN, font=FONT)
        self.lbl_ok.pack(side="left", padx=8)

        self.lbl_erros   = tk.Label(frame_res, text="4xx/5xx: 0",
            bg=BG_PANEL, fg=FG_RED, font=FONT)
        self.lbl_erros.pack(side="left", padx=8)

        self._cnt_total = 0
        self._cnt_ok    = 0
        self._cnt_erro  = 0

        # Text widget de log
        frame_log = tk.Frame(parent, bg=BG)
        frame_log.pack(fill="both", expand=True)

        self.txt_log = tk.Text(frame_log,
            bg=BG_LOG, fg=FG,
            font=("Consolas", 8),
            relief="flat", bd=6,
            state="disabled", wrap="none")

        self.txt_log.tag_configure("green",  foreground=FG_GREEN)
        self.txt_log.tag_configure("yellow", foreground=FG_YELLOW)
        self.txt_log.tag_configure("red",    foreground=FG_RED)
        self.txt_log.tag_configure("dim",    foreground=FG_DIM)

        sv_l = ttk.Scrollbar(frame_log, orient="vertical",   command=self.txt_log.yview)
        sh_l = ttk.Scrollbar(frame_log, orient="horizontal", command=self.txt_log.xview)
        self.txt_log.configure(yscrollcommand=sv_l.set, xscrollcommand=sh_l.set)
        sv_l.pack(side="right",  fill="y")
        sh_l.pack(side="bottom", fill="x")
        self.txt_log.pack(fill="both", expand=True)

        # Curl helper
        tk.Label(parent, text="Exemplo de teste rapido:",
            bg=BG, fg=FG_DIM, font=FONT,
        ).pack(anchor="w", pady=(6, 2))
        self.txt_curl = tk.Text(parent,
            bg=BG_PANEL, fg=FG_BLUE,
            font=("Consolas", 8),
            relief="flat", bd=4, height=2, state="disabled")
        self.txt_curl.pack(fill="x")
        self._atualizar_curl_hint()

    # ══════════════════════════════════════════════════════
    #  SERVIDOR HTTP
    # ══════════════════════════════════════════════════════

    def _toggle_servidor(self) -> None:
        if self._servidor is None:
            self._iniciar()
        else:
            self._parar()

    def _iniciar(self) -> None:
        porta_str = self.entry_porta.get().strip()
        try:
            porta = int(porta_str)
            if not (1024 <= porta <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Porta invalida",
                "Informe uma porta valida entre 1024 e 65535.")
            return

        # Verifica se a porta esta livre
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", porta)) == 0:
                messagebox.showerror("Porta em uso",
                    f"A porta {porta} ja esta em uso.\nEscolha outra porta.")
                return

        # Atualiza handler com endpoints atuais
        _FakeHandler.endpoints    = list(self._endpoints)
        _FakeHandler.log_callback = self._receber_log

        try:
            self._servidor = HTTPServer(("0.0.0.0", porta), _FakeHandler)
        except Exception as e:
            messagebox.showerror("Erro ao iniciar servidor", str(e))
            return

        self._thread = threading.Thread(
            target=self._servidor.serve_forever, daemon=True)
        self._thread.start()

        self.btn_toggle.config(text="  ■  PARAR  ", bg="#dc2626",
            activebackground="#b91c1c")
        self.lbl_status.config(text=f"● Rodando :{porta}", fg=FG_GREEN)
        self.entry_porta.config(state="disabled")
        self._log(f"Servidor iniciado em http://localhost:{porta}", "green")
        self._log(f"{len(self._endpoints)} endpoint(s) configurado(s).", "dim")
        self.atualizar_rodape(f"API Fake rodando em http://localhost:{porta}")
        self._atualizar_curl_hint()

    def _parar(self) -> None:
        if self._servidor:
            self._servidor.shutdown()
            self._servidor = None
        self.btn_toggle.config(text="  ▶  INICIAR  ", bg="#059669",
            activebackground="#047857")
        self.lbl_status.config(text="● Parado", fg=FG_RED)
        self.entry_porta.config(state="normal")
        self._log("Servidor parado.", "dim")
        self.atualizar_rodape("API Fake parada.")

    # ══════════════════════════════════════════════════════
    #  ENDPOINTS
    # ══════════════════════════════════════════════════════

    def _validar_json(self, texto: str) -> tuple[bool, str]:
        """Retorna (valido, mensagem)."""
        try:
            json.loads(texto)
            return True, ""
        except json.JSONDecodeError as e:
            return False, str(e)

    def _adicionar_endpoint(self) -> None:
        metodo = self.combo_metodo.get().strip().upper()
        path   = self.entry_path.get().strip()
        status = self.combo_status.get().strip()
        delay  = self.entry_delay.get().strip()
        body   = self.txt_json.get("1.0", "end").strip()

        if not path:
            messagebox.showwarning("Atencao", "Informe o Path do endpoint.")
            return

        valido, erro = self._validar_json(body)
        if not valido:
            messagebox.showerror("JSON invalido", f"O JSON de retorno tem erro:\n\n{erro}")
            return

        try:
            delay_f = float(delay)
        except ValueError:
            messagebox.showerror("Delay invalido", "O delay deve ser um numero (ex: 0.5).")
            return

        # Normaliza path
        if not path.startswith("/"):
            path = "/" + path

        # Verifica duplicata
        for ep in self._endpoints:
            if ep["path"] == path and ep["metodo"] == metodo:
                if not messagebox.askyesno("Endpoint duplicado",
                        f"Ja existe um endpoint {metodo} {path}.\nDeseja substituir?"):
                    return
                self._endpoints.remove(ep)
                break

        ep = {"metodo": metodo, "path": path, "status": status,
              "delay": delay_f, "body": body}
        self._endpoints.append(ep)
        self._atualizar_tree()
        self._sincronizar_servidor()
        self._log(f"Endpoint adicionado: {metodo} {path} → {status}", "green")

    def _remover_endpoint(self) -> None:
        sel = self.tree_ep.selection()
        if not sel:
            return
        idx = self.tree_ep.index(sel[0])
        ep  = self._endpoints[idx]
        self._endpoints.pop(idx)
        self._atualizar_tree()
        self._sincronizar_servidor()
        self._log(f"Endpoint removido: {ep['metodo']} {ep['path']}", "dim")

    def _editar_endpoint(self) -> None:
        sel = self.tree_ep.selection()
        if not sel:
            messagebox.showwarning("Atencao", "Selecione um endpoint para editar.")
            return
        idx = self.tree_ep.index(sel[0])
        ep  = self._endpoints[idx]

        # Carrega valores no formulario
        self.combo_metodo.set(ep["metodo"])
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, ep["path"])
        self.combo_status.set(str(ep["status"]))
        self.entry_delay.delete(0, "end")
        self.entry_delay.insert(0, str(ep["delay"]))
        self.txt_json.delete("1.0", "end")
        try:
            body_fmt = json.dumps(json.loads(ep["body"]), indent=2)
        except Exception:
            body_fmt = ep["body"]
        self.txt_json.insert("1.0", body_fmt)

        # Remove da lista para reinsercao ao clicar Adicionar
        self._endpoints.pop(idx)
        self._atualizar_tree()

    def _limpar_endpoints(self) -> None:
        if not self._endpoints:
            return
        if messagebox.askyesno("Limpar endpoints",
                "Remover todos os endpoints configurados?"):
            self._endpoints.clear()
            self._atualizar_tree()
            self._sincronizar_servidor()
            self._log("Todos os endpoints removidos.", "dim")

    def _selecionar_endpoint(self, event=None) -> None:
        """Ao clicar num endpoint da lista, mostra o JSON no editor."""
        sel = self.tree_ep.selection()
        if not sel:
            return
        idx = self.tree_ep.index(sel[0])
        ep  = self._endpoints[idx]
        try:
            body_fmt = json.dumps(json.loads(ep["body"]), indent=2)
        except Exception:
            body_fmt = ep["body"]
        self.txt_json.delete("1.0", "end")
        self.txt_json.insert("1.0", body_fmt)

    def _atualizar_tree(self) -> None:
        self.tree_ep.delete(*self.tree_ep.get_children())
        for ep in self._endpoints:
            self.tree_ep.insert("", "end", tags=("ep",), values=(
                ep["metodo"], ep["path"], ep["status"], ep["delay"]))

    def _sincronizar_servidor(self) -> None:
        """Atualiza os endpoints no handler sem reiniciar o servidor."""
        _FakeHandler.endpoints = list(self._endpoints)

    # ══════════════════════════════════════════════════════
    #  LOG
    # ══════════════════════════════════════════════════════

    def _receber_log(self, mensagem: str, cor: str) -> None:
        """Chamado pelo handler (thread do servidor) — agenda no thread da UI."""
        # Mapeia cor hex para tag
        tag_map = {
            FG_GREEN:  "green",
            FG_YELLOW: "yellow",
            FG_RED:    "red",
            FG_DIM:    "dim",
        }
        tag = tag_map.get(cor, "")

        # Atualiza contadores
        self._cnt_total += 1
        if "→  2" in mensagem or "→  3" in mensagem:
            self._cnt_ok += 1
        elif "→  4" in mensagem or "→  5" in mensagem:
            self._cnt_erro += 1

        self.after(0, self._log, mensagem, tag)
        self.after(0, self._atualizar_contadores)

    def _log(self, mensagem: str, tag: str = "") -> None:
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", mensagem + "\n", tag)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def _limpar_log(self) -> None:
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")
        self._cnt_total = self._cnt_ok = self._cnt_erro = 0
        self._atualizar_contadores()

    def _atualizar_contadores(self) -> None:
        self.lbl_total.config(text=f"Total: {self._cnt_total}")
        self.lbl_ok.config(text=f"2xx: {self._cnt_ok}")
        self.lbl_erros.config(text=f"4xx/5xx: {self._cnt_erro}")

    # ══════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════

    def _formatar_json(self) -> None:
        texto = self.txt_json.get("1.0", "end").strip()
        valido, erro = self._validar_json(texto)
        if not valido:
            messagebox.showerror("JSON invalido", f"Nao foi possivel formatar:\n\n{erro}")
            return
        formatado = json.dumps(json.loads(texto), indent=2, ensure_ascii=False)
        self.txt_json.delete("1.0", "end")
        self.txt_json.insert("1.0", formatado)

    def _atualizar_url_label(self, event=None) -> None:
        porta = self.entry_porta.get().strip()
        self.lbl_url.config(text=f"http://localhost:{porta}")
        self._atualizar_curl_hint()

    def _atualizar_curl_hint(self) -> None:
        porta = self.entry_porta.get().strip()
        path  = "/api/exemplo"
        if self._endpoints:
            path = self._endpoints[0]["path"]
        hint = (f"curl http://localhost:{porta}{path}\n"
                f"Invoke-RestMethod http://localhost:{porta}{path}")
        self.txt_curl.config(state="normal")
        self.txt_curl.delete("1.0", "end")
        self.txt_curl.insert("1.0", hint)
        self.txt_curl.config(state="disabled")
