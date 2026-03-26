"""
ui/aba_sql_livre.py
===================
Aba de consulta SQL livre: editor de texto + Treeview + exportação.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from ui.exportacao import extrair_dados_treeview, exportar_csv, exportar_xlsx


class AbaSqlLivre(tk.Frame):
    """Aba com editor SQL livre, resultado em Treeview e exportação."""

    def __init__(
        self,
        notebook: ttk.Notebook,
        banco,
        verificar_conexao,
        atualizar_rodape,
    ) -> None:
        super().__init__(notebook, bg="#0d0d1a")
        notebook.add(self, text="  🛠 SQL Livre  ")

        self.banco              = banco
        self.verificar_conexao  = verificar_conexao
        self.atualizar_rodape   = atualizar_rodape

        self._construir()

    # ── Construção da UI ──────────────────────────────────

    def _construir(self) -> None:
        # Título
        tk.Label(
            self, text="Consulta SQL Livre",
            bg="#0d0d1a", fg="#f5f8fa", font=("Consolas", 12, "bold"),
        ).pack(pady=(12, 2), padx=12, anchor="w")

        tk.Label(
            self, text="Execute qualquer SELECT diretamente no banco conectado.",
            bg="#0d0d1a", fg="#6b6b8a", font=("Consolas", 8),
        ).pack(padx=12, anchor="w")

        # Editor SQL
        frame_ed = tk.Frame(self, bg="#0d0d1a")
        frame_ed.pack(fill="x", padx=12, pady=(8, 0))

        self.editor = tk.Text(
            frame_ed,
            bg="#050515", fg="#e0e0f0",
            insertbackground="#4ade80",
            font=("Consolas", 10),
            height=8, relief="flat", bd=6,
            undo=True, wrap="none",
        )
        self.editor.pack(fill="x")
        self.editor.insert(
            "1.0", "SELECT TOP 100\n    *\nFROM SX3T10\nWHERE D_E_L_E_T_ = ' '\n"
        )

        # Barra de botões
        linha = tk.Frame(self, bg="#0d0d1a")
        linha.pack(fill="x", padx=12, pady=6)

        tk.Button(
            linha, text="  ▶  EXECUTAR  (F5)  ",
            bg="#059669", fg="white",
            font=("Consolas", 10, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#047857",
            command=self.executar,
        ).pack(side="left")

        tk.Button(
            linha, text="🗑 Limpar",
            bg="#1a1a2e", fg="#a0a0c0",
            font=("Consolas", 9),
            relief="flat", cursor="hand2",
            command=lambda: self.editor.delete("1.0", "end"),
        ).pack(side="left", padx=(8, 0))

        self.lbl_count = tk.Label(
            linha, text="",
            bg="#0d0d1a", fg="#6b6b8a", font=("Consolas", 8),
        )
        self.lbl_count.pack(side="left", padx=12)

        tk.Button(
            linha, text="📄 CSV",
            bg="#064e3b", fg="white",
            font=("Consolas", 8, "bold"),
            relief="flat", cursor="hand2",
            command=self._exportar_csv,
        ).pack(side="right", padx=(2, 0))

        tk.Button(
            linha, text="📊 XLSX",
            bg="#1e3a5f", fg="white",
            font=("Consolas", 8, "bold"),
            relief="flat", cursor="hand2",
            command=self._exportar_xlsx,
        ).pack(side="right", padx=(2, 0))

        # Treeview
        frame_tree = tk.Frame(self, bg="#0d0d1a")
        frame_tree.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.tree = ttk.Treeview(frame_tree, show="headings", selectmode="browse")
        sv = ttk.Scrollbar(frame_tree, orient="vertical",  command=self.tree.yview)
        sh = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)
        sv.pack(side="right",  fill="y")
        sh.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("par",   background="#13131f")
        self.tree.tag_configure("impar", background="#1a1a2e")

        # Atalho F5 (escopo global da janela)
        self.bind_all("<F5>", lambda e: self.executar())

    # ── Execução ──────────────────────────────────────────

    def executar(self) -> None:
        if not self.verificar_conexao():
            messagebox.showwarning("Atenção", "Conecte ao banco antes de executar!")
            return
        sql = self.editor.get("1.0", "end").strip()
        if not sql:
            return
        threading.Thread(target=self._thread_exec, args=(sql,), daemon=True).start()

    def _thread_exec(self, sql: str) -> None:
        try:
            colunas, linhas = self.banco.consultar_sql_livre(sql)
            self.after(0, self._preencher, colunas, linhas)
        except Exception as e:
            self.after(0, messagebox.showerror, "Erro SQL", str(e))

    def _preencher(self, colunas: list, linhas: list) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = colunas
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=max(len(col) * 10, 80), minwidth=60)
        for i, linha in enumerate(linhas):
            tag = "par" if i % 2 == 0 else "impar"
            valores = [str(v).strip() if v is not None else "" for v in linha]
            self.tree.insert("", "end", values=valores, tags=(tag,))
        total = len(linhas)
        self.lbl_count.config(text=f"{total} registro(s)")
        self.atualizar_rodape(f"SQL Livre — {total} registros retornados")

    # ── Exportação ────────────────────────────────────────

    def _exportar_csv(self) -> None:
        colunas, linhas = extrair_dados_treeview(self.tree)
        exportar_csv(colunas, linhas, "sql_livre.csv", self.atualizar_rodape)

    def _exportar_xlsx(self) -> None:
        colunas, linhas = extrair_dados_treeview(self.tree)
        exportar_xlsx(colunas, linhas, "sql_livre.xlsx", "SQL Livre", self.atualizar_rodape)
