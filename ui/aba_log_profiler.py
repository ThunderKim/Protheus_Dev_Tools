"""
ui/aba_log_profiler.py
======================
Aba de analise de arquivos FWLogProfiler do Protheus.

Estrutura do arquivo:
  Cabecalho com metadados (DateTime, Service, Method, Thread, T.Timer)
  Blocos CALL com uma ou mais linhas -- FROM:

  CALL    FUNCAO(ARQUIVO.PRW)   C   <qtd>  T  <total_s>  M  <max_s>
  -- FROM ORIGEM (ARQUIVO.PRW) (linha)  C  <qtd>  T  <total_s>  M  <max_s>

Metricas por CALL:
  C  = total de chamadas
  T  = tempo total acumulado (segundos)
  M  = tempo maximo em uma unica chamada (segundos)

A aba oferece:
  - Carregamento de arquivo via filedialog
  - Resumo geral (cabecalho + totais)
  - Tabela de top N funcoes por tempo total / max / chamadas
  - Busca/filtro por nome de funcao ou arquivo
  - Detalhes de uma funcao selecionada (todos os callers)
  - Grafico de barras horizontal (top 15 por tempo total)
  - Exportacao CSV / XLSX
"""

import re
import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass, field

from ui.exportacao import exportar_csv, exportar_xlsx

# ── Paleta ────────────────────────────────────────────────
BG        = "#0d0d1a"
BG_PANEL  = "#13131f"
BG_ENTRY  = "#1a1a2e"
BG_HEADER = "#0a1929"
FG        = "#e0e0f0"
FG_DIM    = "#6b6b8a"
FG_GREEN  = "#4ade80"
FG_YELLOW = "#fbbf24"
FG_RED    = "#f87171"
FG_BLUE   = "#60a5fa"
FG_PURPLE = "#a78bfa"
FG_ORANGE = "#fb923c"
ACCENT    = "#7c3aed"
FONT      = ("Consolas", 9)
FONT_BOLD = ("Consolas", 9, "bold")
FONT_BIG  = ("Consolas", 11, "bold")
FONT_MONO = ("Consolas", 9)
FONT_SM   = ("Consolas", 8)


# ══════════════════════════════════════════════════════════
#  ESTRUTURAS DE DADOS
# ══════════════════════════════════════════════════════════

@dataclass
class Caller:
    origem:   str        # nome da funcao chamadora
    arquivo:  str        # arquivo da funcao chamadora
    linha:    int        # linha no fonte
    calls:    int        # chamadas neste caller
    tempo_t:  float      # tempo total neste caller
    tempo_m:  float      # tempo maximo neste caller


@dataclass
class FuncaoCall:
    nome:     str
    arquivo:  str
    calls:    int
    tempo_t:  float      # T - tempo total
    tempo_m:  float      # M - tempo maximo
    callers:  list = field(default_factory=list)  # list[Caller]


@dataclass
class CabecalhoLog:
    datetime:  str = ""
    service:   str = ""
    method:    str = ""
    thread:    str = ""
    timer_s:   float = 0.0


# ══════════════════════════════════════════════════════════
#  PARSER
# ══════════════════════════════════════════════════════════

# CALL    NOME(ARQUIVO)   C  <n>  T  <t>  M  <m>
RE_CALL = re.compile(
    r"^CALL\s+(\S+)\(([^)]+)\)\s+C\s+(\d+)\s+T\s+([\d.]+)\s+M\s+([\d.]+)",
    re.IGNORECASE,
)

# -- FROM  NOME (ARQUIVO) (LINHA)  C  <n>  T  <t>  M  <m>
RE_FROM = re.compile(
    r"^--\s+FROM\s+(\S+)\s+\(([^)]+)\)\s+\((\d+)\)\s+C\s+(\d+)\s+T\s+([\d.]+)\s+M\s+([\d.]+)",
    re.IGNORECASE,
)

RE_DATETIME = re.compile(r"DateTime\s*\.\.*:\s*(.+)")
RE_SERVICE  = re.compile(r"Service\s*\.\.*:\s*(.+)")
RE_METHOD   = re.compile(r"Method\s*\.\.*:\s*(.+)")
RE_THREAD   = re.compile(r"Thread\s*\.\.*:\s*(.+)")
RE_TIMER    = re.compile(r"T\.Timer\s*\.+:\s*([\d.]+)")


