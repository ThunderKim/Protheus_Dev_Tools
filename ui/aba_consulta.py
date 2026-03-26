"""
ui/aba_consulta.py
==================
Widget reutilizável para abas de consulta ao dicionário Protheus.
Cada aba contém: filtro, histórico, botões de exportação e Treeview.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from historico import HistoricoConsultas
from ui.exportacao import extrair_dados_treeview, exportar_csv, exportar_xlsx


class AbaConsulta(ttk.Frame):
    """Frame completo de uma aba de consulta (filtro + Treeview + exportação)."""

    def __init__(
        self,
        notebook: ttk.Notebook,
        nome_aba: str,
        banco,
        metodo_banco: str,
        historico: HistoricoConsultas,
        atualizar_rodape,
        verificar_conexao,
    ) -> None:
        super().__init__(notebook)
        notebook.add(self, text=f"  {nome_aba}  ")

        self.nome_aba       = nome_aba
        self.banco          = banco
        self.metodo_banco   = metodo_banco
        self.historico      = historico
        self.atualizar_rodape   = atualizar_rodape
        self.verificar_conexao  = verificar_conexao

        self._construir()

    # ── Construção da UI ──────────────────────────────────

    def _construir(self) -> None:
        linha_busca = tk.Frame(self, bg="#004064")
        linha_busca.pack(fill="x", padx=8, pady=8)

        # Filtro
        tk.Label(
            linha_busca, text="🔍  Filtro:",
            bg="#004064", fg="#f5f8fa", font=("Consolas", 9),
        ).pack(side="left", padx=(0, 6))

        self.entry_filtro = tk.Entry(
            linha_busca,
            bg="#13131f", fg="#e0e0f0",
            insertbackground="#004064",
            relief="flat", font=("Consolas", 10), bd=4, width=40,
        )
        self.entry_filtro.pack(side="left")
        self.entry_filtro.bind("<Return>", lambda e: self.buscar())

        # Botão buscar
        tk.Button(
            linha_busca, text="  BUSCAR  ",
            bg="#13131f", fg="white",
            font=("Consolas", 9, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#6d28d9",
            command=self.buscar,
        ).pack(side="left", padx=8)

        # Botão histórico
        btn_hist = tk.Menubutton(
            linha_busca, text="🕘",
            bg="#13131f", fg="#a0a0c0",
            font=("Consolas", 10),
            relief="flat", cursor="hand2",
            activebackground="#2a2a3e",
        )
        btn_hist.pack(side="left", padx=(0, 4))

        self._menu_hist = tk.Menu(
            btn_hist, tearoff=0,
            bg="#13131f", fg="#e0e0f0",
            activebackground="#004064",
            font=("Consolas", 9),
        )
        btn_hist["menu"] = self._menu_hist
        btn_hist.bind("<ButtonPress>", lambda e: self._rebuild_hist_menu())

        # Contador
        self.lbl_count = tk.Label(
            linha_busca, text="",
            bg="#0079B8", fg="#004064", font=("Consolas", 8),
        )
        self.lbl_count.pack(side="left", padx=8)

        # Exportação (direita)
        tk.Button(
            linha_busca, text="📄 CSV",
            bg="#064e3b", fg="white",
            font=("Consolas", 8, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#065f46",
            command=self._exportar_csv,
        ).pack(side="right", padx=(2, 0))

        tk.Button(
            linha_busca, text="📊 XLSX",
            bg="#1e3a5f", fg="white",
            font=("Consolas", 8, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#1e4976",
            command=self._exportar_xlsx,
        ).pack(side="right", padx=(2, 0))

        # Treeview
        frame_tree = tk.Frame(self, bg="#0079B8")
        frame_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(frame_tree, show="headings", selectmode="browse")

        sv = ttk.Scrollbar(frame_tree, orient="vertical",   command=self.tree.yview)
        sh = ttk.Scrollbar(frame_tree, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)

        sv.pack(side="right",  fill="y")
        sh.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("par",   background="#13131f")
        self.tree.tag_configure("impar", background="#1a1a2e")

    # ── Busca ─────────────────────────────────────────────

    def buscar(self) -> None:
        if not self.verificar_conexao():
            messagebox.showwarning("Atenção", "Conecte ao banco antes de buscar!")
            return

        filtro = self.entry_filtro.get().strip()
        self.historico.registrar(self.nome_aba, filtro)

        threading.Thread(
            target=self._thread_busca, args=(filtro,), daemon=True
        ).start()

    def _thread_busca(self, filtro: str) -> None:
        try:
            metodo = getattr(self.banco, self.metodo_banco)
            colunas, linhas = metodo(filtro)
            self.after(0, self._preencher, colunas, linhas)
        except Exception as e:
            self.after(0, messagebox.showerror, "Erro na Consulta", str(e))

    def _preencher(self, colunas: list, linhas: list) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = colunas

        for col in colunas:
            self.tree.heading(
                col, text=col,
                command=lambda c=col: self._ordenar(c),
            )
            self.tree.column(col, width=max(len(col) * 10, 100), minwidth=60)

        for i, linha in enumerate(linhas):
            tag = "par" if i % 2 == 0 else "impar"
            valores = [str(v).strip() if v is not None else "" for v in linha]
            self.tree.insert("", "end", values=valores, tags=(tag,))

        total = len(linhas)
        self.lbl_count.config(text=f"{total} registro(s) encontrado(s)")
        self.atualizar_rodape(f"Última consulta: {self.nome_aba} — {total} registros")

    # ── Ordenação ─────────────────────────────────────────

    def _ordenar(self, coluna: str) -> None:
        itens = [(self.tree.set(k, coluna), k) for k in self.tree.get_children("")]
        reverso = getattr(self.tree, "_ord_reverso", False)
        itens.sort(reverse=reverso)
        self.tree._ord_reverso = not reverso

        for idx, (_, k) in enumerate(itens):
            self.tree.move(k, "", idx)
            self.tree.item(k, tags=("par" if idx % 2 == 0 else "impar",))

    # ── Histórico ─────────────────────────────────────────

    def _rebuild_hist_menu(self) -> None:
        self._menu_hist.delete(0, "end")
        itens = self.historico.obter(self.nome_aba)
        if not itens:
            self._menu_hist.add_command(label="(sem histórico)", state="disabled")
            return
        for termo in itens:
            self._menu_hist.add_command(
                label=termo,
                command=lambda t=termo: self._aplicar_hist(t),
            )
        self._menu_hist.add_separator()
        self._menu_hist.add_command(
            label="🗑  Limpar histórico",
            command=lambda: self.historico.limpar(self.nome_aba),
        )

    def _aplicar_hist(self, termo: str) -> None:
        self.entry_filtro.delete(0, "end")
        self.entry_filtro.insert(0, termo)
        self.buscar()

    # ── Exportação ────────────────────────────────────────

    def _exportar_csv(self) -> None:
        colunas, linhas = extrair_dados_treeview(self.tree)
        nome = self.nome_aba.split("—")[0].strip().replace(" ", "_") + ".csv"
        exportar_csv(colunas, linhas, nome, self.atualizar_rodape)

    def _exportar_xlsx(self) -> None:
        colunas, linhas = extrair_dados_treeview(self.tree)
        nome = self.nome_aba.split("—")[0].strip().replace(" ", "_") + ".xlsx"
        exportar_xlsx(colunas, linhas, nome, self.nome_aba[:31], self.atualizar_rodape)
