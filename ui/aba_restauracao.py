"""
ui/aba_restauracao.py
=====================
Aba de restauração de base de testes do Protheus.
Gerencia download/restauração de banco SQL e pasta Protheus_Data.
"""

import os
import shutil
import time
import threading
import zipfile
import base64
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pyodbc

from config import CONFIG, PY7ZR_DISPONIVEL

if PY7ZR_DISPONIVEL:
    import py7zr


class AbaRestauracao(tk.Frame):
    """Aba completa de restauração de banco + Protheus_Data."""

    def __init__(self, notebook: ttk.Notebook, atualizar_rodape) -> None:
        super().__init__(notebook, bg="#1a1a1a")
        notebook.add(self, text="  🔄 Restaurar Base  ")

        self.atualizar_rodape = atualizar_rodape
        self._construir()

    # ══════════════════════════════════════════════════════
    #  CONSTRUÇÃO DA UI
    # ══════════════════════════════════════════════════════

    def _construir(self) -> None:
        # Scroll geral
        canvas = tk.Canvas(self, bg="#1a1a1a", highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._inner = tk.Frame(canvas, bg="#1a1a1a")
        self._inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.bind(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        fi = self._inner  # atalho

        tk.Label(fi, text="🔄  RESTAURAR BASE DE TESTES",
            bg="#1a1a1a", fg="#f5f8fa", font=("Consolas", 13, "bold"),
        ).pack(pady=(16, 2))
        tk.Label(fi, text="Baixa os ZIPs do servidor, extrai e restaura o banco e a pasta Protheus_Data",
            bg="#1a1a1a", fg="#6b6b8a", font=("Consolas", 8),
        ).pack(pady=(0, 12))

        self._secao_origem(fi)
        self._secao_banco(fi)
        self._secao_pasta(fi)
        self._secao_tudo(fi)
        self._secao_log(fi)

    # ── Seção 0: Origem ───────────────────────────────────

    def _secao_origem(self, parent) -> None:
        f = tk.Frame(parent, bg="#0d1f0d")
        f.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(f, text="  🌐  ORIGEM DOS ARQUIVOS ZIP",
            bg="#0d1f0d", fg="#86efac", font=("Consolas", 10, "bold"), anchor="w",
        ).pack(fill="x", pady=(10, 6))
        tk.Frame(f, bg="#1a4020", height=1).pack(fill="x", padx=12)

        self._label_dica(f, "URL base do servidor:",
            "Pasta/URL onde estão os arquivos ZIP (sem o nome do arquivo)")

        frame_url = tk.Frame(f, bg="#0d1f0d")
        frame_url.pack(fill="x", padx=12, pady=(2, 6))
        self.rst_url_base = tk.Entry(frame_url,
            bg="#071407", fg="#86efac", insertbackground="#86efac",
            relief="flat", font=("Consolas", 9), bd=4, width=65)
        self.rst_url_base.insert(0,
            "https://arte.engpro.totvs.com.br/engenharia/base_congelada/protheus/bra/12.1.2410/exp_com_dic/latest")
        self.rst_url_base.pack(side="left", fill="x", expand=True)

        frame_cred = tk.Frame(f, bg="#0d1f0d")
        frame_cred.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(frame_cred, text="Usuário do servidor:",
            bg="#0d1f0d", fg="#a0a0c0", font=("Consolas", 9),
        ).pack(side="left")
        self.rst_srv_user = tk.Entry(frame_cred,
            bg="#071407", fg="#86efac", insertbackground="#86efac",
            relief="flat", font=("Consolas", 9), bd=4, width=18)
        self.rst_srv_user.pack(side="left", padx=(4, 16))
        tk.Label(frame_cred, text="Senha:",
            bg="#0d1f0d", fg="#a0a0c0", font=("Consolas", 9),
        ).pack(side="left")
        self.rst_srv_pass = tk.Entry(frame_cred,
            bg="#071407", fg="#86efac", insertbackground="#86efac",
            relief="flat", font=("Consolas", 9), bd=4, width=18, show="*")
        self.rst_srv_pass.pack(side="left", padx=(4, 0))

        tk.Label(f,
            text="  ℹ  Se o servidor exigir autenticação (Artifactory, Nexus etc.), preencha acima.",
            bg="#0d1f0d", fg="#60a5fa", font=("Consolas", 8), anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 0))

        self._label_dica(f, "Pasta local para download/extração:",
            "Pasta temporária na máquina local")
        frame_tmp = tk.Frame(f, bg="#0d1f0d")
        frame_tmp.pack(fill="x", padx=12, pady=(2, 6))
        self.rst_pasta_tmp = tk.Entry(frame_tmp,
            bg="#071407", fg="#86efac", insertbackground="#86efac",
            relief="flat", font=("Consolas", 9), bd=4, width=55)
        self.rst_pasta_tmp.insert(0, "C:\\Temp\\protheus_restore")
        self.rst_pasta_tmp.pack(side="left", fill="x", expand=True)
        tk.Button(frame_tmp, text=" 📂 ",
            bg="#14532d", fg="white", font=("Consolas", 9), relief="flat", cursor="hand2",
            command=lambda: self._pick_folder(self.rst_pasta_tmp, "Pasta temporária"),
        ).pack(side="left", padx=(4, 0))

        self.rst_limpar_tmp = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="  Limpar pasta temporária após restaurar",
            variable=self.rst_limpar_tmp,
            bg="#0d1f0d", fg="#86efac", selectcolor="#071407",
            font=("Consolas", 8), anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 8))

    # ── Seção 1: Banco SQL ────────────────────────────────

    def _secao_banco(self, parent) -> None:
        f = tk.Frame(parent, bg="#0d2137")
        f.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(f, text="  🗄  RESTAURAR BANCO SQL SERVER",
            bg="#0d2137", fg="#4ade80", font=("Consolas", 10, "bold"), anchor="w",
        ).pack(fill="x", pady=(10, 6))
        tk.Frame(f, bg="#1e4060", height=1).pack(fill="x", padx=12)

        self._label_dica(f, "Banco a restaurar:", "Nome do banco que será sobrescrito")
        self.rst_banco = self._entry(f, CONFIG["database"], 30)

        self._label_dica(f, "Usuário admin SQL:", "Precisa ter permissão sysadmin (ex: sa)")
        self.rst_usuario = self._entry(f, CONFIG["username"], 20)

        self._label_dica(f, "Senha admin:", "")
        self.rst_senha = self._entry(f, CONFIG["password"], 20, senha=True)

        tk.Frame(f, bg="#1e4060", height=1).pack(fill="x", padx=12, pady=(8, 4))

        # Radio origem
        self.rst_banco_origem = tk.StringVar(value="download")
        fr = tk.Frame(f, bg="#0d2137")
        fr.pack(fill="x", padx=12, pady=(0, 4))
        tk.Radiobutton(fr, text="  Baixar ZIP do servidor",
            variable=self.rst_banco_origem, value="download",
            bg="#0d2137", fg="#a0a0c0", selectcolor="#0d2137",
            font=("Consolas", 9), cursor="hand2",
            command=self._toggle_banco,
        ).pack(side="left")
        tk.Radiobutton(fr, text="  Usar arquivo local (.zip ou .bak)",
            variable=self.rst_banco_origem, value="local",
            bg="#0d2137", fg="#a0a0c0", selectcolor="#0d2137",
            font=("Consolas", 9), cursor="hand2",
            command=self._toggle_banco,
        ).pack(side="left", padx=(16, 0))

        # Sub-painel download
        self._fpanel_banco_dl = tk.Frame(f, bg="#0d2137")
        self._fpanel_banco_dl.pack(fill="x")
        self._label_dica(self._fpanel_banco_dl, "Nome do arquivo ZIP:", "Ex: mssql_bak.zip")
        self.rst_zip_banco = self._entry(self._fpanel_banco_dl, "mssql_bak.zip", 30)
        self._label_dica(self._fpanel_banco_dl, "Nome do .bak dentro do ZIP:",
            "Deixe em branco para usar o primeiro encontrado")
        self.rst_nome_bak = self._entry(self._fpanel_banco_dl, "", 30)
        tk.Label(self._fpanel_banco_dl,
            text="  ℹ  Deixe em branco para usar o primeiro .bak encontrado no ZIP",
            bg="#0d2137", fg="#60a5fa", font=("Consolas", 8), anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 4))

        # Sub-painel local
        self._fpanel_banco_loc = tk.Frame(f, bg="#0d2137")
        self._label_dica(self._fpanel_banco_loc, "Arquivo local (.zip ou .bak):",
            "Caminho completo do arquivo")
        fr_loc = tk.Frame(self._fpanel_banco_loc, bg="#0d2137")
        fr_loc.pack(fill="x", padx=12, pady=(2, 6))
        self.rst_bak_local = tk.Entry(fr_loc,
            bg="#0a1929", fg="#e0e0f0", insertbackground="#4ade80",
            relief="flat", font=("Consolas", 9), bd=4, width=55)
        self.rst_bak_local.pack(side="left", fill="x", expand=True)
        tk.Button(fr_loc, text=" 📂 ",
            bg="#1e4060", fg="white", font=("Consolas", 9), relief="flat", cursor="hand2",
            command=lambda: self._pick_file(self.rst_bak_local, "Selecione .zip ou .bak",
                [("Backup/ZIP", "*.bak *.zip *.7z"), ("Todos", "*.*")]),
        ).pack(side="left", padx=(4, 0))
        self._label_dica(self._fpanel_banco_loc, "Nome do .bak dentro do ZIP (se for .zip):",
            "Deixe em branco para usar o primeiro encontrado")
        self.rst_nome_bak_local = self._entry(self._fpanel_banco_loc, "", 30)

        tk.Button(f, text="  🗄  RESTAURAR BANCO  ",
            bg="#059669", fg="white", font=("Consolas", 10, "bold"),
            relief="flat", cursor="hand2", activebackground="#047857",
            command=self._restaurar_banco,
        ).pack(pady=(6, 14))

    # ── Seção 2: Pasta Protheus_Data ──────────────────────

    def _secao_pasta(self, parent) -> None:
        f = tk.Frame(parent, bg="#1a0d2e")
        f.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(f, text="  📁  RESTAURAR PASTA PROTHEUS_DATA",
            bg="#1a0d2e", fg="#a78bfa", font=("Consolas", 10, "bold"), anchor="w",
        ).pack(fill="x", pady=(10, 6))
        tk.Frame(f, bg="#3b1f6e", height=1).pack(fill="x", padx=12)

        self.rst_pasta_origem = tk.StringVar(value="download")
        fr = tk.Frame(f, bg="#1a0d2e")
        fr.pack(fill="x", padx=12, pady=(8, 4))
        tk.Radiobutton(fr, text="  Baixar ZIP do servidor",
            variable=self.rst_pasta_origem, value="download",
            bg="#1a0d2e", fg="#a0a0c0", selectcolor="#1a0d2e",
            font=("Consolas", 9), cursor="hand2",
            command=self._toggle_pasta,
        ).pack(side="left")
        tk.Radiobutton(fr, text="  Usar ZIP local",
            variable=self.rst_pasta_origem, value="local",
            bg="#1a0d2e", fg="#a0a0c0", selectcolor="#1a0d2e",
            font=("Consolas", 9), cursor="hand2",
            command=self._toggle_pasta,
        ).pack(side="left", padx=(16, 0))

        # Sub-painel download
        self._fpanel_pasta_dl = tk.Frame(f, bg="#1a0d2e")
        self._fpanel_pasta_dl.pack(fill="x")
        self._label_dica(self._fpanel_pasta_dl, "Nome do ZIP da pasta:", "Ex: protheus_data.zip")
        self.rst_zip_pasta = self._entry(self._fpanel_pasta_dl, "protheus_data.zip", 30)

        # Sub-painel local
        self._fpanel_pasta_loc = tk.Frame(f, bg="#1a0d2e")
        self._label_dica(self._fpanel_pasta_loc, "Arquivo ZIP local da pasta:",
            "Caminho completo do ZIP")
        fr_loc = tk.Frame(self._fpanel_pasta_loc, bg="#1a0d2e")
        fr_loc.pack(fill="x", padx=12, pady=(2, 6))
        self.rst_zip_pasta_local = tk.Entry(fr_loc,
            bg="#0a0015", fg="#e0e0f0", insertbackground="#a78bfa",
            relief="flat", font=("Consolas", 9), bd=4, width=55)
        self.rst_zip_pasta_local.pack(side="left", fill="x", expand=True)
        tk.Button(fr_loc, text=" 📂 ",
            bg="#4c1d95", fg="white", font=("Consolas", 9), relief="flat", cursor="hand2",
            command=lambda: self._pick_file(self.rst_zip_pasta_local, "Selecione o ZIP",
                [("ZIP/7z", "*.zip *.7z"), ("Todos", "*.*")]),
        ).pack(side="left", padx=(4, 0))

        # Pasta destino (sempre visível)
        self._label_dica(f, "Pasta DESTINO (a substituir):",
            "Caminho completo da pasta Protheus_Data atual")
        fr_dest = tk.Frame(f, bg="#1a0d2e")
        fr_dest.pack(fill="x", padx=12, pady=(2, 6))
        self.rst_pasta_dest = tk.Entry(fr_dest,
            bg="#0a0015", fg="#e0e0f0", insertbackground="#a78bfa",
            relief="flat", font=("Consolas", 9), bd=4, width=55)
        self.rst_pasta_dest.pack(side="left", fill="x", expand=True)
        tk.Button(fr_dest, text=" 📂 ",
            bg="#4c1d95", fg="white", font=("Consolas", 9), relief="flat", cursor="hand2",
            command=lambda: self._pick_folder(self.rst_pasta_dest, "Pasta Protheus_Data atual"),
        ).pack(side="left", padx=(4, 0))

        tk.Label(f,
            text="  ⚠  A pasta DESTINO será deletada e substituída. Não pode ser desfeito!",
            bg="#1a0d2e", fg="#fbbf24", font=("Consolas", 8), justify="left", anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 4))

        tk.Button(f, text="  📁  RESTAURAR PASTA  ",
            bg="#7c3aed", fg="white", font=("Consolas", 10, "bold"),
            relief="flat", cursor="hand2", activebackground="#6d28d9",
            command=self._restaurar_pasta,
        ).pack(pady=(6, 14))

    # ── Seção 3: Restaurar tudo ───────────────────────────

    def _secao_tudo(self, parent) -> None:
        f = tk.Frame(parent, bg="#1a1200")
        f.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(f, text="  ⚡  RESTAURAR BANCO + PASTA (completo)",
            bg="#1a1200", fg="#fbbf24", font=("Consolas", 10, "bold"), anchor="w",
        ).pack(fill="x", pady=(10, 6))
        tk.Frame(f, bg="#4a3000", height=1).pack(fill="x", padx=12)
        tk.Label(f, text="  Baixa os dois ZIPs e restaura banco + pasta em sequência.",
            bg="#1a1200", fg="#e0e0a0", font=("Consolas", 8), anchor="w",
        ).pack(fill="x", padx=12, pady=(6, 4))

        tk.Button(f, text="  ⚡  RESTAURAR TUDO  ",
            bg="#d97706", fg="white", font=("Consolas", 11, "bold"),
            relief="flat", cursor="hand2", activebackground="#b45309",
            command=self._restaurar_tudo,
        ).pack(pady=(6, 14))

    # ── Seção 4: Log ──────────────────────────────────────

    def _secao_log(self, parent) -> None:
        tk.Label(parent, text="Log de execução:",
            bg="#1a1a1a", fg="#a0a0c0", font=("Consolas", 9),
        ).pack(anchor="w", padx=20, pady=(4, 2))

        self._log_widget = tk.Text(parent,
            bg="#050510", fg="#4ade80",
            font=("Consolas", 8),
            height=10, relief="flat", bd=4, state="disabled")
        self._log_widget.pack(fill="x", padx=20, pady=(0, 16))

    # ══════════════════════════════════════════════════════
    #  HELPERS DE UI
    # ══════════════════════════════════════════════════════

    def _label_dica(self, parent, texto: str, dica: str = "") -> None:
        linha = tk.Frame(parent, bg=parent.cget("bg"))
        linha.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(linha, text=texto,
            bg=parent.cget("bg"), fg="#a0a0c0", font=("Consolas", 9), anchor="w",
        ).pack(side="left")
        if dica:
            tk.Label(linha, text=f"  ({dica})",
                bg=parent.cget("bg"), fg="#4a4a6a", font=("Consolas", 8), anchor="w",
            ).pack(side="left")

    def _entry(self, parent, valor: str, largura: int, senha: bool = False) -> tk.Entry:
        e = tk.Entry(parent,
            bg="#0a1929", fg="#e0e0f0", insertbackground="#4ade80",
            relief="flat", font=("Consolas", 9), bd=4, width=largura)
        if senha:
            e.config(show="*")
        e.insert(0, valor)
        e.pack(anchor="w", padx=12, pady=(2, 2))
        return e

    def _pick_file(self, entry: tk.Entry, titulo: str, tipos: list) -> None:
        caminho = filedialog.askopenfilename(title=titulo, filetypes=tipos)
        if caminho:
            entry.delete(0, "end")
            entry.insert(0, caminho)

    def _pick_folder(self, entry: tk.Entry, titulo: str) -> None:
        caminho = filedialog.askdirectory(title=titulo)
        if caminho:
            entry.delete(0, "end")
            entry.insert(0, caminho)

    def _toggle_banco(self) -> None:
        if self.rst_banco_origem.get() == "download":
            self._fpanel_banco_loc.pack_forget()
            self._fpanel_banco_dl.pack(fill="x")
        else:
            self._fpanel_banco_dl.pack_forget()
            self._fpanel_banco_loc.pack(fill="x")

    def _toggle_pasta(self) -> None:
        if self.rst_pasta_origem.get() == "download":
            self._fpanel_pasta_loc.pack_forget()
            self._fpanel_pasta_dl.pack(fill="x")
        else:
            self._fpanel_pasta_dl.pack_forget()
            self._fpanel_pasta_loc.pack(fill="x")

    # ── Log ───────────────────────────────────────────────

    def _log(self, mensagem: str) -> None:
        self._log_widget.config(state="normal")
        self._log_widget.insert("end", mensagem + "\n")
        self._log_widget.see("end")
        self._log_widget.config(state="disabled")
        self.update_idletasks()

    def _log_limpar(self) -> None:
        self._log_widget.config(state="normal")
        self._log_widget.delete("1.0", "end")
        self._log_widget.config(state="disabled")

    # ══════════════════════════════════════════════════════
    #  DOWNLOAD / EXTRAÇÃO
    # ══════════════════════════════════════════════════════

    def _montar_url(self, nome_arquivo: str) -> str:
        base = self.rst_url_base.get().strip().rstrip("/").rstrip("\\")
        if base.startswith("http://") or base.startswith("https://"):
            return f"{base}/{nome_arquivo}"
        return os.path.join(base, nome_arquivo)

    def _baixar_zip(self, url: str, destino: str) -> None:
        if url.startswith("http://") or url.startswith("https://"):
            self.after(0, self._log, f"  Baixando: {url}")
            req = urllib.request.Request(url)
            usuario = self.rst_srv_user.get().strip()
            senha   = self.rst_srv_pass.get().strip()
            if usuario and senha:
                cred = base64.b64encode(f"{usuario}:{senha}".encode()).decode()
                req.add_header("Authorization", f"Basic {cred}")

            with urllib.request.urlopen(req) as resp:
                ct = resp.headers.get("Content-Type", "")
                if "text/html" in ct:
                    raise ValueError(
                        "O servidor retornou HTML em vez do arquivo ZIP.\n"
                        "Verifique URL, usuário e senha."
                    )
                tamanho = resp.headers.get("Content-Length")
                if tamanho:
                    self.after(0, self._log, f"  Tamanho: {int(tamanho)/1024/1024:.1f} MB")
                with open(destino, "wb") as f:
                    baixados, ultimo_pct = 0, -1
                    while True:
                        bloco = resp.read(512 * 1024)
                        if not bloco:
                            break
                        f.write(bloco)
                        baixados += len(bloco)
                        if tamanho:
                            pct = int(baixados / int(tamanho) * 100)
                            if pct != ultimo_pct and pct % 10 == 0:
                                self.after(0, self._log, f"  {pct}%  ({baixados/1024/1024:.1f} MB)")
                                ultimo_pct = pct
        else:
            self.after(0, self._log, f"  Copiando: {url}")
            shutil.copy2(url, destino)

        if not zipfile.is_zipfile(destino):
            with open(destino, "rb") as f:
                primeiros = f.read(500)
            os.remove(destino)
            raise ValueError(
                "O arquivo baixado não é um ZIP válido.\n\n"
                + primeiros.decode("utf-8", errors="replace")[:400]
            )
        self.after(0, self._log, f"  Download concluído: {os.path.basename(destino)}")

    def _detectar_formato(self, caminho: str) -> str:
        with open(caminho, "rb") as f:
            header = f.read(6)
        if header[:2] == b"PK":
            return "zip"
        if header[:2] == b"7z":
            return "7z"
        return "desconhecido"

    def _extrair_zip(self, caminho: str, pasta_extracao: str) -> list:
        self.after(0, self._log, f"  Extraindo: {os.path.basename(caminho)}")
        os.makedirs(pasta_extracao, exist_ok=True)
        fmt = self._detectar_formato(caminho)
        self.after(0, self._log, f"  Formato detectado: {fmt.upper()}")

        if fmt == "zip":
            with zipfile.ZipFile(caminho, "r") as zf:
                zf.extractall(pasta_extracao)
                nomes = zf.namelist()
        elif fmt == "7z":
            if not PY7ZR_DISPONIVEL:
                raise RuntimeError(
                    "Arquivo 7z detectado mas py7zr não está instalado.\n"
                    "Execute: pip install py7zr"
                )
            with py7zr.SevenZipFile(caminho, mode="r") as sz:
                sz.extractall(path=pasta_extracao)
                nomes = sz.getnames()
        else:
            raise ValueError(f"Formato não reconhecido: {caminho}")

        self.after(0, self._log, f"  Extraídos {len(nomes)} arquivo(s).")
        return nomes

    # ══════════════════════════════════════════════════════
    #  AÇÕES DE RESTAURAÇÃO
    # ══════════════════════════════════════════════════════

    def _restaurar_banco(self) -> None:
        threading.Thread(target=self._exec_banco, daemon=True).start()

    def _exec_banco(self) -> None:
        servidor   = CONFIG["server"]
        banco      = self.rst_banco.get().strip()
        usuario    = self.rst_usuario.get().strip()
        senha      = self.rst_senha.get().strip()
        pasta_tmp  = self.rst_pasta_tmp.get().strip()
        limpar_tmp = self.rst_limpar_tmp.get()
        origem     = self.rst_banco_origem.get()

        if origem == "download":
            zip_banco = self.rst_zip_banco.get().strip()
            nome_bak  = self.rst_nome_bak.get().strip()
            if not all([banco, usuario, senha, zip_banco, pasta_tmp]):
                self.after(0, messagebox.showwarning, "Atenção",
                    "Preencha todos os campos da seção de banco!")
                return
        else:
            arquivo_local = self.rst_bak_local.get().strip()
            nome_bak_loc  = self.rst_nome_bak_local.get().strip()
            if not all([banco, usuario, senha, arquivo_local]):
                self.after(0, messagebox.showwarning, "Atenção",
                    "Preencha Banco, Usuário, Senha e o arquivo local!")
                return

        self.after(0, self._log_limpar)
        self.after(0, self._log, "[BANCO] === Iniciando restauração do banco ===")

        try:
            os.makedirs(pasta_tmp, exist_ok=True)
            local_zip = pasta_extracao = None

            if origem == "download":
                self.after(0, self._log, "[BANCO] Passo 1/4: Baixando ZIP...")
                url_zip   = self._montar_url(zip_banco)
                local_zip = os.path.join(pasta_tmp, zip_banco)
                self._baixar_zip(url_zip, local_zip)

                self.after(0, self._log, "[BANCO] Passo 2/4: Extraindo .bak...")
                pasta_extracao = os.path.join(pasta_tmp, "banco_extraido")
                nomes = self._extrair_zip(local_zip, pasta_extracao)
                bak_extraido = self._encontrar_bak(nomes, pasta_extracao, nome_bak)
            else:
                self.after(0, self._log, "[BANCO] Passo 1/4: Verificando arquivo local...")
                ext = os.path.splitext(arquivo_local)[1].lower()
                if ext in (".zip", ".7z"):
                    self.after(0, self._log, "[BANCO] Passo 2/4: Extraindo .bak do arquivo local...")
                    pasta_extracao = os.path.join(pasta_tmp, "banco_extraido")
                    nomes = self._extrair_zip(arquivo_local, pasta_extracao)
                    bak_extraido = self._encontrar_bak(nomes, pasta_extracao, nome_bak_loc)
                elif ext == ".bak":
                    self.after(0, self._log, "[BANCO] Passo 2/4: Usando .bak direto.")
                    bak_extraido = arquivo_local
                else:
                    raise ValueError(f"Extensão '{ext}' não suportada. Use .bak, .zip ou .7z")

            self.after(0, self._log, "[BANCO] Passo 3/4: Executando RESTORE DATABASE...")
            conn_str = (
                f"DRIVER={{{CONFIG['driver']}}};"
                f"SERVER={servidor};DATABASE=master;"
                f"UID={usuario};PWD={senha};TrustServerCertificate=yes;"
            )
            conn = pyodbc.connect(conn_str, autocommit=True)
            cur  = conn.cursor()
            self.after(0, self._log, "  Encerrando conexões ativas...")
            cur.execute(f"ALTER DATABASE [{banco}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
            self.after(0, self._log, "  Restaurando (pode demorar)...")
            cur.execute(f"""
                RESTORE DATABASE [{banco}]
                FROM DISK = N'{bak_extraido}'
                WITH REPLACE, RECOVERY
            """)
            cur.execute(f"ALTER DATABASE [{banco}] SET MULTI_USER")
            conn.close()
            self.after(0, self._log, "  RESTORE concluído!")

            if limpar_tmp and origem == "download":
                self.after(0, self._log, "[BANCO] Passo 4/4: Limpando temporários...")
                if local_zip and os.path.exists(local_zip):
                    os.remove(local_zip)
                if pasta_extracao and os.path.exists(pasta_extracao):
                    shutil.rmtree(pasta_extracao)
                self.after(0, self._log, "  Limpeza concluída.")
            else:
                self.after(0, self._log, "[BANCO] Passo 4/4: Limpeza ignorada.")

            self.after(0, self._log, f"[BANCO] ✔ Banco '{banco}' restaurado com sucesso!")
            self.after(0, self.atualizar_rodape, f"✔  Banco {banco} restaurado com sucesso!")

        except Exception as e:
            self.after(0, self._log, f"[BANCO] ❌ ERRO: {e}")
            self.after(0, messagebox.showerror, "Erro na Restauração do Banco", str(e))

    def _encontrar_bak(self, nomes: list, pasta: str, nome_bak: str) -> str:
        if nome_bak:
            caminho = os.path.join(pasta, nome_bak)
            if not os.path.exists(caminho):
                raise FileNotFoundError(f"Arquivo '{nome_bak}' não encontrado no ZIP.")
            return caminho
        baks = [n for n in nomes if n.lower().endswith(".bak")]
        if not baks:
            raise FileNotFoundError("Nenhum .bak encontrado no ZIP.")
        self.after(0, self._log, f"  .bak encontrado: {baks[0]}")
        return os.path.join(pasta, baks[0])

    def _restaurar_pasta(self) -> None:
        threading.Thread(target=self._exec_pasta, daemon=True).start()

    def _exec_pasta(self) -> None:
        destino    = self.rst_pasta_dest.get().strip()
        pasta_tmp  = self.rst_pasta_tmp.get().strip()
        limpar_tmp = self.rst_limpar_tmp.get()
        origem     = self.rst_pasta_origem.get()

        if origem == "download":
            zip_pasta = self.rst_zip_pasta.get().strip()
            if not all([zip_pasta, destino, pasta_tmp]):
                self.after(0, messagebox.showwarning, "Atenção",
                    "Preencha todos os campos da seção de pasta!")
                return
        else:
            zip_local = self.rst_zip_pasta_local.get().strip()
            if not all([zip_local, destino]):
                self.after(0, messagebox.showwarning, "Atenção",
                    "Informe o arquivo ZIP local e a pasta DESTINO!")
                return

        confirmar = [False]
        def pedir():
            confirmar[0] = messagebox.askyesno(
                "Confirmar restauração",
                f"Esta operação irá DELETAR a pasta:\n{destino}\n\n"
                "e substituí-la pelo conteúdo do ZIP.\n\nDeseja continuar?")
        self.after(0, pedir)
        time.sleep(0.6)
        if not confirmar[0]:
            self.after(0, self._log, "[PASTA] Operação cancelada.")
            return

        self.after(0, self._log, "[PASTA] === Iniciando restauração da pasta ===")

        try:
            os.makedirs(pasta_tmp, exist_ok=True)

            if origem == "download":
                self.after(0, self._log, "[PASTA] Passo 1/4: Baixando ZIP...")
                url_zip   = self._montar_url(zip_pasta)
                local_zip = os.path.join(pasta_tmp, zip_pasta)
                self._baixar_zip(url_zip, local_zip)
            else:
                self.after(0, self._log, "[PASTA] Passo 1/4: Usando ZIP local...")
                local_zip = zip_local
                self.after(0, self._log, f"  Arquivo: {local_zip}")

            self.after(0, self._log, "[PASTA] Passo 2/4: Extraindo ZIP...")
            pasta_extracao = os.path.join(pasta_tmp, "pasta_extraida")
            self._extrair_zip(local_zip, pasta_extracao)

            itens = os.listdir(pasta_extracao)
            if len(itens) == 1 and os.path.isdir(os.path.join(pasta_extracao, itens[0])):
                pasta_extracao = os.path.join(pasta_extracao, itens[0])
                self.after(0, self._log, f"  Subpasta raiz: {itens[0]}")

            self.after(0, self._log, "[PASTA] Passo 3/4: Deletando pasta destino...")
            if os.path.exists(destino):
                shutil.rmtree(destino)
                self.after(0, self._log, "  Pasta deletada.")

            self.after(0, self._log, "[PASTA] Passo 4/4: Copiando para destino...")
            shutil.copytree(pasta_extracao, destino)
            self.after(0, self._log, "  Cópia concluída!")

            if limpar_tmp:
                pasta_base = os.path.join(pasta_tmp, "pasta_extraida")
                if os.path.exists(pasta_base):
                    shutil.rmtree(pasta_base)
                if origem == "download" and os.path.exists(local_zip):
                    os.remove(local_zip)
                self.after(0, self._log, "  Temporários removidos.")

            self.after(0, self._log, "[PASTA] ✔ Pasta Protheus_Data restaurada!")
            self.after(0, self.atualizar_rodape, "✔  Pasta Protheus_Data restaurada com sucesso!")

        except PermissionError as e:
            self.after(0, self._log, f"[PASTA] ❌ Erro de permissão: {e}")
            self.after(0, self._log, "[PASTA] Dica: feche o Protheus e o AppServer!")
            self.after(0, messagebox.showerror, "Erro de Permissão",
                "Feche o Protheus/AppServer e tente novamente.\n\n" + str(e))
        except Exception as e:
            self.after(0, self._log, f"[PASTA] ❌ ERRO: {e}")
            self.after(0, messagebox.showerror, "Erro na Restauração da Pasta", str(e))

    def _restaurar_tudo(self) -> None:
        threading.Thread(target=self._exec_tudo, daemon=True).start()

    def _exec_tudo(self) -> None:
        self.after(0, self._log_limpar)
        self.after(0, self._log, "[⚡] === RESTAURAÇÃO COMPLETA ===")
        self._exec_banco()
        time.sleep(1)
        self.after(0, self._log, "[⚡] Iniciando restauração da pasta...")
        self._exec_pasta()
        self.after(0, self._log, "[⚡] ✔ Restauração completa finalizada!")