def parse_log(caminho: str) -> tuple[CabecalhoLog, list[FuncaoCall]]:
    """Faz o parse do arquivo FWLogProfiler e retorna (cabecalho, funcoes)."""
    cabecalho = CabecalhoLog()
    funcoes: list[FuncaoCall] = []
    atual: FuncaoCall | None = None

    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        for linha in f:
            linha = linha.rstrip("\n")

            # Cabecalho
            m = RE_DATETIME.search(linha)
            if m:
                cabecalho.datetime = m.group(1).strip()
                continue
            m = RE_SERVICE.search(linha)
            if m:
                cabecalho.service = m.group(1).strip()
                continue
            m = RE_METHOD.search(linha)
            if m:
                cabecalho.method = m.group(1).strip()
                continue
            m = RE_THREAD.search(linha)
            if m:
                cabecalho.thread = m.group(1).strip()
                continue
            m = RE_TIMER.search(linha)
            if m:
                cabecalho.timer_s = float(m.group(1))
                continue

            # Linha CALL
            m = RE_CALL.match(linha)
            if m:
                atual = FuncaoCall(
                    nome     = m.group(1),
                    arquivo  = m.group(2),
                    calls    = int(m.group(3)),
                    tempo_t  = float(m.group(4)),
                    tempo_m  = float(m.group(5)),
                )
                funcoes.append(atual)
                continue

            # Linha -- FROM
            m = RE_FROM.match(linha)
            if m and atual:
                atual.callers.append(Caller(
                    origem  = m.group(1),
                    arquivo = m.group(2),
                    linha   = int(m.group(3)),
                    calls   = int(m.group(4)),
                    tempo_t = float(m.group(5)),
                    tempo_m = float(m.group(6)),
                ))

    return cabecalho, funcoes


# ══════════════════════════════════════════════════════════
#  ABA
# ══════════════════════════════════════════════════════════

ORDENACOES = [
    ("Tempo Total (T)",   "tempo_t"),
    ("Tempo Maximo (M)",  "tempo_m"),
    ("Nr. Chamadas (C)",  "calls"),
    ("Nome Funcao",       "nome"),
]

TOP_OPCOES = ["10", "20", "50", "100", "200", "Todos"]


