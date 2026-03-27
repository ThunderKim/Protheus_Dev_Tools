"""
ui/app.py
=========
Janela principal da aplicação.
Orquestra todas as abas e o painel de conexão.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from config import CONFIG, carregar_conexoes, salvar_conexoes
from database import BancoDados
from historico import HistoricoConsultas

from ui.aba_consulta    import AbaConsulta
from ui.aba_sql_livre   import AbaSqlLivre
from ui.aba_nfe         import AbaNfe
from ui.aba_restauracao import AbaRestauracao
from ui.aba_api_fake    import AbaApiFake
from ui.ajuda           import abrir_ajuda


# Mapeamento: nome da aba → método do BancoDados
TABELAS = {
    "SX6 — Parâmetros":     "consultar_sx6",
    "SX3 — Campos":         "consultar_sx3",
    "SX2 — Tabelas":        "consultar_sx2",
    "SIX — Índices":        "consultar_six",
    "SX1 — Perguntas":      "consultar_sx1",
    "SX5 — Tab. Genéricas": "consultar_sx5",
    "SX7 — Gatilhos":       "consultar_sx7",
    "SXB — Consultas F3":   "consultar_sxb",
    "SYS_COMPANY — Filiais": "consultar_sys_company",
}


class App(tk.Tk):
    """Janela raiz — ponto de entrada da UI."""

    def __init__(self) -> None:
        super().__init__()

        self.banco           = BancoDados()
        self.conectado       = False
        self.historico       = HistoricoConsultas()
        self.conexoes_salvas = carregar_conexoes()

        self.title("Protheus Dicionário Tool")
        self.geometry("1100x680")
        self.configure(bg="#0079B8")
        self.resizable(True, True)

        self._criar_rodape()
        self._aplicar_estilo()
        self._criar_header()
        self._criar_painel_conexao()
        self._criar_notebook()        

        # Tenta conectar silenciosamente ao abrir
        self.after(100, lambda: self._conectar(silencioso=True))

    # ══════════════════════════════════════════════════════
    #  ESTILOS
    # ══════════════════════════════════════════════════════

    def _aplicar_estilo(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure("TNotebook",
            background="#0079B8", borderwidth=0)
        s.configure("TNotebook.Tab",
            background="#004064", foreground="#a0a0c0",
            padding=[14, 6], font=("Consolas", 9, "bold"))
        s.map("TNotebook.Tab",
            background=[("selected", "#004064")],
            foreground=[("selected", "#ffffff")])

        s.configure("Treeview",
            background="#13131f", foreground="#e0e0f0",
            fieldbackground="#13131f", rowheight=24,
            font=("Consolas", 9))
        s.configure("Treeview.Heading",
            background="#2a2a3e", foreground="#f2f2f5",
            font=("Consolas", 9, "bold"), relief="flat")
        s.map("Treeview",
            background=[("selected", "#004064")],
            foreground=[("selected", "#ffffff")])

        s.configure("Vertical.TScrollbar",
            background="#2a2a3e", troughcolor="#13131f", arrowcolor="#004064")
        s.configure("Horizontal.TScrollbar",
            background="#2a2a3e", troughcolor="#13131f", arrowcolor="#004064")
        s.configure("TFrame", background="#004064")

    # ══════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════

    def _criar_header(self) -> None:
        header = tk.Frame(self, bg="#13131f", height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header,
            text="⬡  PROTHEUS DICIONÁRIO TOOL",
            bg="#13131f", fg="#f5f8fa", font=("Consolas", 15, "bold"),
        ).pack(side="left", padx=20, pady=12)

        tk.Button(header, text="  ❓ AJUDA  ",
            bg="#004064", fg="white",
            font=("Consolas", 9, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#006090",
            command=lambda: abrir_ajuda(self),
        ).pack(side="right", padx=(0, 12), pady=10)

        self.lbl_status = tk.Label(header,
            text="● Desconectado",
            bg="#13131f", fg="#f87171", font=("Consolas", 9))
        self.lbl_status.pack(side="right", padx=20)

    # ══════════════════════════════════════════════════════
    #  PAINEL DE CONEXÃO
    # ══════════════════════════════════════════════════════

    def _criar_painel_conexao(self) -> None:
        painel = tk.Frame(self, bg="#0079B8")
        painel.pack(fill="x", padx=16, pady=(10, 0))

        # Linha 1: perfis
        linha_perfil = tk.Frame(painel, bg="#0079B8")
        linha_perfil.pack(fill="x", pady=(0, 4))

        tk.Label(linha_perfil, text="Perfil:",
            bg="#0079B8", fg="#f5f8fa", font=("Consolas", 8),
        ).pack(side="left", padx=(8, 2))

        self.combo_perfil = ttk.Combobox(linha_perfil,
            width=22, font=("Consolas", 8), state="readonly")
        self.combo_perfil.pack(side="left", padx=(0, 4))
        self.combo_perfil.bind("<<ComboboxSelected>>", self._carregar_perfil)

        tk.Button(linha_perfil, text="💾 Salvar",
            bg="#004064", fg="white", font=("Consolas", 8, "bold"),
            relief="flat", cursor="hand2", activebackground="#006090",
            command=self._salvar_perfil,
        ).pack(side="left", padx=(0, 2))

        tk.Button(linha_perfil, text="🗑 Excluir",
            bg="#4a1010", fg="white", font=("Consolas", 8, "bold"),
            relief="flat", cursor="hand2", activebackground="#7a2020",
            command=self._excluir_perfil,
        ).pack(side="left", padx=(0, 12))

        # Linha 2: campos
        linha_campos = tk.Frame(painel, bg="#0079B8")
        linha_campos.pack(fill="x")

        campos = [
            ("Servidor",  "entry_server",   CONFIG["server"],   20),
            ("Banco",     "entry_database", CONFIG["database"], 20),
            ("Usuário",   "entry_user",     CONFIG["username"], 14),
            ("Senha",     "entry_pass",     CONFIG["password"], 14),
            ("Empresa",   "entry_empresa",  CONFIG["empresa"],   5),
        ]

        for label, attr, valor, largura in campos:
            tk.Label(linha_campos, text=f"{label}:",
                bg="#0079B8", fg="#f5f8fa", font=("Consolas", 8),
            ).pack(side="left", padx=(8, 2))

            entry = tk.Entry(linha_campos, width=largura,
                bg="#004064", fg="#e0e0f0",
                insertbackground="#004064",
                relief="flat", font=("Consolas", 9), bd=4)
            entry.insert(0, valor)
            if attr == "entry_pass":
                entry.config(show="*")
            entry.pack(side="left", padx=(0, 4))
            setattr(self, attr, entry)

        self.btn_conectar = tk.Button(linha_campos, text="  CONECTAR  ",
            bg="#004064", fg="white", font=("Consolas", 9, "bold"),
            relief="flat", cursor="hand2", activebackground="#6d28d9",
            command=self._conectar)
        self.btn_conectar.pack(side="left", padx=(12, 0))

        self._atualizar_combo_perfis()

    # ══════════════════════════════════════════════════════
    #  NOTEBOOK
    # ══════════════════════════════════════════════════════

    def _criar_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=12)

        # Abas de consulta ao dicionário
        for nome_aba, metodo in TABELAS.items():
            AbaConsulta(
                notebook        = self.notebook,
                nome_aba        = nome_aba,
                banco           = self.banco,
                metodo_banco    = metodo,
                historico       = self.historico,
                atualizar_rodape= self._set_rodape,
                verificar_conexao= lambda: self.conectado,
            )

        # Aba SQL livre
        AbaSqlLivre(
            notebook         = self.notebook,
            banco            = self.banco,
            verificar_conexao= lambda: self.conectado,
            atualizar_rodape = self._set_rodape,
        )

        # Calculadora NF-e
        AbaNfe(
            notebook        = self.notebook,
            atualizar_rodape= self._set_rodape,
        )

        # Restauração de base
        AbaRestauracao(
            notebook        = self.notebook,
            atualizar_rodape= self._set_rodape,
        )

        # API Fake
        AbaApiFake(
            notebook        = self.notebook,
            atualizar_rodape= self._set_rodape,
        )

    # ══════════════════════════════════════════════════════
    #  RODAPÉ
    # ══════════════════════════════════════════════════════

    def _criar_rodape(self) -> None:
        rodape = tk.Frame(self, bg="#13131f", height=28)
        rodape.pack(fill="x", side="bottom")
        rodape.pack_propagate(False)

        self.lbl_rodape = tk.Label(rodape,
            text="Preencha as configurações de conexão e clique em CONECTAR",
            bg="#13131f", fg="#6b6b8a", font=("Consolas", 8))
        self.lbl_rodape.pack(side="left", padx=16, pady=6)

    def _set_rodape(self, texto: str) -> None:
        self.lbl_rodape.config(text=texto)

    # ══════════════════════════════════════════════════════
    #  CONEXÃO
    # ══════════════════════════════════════════════════════

    def _conectar(self, silencioso: bool = False) -> None:
        CONFIG["server"]   = self.entry_server.get().strip()
        CONFIG["database"] = self.entry_database.get().strip()
        CONFIG["username"] = self.entry_user.get().strip()
        CONFIG["password"] = self.entry_pass.get().strip()
        CONFIG["empresa"]  = self.entry_empresa.get().strip()

        try:
            self.banco.conectar()
            self.conectado = True
            self.lbl_status.config(text="● Conectado", fg="#4ade80")
            self._set_rodape(f"✔  Conectado em {CONFIG['server']} / {CONFIG['database']}")
            self.btn_conectar.config(text="  RECONECTAR  ")
            if not silencioso:
                messagebox.showinfo("Conexão", "✔ Conexão estabelecida com sucesso!")
        except Exception as e:
            self.conectado = False
            self.lbl_status.config(text="● Erro de conexão", fg="#f87171")
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar:\n\n{e}")

    # ══════════════════════════════════════════════════════
    #  PERFIS DE CONEXÃO
    # ══════════════════════════════════════════════════════

    def _atualizar_combo_perfis(self) -> None:
        nomes = list(self.conexoes_salvas.keys())
        self.combo_perfil["values"] = nomes
        if nomes:
            self.combo_perfil.set(nomes[0])
            self._carregar_perfil()
        else:
            self.combo_perfil.set("")

    def _carregar_perfil(self, event=None) -> None:
        nome = self.combo_perfil.get()
        if not nome or nome not in self.conexoes_salvas:
            return
        cfg = self.conexoes_salvas[nome]
        for campo, attr in [
            ("server",   "entry_server"),
            ("database", "entry_database"),
            ("username", "entry_user"),
            ("password", "entry_pass"),
            ("empresa",  "entry_empresa"),
        ]:
            e = getattr(self, attr)
            e.delete(0, "end")
            e.insert(0, cfg.get(campo, ""))
        self._set_rodape(f"Perfil '{nome}' carregado.")

    def _salvar_perfil(self) -> None:
        win = tk.Toplevel(self)
        win.title("Salvar Perfil de Conexão")
        win.geometry("380x140")
        win.configure(bg="#13131f")
        win.resizable(False, False)
        win.grab_set()
        win.focus_set()

        tk.Label(win, text="Nome do perfil:",
            bg="#13131f", fg="#f5f8fa", font=("Consolas", 10),
        ).pack(pady=(20, 4))

        var_nome = tk.StringVar(value=self.combo_perfil.get())
        entry_nome = tk.Entry(win, textvariable=var_nome,
            bg="#1a1a2e", fg="#e0e0f0", insertbackground="#ffffff",
            relief="flat", font=("Consolas", 10), bd=6, width=30)
        entry_nome.pack(pady=4)
        entry_nome.select_range(0, "end")
        entry_nome.focus_set()

        def confirmar():
            nome = var_nome.get().strip()
            if not nome:
                messagebox.showwarning("Atenção", "Informe um nome.", parent=win)
                return
            self.conexoes_salvas[nome] = {
                "server":   self.entry_server.get().strip(),
                "database": self.entry_database.get().strip(),
                "username": self.entry_user.get().strip(),
                "password": self.entry_pass.get().strip(),
                "empresa":  self.entry_empresa.get().strip(),
            }
            salvar_conexoes(self.conexoes_salvas)
            self._atualizar_combo_perfis()
            self.combo_perfil.set(nome)
            self._set_rodape(f"✔  Perfil '{nome}' salvo.")
            win.destroy()

        entry_nome.bind("<Return>", lambda e: confirmar())
        tk.Button(win, text="  SALVAR  ",
            bg="#059669", fg="white", font=("Consolas", 10, "bold"),
            relief="flat", cursor="hand2", command=confirmar,
        ).pack(pady=10)

    def _excluir_perfil(self) -> None:
        nome = self.combo_perfil.get()
        if not nome:
            return
        if not messagebox.askyesno("Excluir Perfil", f"Excluir o perfil '{nome}'?"):
            return
        self.conexoes_salvas.pop(nome, None)
        salvar_conexoes(self.conexoes_salvas)
        self._atualizar_combo_perfis()
        self._set_rodape(f"Perfil '{nome}' excluído.")