class AbaLogProfiler(tk.Frame):

    def __init__(self, notebook: ttk.Notebook, atualizar_rodape) -> None:
        super().__init__(notebook, bg=BG)
        notebook.add(self, text="  📊 LogProfiler  ")

        self.atualizar_rodape = atualizar_rodape
        self._cabecalho: CabecalhoLog | None = None
        self._funcoes:   list[FuncaoCall]   = []
        self._funcoes_filtradas: list[FuncaoCall] = []
        self._arquivo_atual: str = ""

        self._construir()

    # ══════════════════════════════════════════════════════
    #  CONSTRUCAO
    # ══════════════════════════════════════════════════════

    def _construir(self) -> None:
        # ── Toolbar ───────────────────────────────────────
        toolbar = tk.Frame(self, bg=BG_PANEL)
        toolbar.pack(fill="x", padx=6, pady=(6, 0))

        tk.Button(toolbar, text="  📂  Abrir LogProfiler  ",
            bg=ACCENT, fg="white", font=FONT_BOLD,
            relief="flat", cursor="hand2", activebackground="#6d28d9",
            command=self._abrir_arquivo,
        ).pack(side="left", padx=(6, 0), pady=6)

        self.lbl_arquivo = tk.Label(toolbar,
            text="Nenhum arquivo carregado",
            bg=BG_PANEL, fg=FG_DIM, font=FONT_SM)
        self.lbl_arquivo.pack(side="left", padx=12)

        tk.Button(toolbar, text="📄 CSV",
            bg="#064e3b", fg="white", font=FONT_SM,
            relief="flat", cursor="hand2",
            command=self._exportar_csv,
        ).pack(side="right", padx=(2, 6), pady=6)

        tk.Button(toolbar, text="📊 XLSX",
            bg="#1e3a5f", fg="white", font=FONT_SM,
            relief="flat", cursor="hand2",
            command=self._exportar_xlsx,
        ).pack(side="right", padx=2, pady=6)

        # ── Resumo (cabecalho do log) ──────────────────────
        self._frame_resumo = tk.Frame(self, bg=BG_HEADER)
        self._frame_resumo.pack(fill="x", padx=6, pady=(4, 0))

        self._labels_resumo: dict[str, tk.Label] = {}
        cols_resumo = [
            ("Data/Hora",   "datetime"),
            ("Servico",     "service"),
            ("Metodo",      "method"),
            ("Thread",      "thread"),
            ("Tempo Total", "timer"),
            ("Funcoes",     "total_func"),
        ]
        for i, (lbl, key) in enumerate(cols_resumo):
            tk.Label(self._frame_resumo, text=f"{lbl}:",
                bg=BG_HEADER, fg=FG_DIM, font=FONT_SM,
            ).grid(row=0, column=i*2, padx=(10, 2), pady=4, sticky="e")
            lbl_val = tk.Label(self._frame_resumo, text="—",
                bg=BG_HEADER, fg=FG_BLUE, font=FONT_SM)
            lbl_val.grid(row=0, column=i*2+1, padx=(0, 10), pady=4, sticky="w")
            self._labels_resumo[key] = lbl_val

        # ── Controles de filtro / ordenacao ───────────────
        frame_ctrl = tk.Frame(self, bg=BG)
        frame_ctrl.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(frame_ctrl, text="🔍 Filtro:",
            bg=BG, fg=FG, font=FONT).pack(side="left")

        self.entry_filtro = tk.Entry(frame_ctrl, width=30,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            relief="flat", font=FONT_MONO, bd=4)
        self.entry_filtro.pack(side="left", padx=(4, 12))
        self.entry_filtro.bind("<KeyRelease>", lambda e: self._aplicar_filtro())

        tk.Label(frame_ctrl, text="Ordenar por:",
            bg=BG, fg=FG, font=FONT).pack(side="left")
        self.combo_ord = ttk.Combobox(frame_ctrl,
            values=[o[0] for o in ORDENACOES],
            width=18, font=FONT, state="readonly")
        self.combo_ord.set(ORDENACOES[0][0])
        self.combo_ord.pack(side="left", padx=(4, 12))
        self.combo_ord.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro())

        tk.Label(frame_ctrl, text="Exibir top:",
            bg=BG, fg=FG, font=FONT).pack(side="left")
        self.combo_top = ttk.Combobox(frame_ctrl,
            values=TOP_OPCOES, width=6, font=FONT, state="readonly")
        self.combo_top.set("50")
        self.combo_top.pack(side="left", padx=(4, 12))
        self.combo_top.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro())

        self.lbl_contagem = tk.Label(frame_ctrl, text="",
            bg=BG, fg=FG_DIM, font=FONT_SM)
        self.lbl_contagem.pack(side="left", padx=8)

        tk.Button(frame_ctrl, text="✕ Limpar",
            bg=BG_ENTRY, fg=FG_DIM, font=FONT_SM,
            relief="flat", cursor="hand2",
            command=self._limpar_filtro,
        ).pack(side="left")

        # ── Painel principal: tabela | detalhes ───────────
        paned = tk.PanedWindow(self, orient="horizontal",
            bg=BG, sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        frame_esq = tk.Frame(paned, bg=BG)
        frame_dir = tk.Frame(paned, bg=BG)
        paned.add(frame_esq, minsize=500)
        paned.add(frame_dir, minsize=360)

        self._construir_tabela(frame_esq)
        self._construir_detalhes(frame_dir)

    # ── Tabela principal ──────────────────────────────────

    def _construir_tabela(self, parent) -> None:
        tk.Label(parent, text="Funcoes por Tempo de Execucao",
            bg=BG, fg=FG_PURPLE, font=FONT_BOLD,
        ).pack(anchor="w", pady=(0, 4))

        frame_tree = tk.Frame(parent, bg=BG)
        frame_tree.pack(fill="both", expand=True)

        cols = ("rank", "funcao", "arquivo", "calls", "tempo_t", "tempo_m", "pct")
        self.tree = ttk.Treeview(frame_tree,
            columns=cols, show="headings", selectmode="browse")

        hdrs = [
            ("rank",    "#",             40),
            ("funcao",  "Funcao",       280),
            ("arquivo", "Arquivo",      140),
            ("calls",   "Chamadas",      80),
            ("tempo_t", "Tempo Total(s)",110),
            ("tempo_m", "Tempo Max(s)",  100),
            ("pct",     "% do Total",     80),
        ]
        for col, lbl, w in hdrs:
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w, minwidth=40, anchor="center"
                if col in ("rank", "calls", "tempo_t", "tempo_m", "pct") else "w")

        sv = ttk.Scrollbar(frame_tree, orient="vertical",   command=self.tree.yview)
        sh = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)
        sv.pack(side="right",  fill="y")
        sh.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # Tags de cor por faixa de tempo
        self.tree.tag_configure("critico", background="#2d0000", foreground=FG_RED)
        self.tree.tag_configure("alto",    background="#1a1200", foreground=FG_YELLOW)
        self.tree.tag_configure("medio",   background="#0d1a0d", foreground=FG_GREEN)
        self.tree.tag_configure("baixo",   background=BG_PANEL,  foreground=FG_DIM)

        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

    # ── Painel de detalhes ────────────────────────────────

    def _construir_detalhes(self, parent) -> None:
        tk.Label(parent, text="Detalhes da Funcao Selecionada",
            bg=BG, fg=FG_PURPLE, font=FONT_BOLD,
        ).pack(anchor="w", pady=(0, 4))

        # Card de metricas
        self._frame_card = tk.Frame(parent, bg=BG_HEADER)
        self._frame_card.pack(fill="x", pady=(0, 6))

        self._card_labels: dict[str, tk.Label] = {}
        card_campos = [
            ("Funcao",       "d_funcao"),
            ("Arquivo",      "d_arquivo"),
            ("Chamadas",     "d_calls"),
            ("Tempo Total",  "d_tempo_t"),
            ("Tempo Maximo", "d_tempo_m"),
            ("% do Total",   "d_pct"),
        ]
        for i, (lbl, key) in enumerate(card_campos):
            row = i // 2
            col_base = (i % 2) * 2
            tk.Label(self._frame_card, text=f"{lbl}:",
                bg=BG_HEADER, fg=FG_DIM, font=FONT_SM,
            ).grid(row=row, column=col_base, padx=(8, 2), pady=3, sticky="e")
            lv = tk.Label(self._frame_card, text="—",
                bg=BG_HEADER, fg=FG_BLUE, font=FONT_SM,
                anchor="w", wraplength=180)
            lv.grid(row=row, column=col_base+1, padx=(0, 8), pady=3, sticky="w")
            self._card_labels[key] = lv

        # Tabela de callers
        tk.Label(parent, text="Chamado a partir de (Callers):",
            bg=BG, fg=FG, font=FONT,
        ).pack(anchor="w", pady=(4, 2))

        frame_cal = tk.Frame(parent, bg=BG)
        frame_cal.pack(fill="both", expand=True)

        cols_c = ("origem", "arquivo", "linha", "calls", "tempo_t", "tempo_m")
        self.tree_callers = ttk.Treeview(frame_cal,
            columns=cols_c, show="headings", selectmode="browse")

        hdrs_c = [
            ("origem",  "Origem",    180),
            ("arquivo", "Arquivo",   110),
            ("linha",   "Linha",      50),
            ("calls",   "C",          40),
            ("tempo_t", "T(s)",        65),
            ("tempo_m", "M(s)",        65),
        ]
        for col, lbl, w in hdrs_c:
            self.tree_callers.heading(col, text=lbl)
            self.tree_callers.column(col, width=w, minwidth=30,
                anchor="center" if col in ("linha","calls","tempo_t","tempo_m") else "w")

        sv_c = ttk.Scrollbar(frame_cal, orient="vertical",
            command=self.tree_callers.yview)
        self.tree_callers.configure(yscrollcommand=sv_c.set)
        sv_c.pack(side="right", fill="y")
        self.tree_callers.pack(fill="both", expand=True)

        self.tree_callers.tag_configure("par",   background=BG_PANEL)
        self.tree_callers.tag_configure("impar",  background=BG_ENTRY)

        # Grafico de barras (canvas)
        tk.Label(parent, text="Top 15 — Tempo Total (barras):",
            bg=BG, fg=FG, font=FONT,
        ).pack(anchor="w", pady=(6, 2))

        self.canvas_grafico = tk.Canvas(parent,
            bg=BG_PANEL, highlightthickness=0, height=180)
        self.canvas_grafico.pack(fill="x", padx=0, pady=(0, 4))
        self.canvas_grafico.bind("<Configure>", lambda e: self._desenhar_grafico())

    # ══════════════════════════════════════════════════════
    #  CARREGAMENTO
    # ══════════════════════════════════════════════════════

    def _abrir_arquivo(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecionar arquivo LogProfiler",
            filetypes=[
                ("Log Profiler", "*.log"),
                ("Todos",        "*.*"),
            ],
        )
        if not caminho:
            return
        self._carregar(caminho)

    def _carregar(self, caminho: str) -> None:
        try:
            tamanho = os.path.getsize(caminho) / 1024
            self.lbl_arquivo.config(
                text=f"Carregando... ({tamanho:.0f} KB)", fg=FG_YELLOW)
            self.update_idletasks()

            cab, funcoes = parse_log(caminho)
            self._cabecalho   = cab
            self._funcoes     = funcoes
            self._arquivo_atual = caminho

            self._atualizar_resumo()
            self._aplicar_filtro()
            self._desenhar_grafico()

            nome = os.path.basename(caminho)
            self.lbl_arquivo.config(
                text=f"{nome}  ({len(funcoes)} funcoes  |  {tamanho:.0f} KB)",
                fg=FG_GREEN)
            self.atualizar_rodape(
                f"LogProfiler carregado: {nome}  —  {len(funcoes)} funcoes")

        except Exception as e:
            messagebox.showerror("Erro ao carregar arquivo", str(e))
            self.lbl_arquivo.config(text="Erro ao carregar arquivo", fg=FG_RED)

    # ══════════════════════════════════════════════════════
    #  ATUALIZACAO DA UI
    # ══════════════════════════════════════════════════════

    def _atualizar_resumo(self) -> None:
        cab = self._cabecalho
        if not cab:
            return
        self._labels_resumo["datetime"].config(text=cab.datetime or "—")
        self._labels_resumo["service"].config( text=cab.service  or "—")
        self._labels_resumo["method"].config(  text=cab.method   or "—")
        self._labels_resumo["thread"].config(  text=cab.thread   or "—")
        self._labels_resumo["timer"].config(
            text=f"{cab.timer_s:,.3f} s" if cab.timer_s else "—")
        self._labels_resumo["total_func"].config(
            text=str(len(self._funcoes)))

    def _aplicar_filtro(self) -> None:
        if not self._funcoes:
            return

        filtro  = self.entry_filtro.get().strip().lower()
        ord_key = ORDENACOES[self.combo_ord.current()][1]
        top_str = self.combo_top.get()

        # Filtra
        lista = self._funcoes
        if filtro:
            lista = [f for f in lista
                     if filtro in f.nome.lower() or filtro in f.arquivo.lower()]

        # Ordena
        reverso = ord_key != "nome"
        lista = sorted(lista, key=lambda f: getattr(f, ord_key), reverse=reverso)

        # Limita top N
        if top_str != "Todos":
            lista = lista[:int(top_str)]

        self._funcoes_filtradas = lista
        self._preencher_tabela()

    def _preencher_tabela(self) -> None:
        self.tree.delete(*self.tree.get_children())

        timer = self._cabecalho.timer_s if self._cabecalho else 0
        total_f = sum(f.tempo_t for f in self._funcoes) or 1

        for i, f in enumerate(self._funcoes_filtradas, 1):
            pct = (f.tempo_t / timer * 100) if timer > 0 else 0

            if f.tempo_t >= 2.0:
                tag = "critico"
            elif f.tempo_t >= 0.5:
                tag = "alto"
            elif f.tempo_t >= 0.1:
                tag = "medio"
            else:
                tag = "baixo"

            self.tree.insert("", "end", tags=(tag,), values=(
                i,
                f.nome,
                f.arquivo,
                f.calls,
                f"{f.tempo_t:.3f}",
                f"{f.tempo_m:.3f}",
                f"{pct:.1f}%",
            ))

        total = len(self._funcoes_filtradas)
        total_todos = len(self._funcoes)
        self.lbl_contagem.config(
            text=f"Exibindo {total} de {total_todos} funcoes")

    def _ao_selecionar(self, event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self._funcoes_filtradas):
            return
        f = self._funcoes_filtradas[idx]
        self._preencher_detalhes(f)

    def _preencher_detalhes(self, f: FuncaoCall) -> None:
        timer = self._cabecalho.timer_s if self._cabecalho else 0
        pct   = (f.tempo_t / timer * 100) if timer > 0 else 0

        self._card_labels["d_funcao"].config( text=f.nome,               fg=FG_BLUE)
        self._card_labels["d_arquivo"].config(text=f.arquivo,            fg=FG)
        self._card_labels["d_calls"].config(  text=str(f.calls),         fg=FG_YELLOW)
        self._card_labels["d_tempo_t"].config(text=f"{f.tempo_t:.3f} s", fg=FG_RED if f.tempo_t >= 2 else FG_YELLOW if f.tempo_t >= 0.5 else FG_GREEN)
        self._card_labels["d_tempo_m"].config(text=f"{f.tempo_m:.3f} s", fg=FG)
        self._card_labels["d_pct"].config(    text=f"{pct:.2f}%",        fg=FG_ORANGE)

        # Callers
        self.tree_callers.delete(*self.tree_callers.get_children())
        callers = sorted(f.callers, key=lambda c: c.tempo_t, reverse=True)
        for i, c in enumerate(callers):
            tag = "par" if i % 2 == 0 else "impar"
            self.tree_callers.insert("", "end", tags=(tag,), values=(
                c.origem,
                c.arquivo,
                c.linha,
                c.calls,
                f"{c.tempo_t:.3f}",
                f"{c.tempo_m:.3f}",
            ))

    # ══════════════════════════════════════════════════════
    #  GRAFICO DE BARRAS
    # ══════════════════════════════════════════════════════

    def _desenhar_grafico(self) -> None:
        c = self.canvas_grafico
        c.delete("all")

        if not self._funcoes:
            c.create_text(10, 10, text="Carregue um arquivo para ver o grafico.",
                fill=FG_DIM, font=FONT_SM, anchor="nw")
            return

        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10 or H < 10:
            return

        top15 = sorted(self._funcoes, key=lambda f: f.tempo_t, reverse=True)[:15]
        if not top15:
            return

        max_t = top15[0].tempo_t or 1
        n     = len(top15)

        pad_esq  = 8
        pad_dir  = 70   # espaco para o valor
        pad_top  = 6
        pad_bot  = 6
        h_bar    = max(8, (H - pad_top - pad_bot) // n - 3)
        CORES    = [FG_RED, FG_ORANGE, FG_YELLOW, FG_GREEN, FG_BLUE, FG_PURPLE]

        for i, f in enumerate(top15):
            y0 = pad_top + i * (h_bar + 3)
            y1 = y0 + h_bar
            bar_w = int((f.tempo_t / max_t) * (W - pad_esq - pad_dir - 120))
            cor = CORES[i % len(CORES)]

            # Barra
            c.create_rectangle(pad_esq + 120, y0,
                                pad_esq + 120 + max(bar_w, 2), y1,
                                fill=cor, outline="")

            # Nome (truncado)
            nome_exib = f.nome if len(f.nome) <= 22 else f.nome[:20] + ".."
            c.create_text(pad_esq + 118, (y0 + y1) // 2,
                text=nome_exib, fill=FG, font=("Consolas", 7),
                anchor="e")

            # Valor
            c.create_text(pad_esq + 120 + bar_w + 4, (y0 + y1) // 2,
                text=f"{f.tempo_t:.3f}s",
                fill=cor, font=("Consolas", 7), anchor="w")

    # ══════════════════════════════════════════════════════
    #  EXPORTACAO
    # ══════════════════════════════════════════════════════

    def _dados_exportar(self) -> tuple[list[str], list[list]]:
        colunas = ["Rank", "Funcao", "Arquivo", "Chamadas",
                   "Tempo Total(s)", "Tempo Maximo(s)", "% do Total"]
        timer = self._cabecalho.timer_s if self._cabecalho else 0
        linhas = []
        for i, f in enumerate(self._funcoes_filtradas, 1):
            pct = f"{(f.tempo_t / timer * 100):.1f}%" if timer > 0 else "0.0%"
            linhas.append([
                i, f.nome, f.arquivo, f.calls,
                f"{f.tempo_t:.3f}", f"{f.tempo_m:.3f}", pct
            ])
        return colunas, linhas

    def _exportar_csv(self) -> None:
        if not self._funcoes_filtradas:
            messagebox.showwarning("Exportar", "Nenhum dado para exportar.")
            return
        colunas, linhas = self._dados_exportar()
        exportar_csv(colunas, linhas, "logprofiler.csv",
                     self.atualizar_rodape)

    def _exportar_xlsx(self) -> None:
        if not self._funcoes_filtradas:
            messagebox.showwarning("Exportar", "Nenhum dado para exportar.")
            return
        colunas, linhas = self._dados_exportar()
        exportar_xlsx(colunas, linhas, "logprofiler.xlsx",
                      "LogProfiler", self.atualizar_rodape)

    # ── Helpers ───────────────────────────────────────────

    def _limpar_filtro(self) -> None:
        self.entry_filtro.delete(0, "end")
        self._aplicar_filtro()
