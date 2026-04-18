"""
ui/aba_appserver_ini.py
=======================
Aba de edicao do arquivo appserver.ini do Protheus.

Comportamento:
  - Usuario informa o caminho do arquivo via dialogo ou campo de texto
  - O app le o .ini ignorando linhas comentadas com ";" e linhas vazias
  - Monta secoes dobre/expanda com um campo editavel por chave
  - Alteracoes sao marcadas em amarelo
  - Botao SALVAR reescreve o arquivo preservando:
      * todos os comentarios originais
      * linhas em branco
      * ordem exata das secoes e chaves
      * apenas o valor apos o "=" e alterado
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass, field


# ── Paleta ────────────────────────────────────────────────
BG        = "#0d0d1a"
BG_PANEL  = "#13131f"
BG_SECAO  = "#0a1929"
BG_ROW_A  = "#13131f"
BG_ROW_B  = "#1a1a2e"
BG_ENTRY  = "#050515"
FG        = "#e0e0f0"
FG_DIM    = "#6b6b8a"
FG_SEC    = "#4ade80"
FG_KEY    = "#60a5fa"
FG_VAL    = "#e0e0f0"
FG_MOD    = "#fbbf24"
FG_RED    = "#f87171"
ACCENT    = "#7c3aed"
FONT      = ("Consolas", 9)
FONT_BOLD = ("Consolas", 9, "bold")
FONT_SEC  = ("Consolas", 10, "bold")
FONT_SM   = ("Consolas", 8)
FONT_ENTRY= ("Consolas", 9)


# ══════════════════════════════════════════════════════════
#  MODELO DE DADOS
# ══════════════════════════════════════════════════════════

@dataclass
class LinhaIni:
    """Representa uma linha do arquivo .ini com seus metadados."""
    numero:  int          # indice 0-based no arquivo
    raw:     str          # texto original sem \n
    tipo:    str          # "secao" | "chave" | "ignorada"
    secao:   str  = ""    # nome da secao (so para tipo=="secao")
    chave:   str  = ""    # nome da chave (so para tipo=="chave")
    valor:   str  = ""    # valor original apos o "="


def _parsear(raw: str) -> LinhaIni:
    """Classifica uma linha do .ini."""
    s = raw.strip()

    if not s or s.startswith(";"):
        return LinhaIni(numero=0, raw=raw, tipo="ignorada")

    if s.startswith("[") and s.endswith("]"):
        return LinhaIni(numero=0, raw=raw, tipo="secao",
                        secao=s[1:-1].strip())

    if "=" in s:
        idx   = s.index("=")
        chave = s[:idx].strip()
        valor = s[idx + 1:]          # preserva espacos/conteudo original
        return LinhaIni(numero=0, raw=raw, tipo="chave",
                        chave=chave, valor=valor)

    return LinhaIni(numero=0, raw=raw, tipo="ignorada")


def ler_ini(caminho: str) -> list[LinhaIni]:
    """Le e retorna todas as linhas classificadas."""
    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        linhas_raw = f.read().splitlines()

    resultado = []
    for i, raw in enumerate(linhas_raw):
        ln = _parsear(raw)
        ln.numero = i
        resultado.append(ln)
    return resultado


def salvar_ini(caminho: str, linhas: list[LinhaIni],
               novos_valores: dict[int, str]) -> None:
    """
    Reescreve o arquivo aplicando os novos valores.
    novos_valores: {numero_da_linha: novo_valor_string}
    Todas as demais linhas (comentarios, secoes, vazias) sao
    escritas sem qualquer alteracao.
    """
    saida = []
    for ln in linhas:
        if ln.tipo == "chave" and ln.numero in novos_valores:
            novo = novos_valores[ln.numero]
            saida.append(f"{ln.chave}={novo}")
        else:
            saida.append(ln.raw)

    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(saida))


# ══════════════════════════════════════════════════════════
#  ABA PRINCIPAL
# ══════════════════════════════════════════════════════════

class AbaAppserverIni(tk.Frame):
    """Aba de leitura e edicao do appserver.ini."""

    def __init__(self, notebook: ttk.Notebook, atualizar_rodape) -> None:
        super().__init__(notebook, bg=BG)
        notebook.add(self, text="  ⚙ AppServer.ini  ")

        self.atualizar_rodape  = atualizar_rodape
        self._linhas:          list[LinhaIni]         = []
        self._vars:            dict[int, tk.StringVar] = {}  # linha → var
        self._originais:       dict[int, str]          = {}  # linha → valor orig
        self._modificados:     set[int]                = set()
        self._arquivo:         str                     = ""

        # Mapa de widgets por secao para filtro e expand/collapse
        self._sec_frames:   dict[str, tk.Frame] = {}   # nome → frame de chaves
        self._sec_visible:  dict[str, bool]     = {}   # nome → expandido?
        self._sec_btns:     dict[str, tk.Button]= {}   # nome → botao toggle

        self._construir_ui()

    # ══════════════════════════════════════════════════════
    #  CONSTRUÇÃO DA UI ESTÁTICA
    # ══════════════════════════════════════════════════════

    def _construir_ui(self) -> None:

        # ── Toolbar superior ──────────────────────────────
        bar = tk.Frame(self, bg=BG_PANEL)
        bar.pack(fill="x", padx=6, pady=(6, 0))

        tk.Button(bar, text="  📂  Abrir  ",
            bg=ACCENT, fg="white", font=FONT_BOLD,
            relief="flat", cursor="hand2", activebackground="#6d28d9",
            command=self._dialogo_abrir,
        ).pack(side="left", padx=(6, 4), pady=6)

        self._entry_caminho = tk.Entry(bar,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            relief="flat", font=FONT, bd=4, width=52)
        self._entry_caminho.pack(side="left", pady=6)
        self._entry_caminho.bind("<Return>", lambda e: self._carregar_do_campo())

        tk.Button(bar, text="Carregar",
            bg=BG_PANEL, fg=FG, font=FONT,
            relief="flat", cursor="hand2", activebackground=BG_ROW_A,
            command=self._carregar_do_campo,
        ).pack(side="left", padx=(4, 16), pady=6)

        # Lado direito da toolbar
        self._btn_salvar = tk.Button(bar, text="  💾  SALVAR  ",
            bg="#059669", fg="white", font=FONT_BOLD,
            relief="flat", cursor="hand2", activebackground="#047857",
            state="disabled", command=self._salvar,
        )
        self._btn_salvar.pack(side="right", padx=(4, 6), pady=6)

        tk.Button(bar, text="⊞ Expandir tudo",
            bg=BG_PANEL, fg=FG_DIM, font=FONT_SM,
            relief="flat", cursor="hand2",
            command=lambda: self._toggle_todos(True),
        ).pack(side="right", padx=2, pady=6)

        tk.Button(bar, text="⊟ Recolher tudo",
            bg=BG_PANEL, fg=FG_DIM, font=FONT_SM,
            relief="flat", cursor="hand2",
            command=lambda: self._toggle_todos(False),
        ).pack(side="right", padx=2, pady=6)

        tk.Label(bar, text="🔍 Filtrar seção:",
            bg=BG_PANEL, fg=FG_DIM, font=FONT_SM,
        ).pack(side="right", padx=(0, 2), pady=6)

        self._entry_filtro = tk.Entry(bar,
            bg=BG_ENTRY, fg=FG, insertbackground=FG,
            relief="flat", font=FONT, bd=4, width=16)
        self._entry_filtro.pack(side="right", pady=6)
        self._entry_filtro.bind("<KeyRelease>", lambda e: self._filtrar())

        # ── Barra de info ─────────────────────────────────
        info = tk.Frame(self, bg=BG_SECAO)
        info.pack(fill="x", padx=6, pady=(3, 0))

        self._lbl_arquivo = tk.Label(info,
            text="Nenhum arquivo carregado",
            bg=BG_SECAO, fg=FG_DIM, font=FONT_SM)
        self._lbl_arquivo.pack(side="left", padx=8, pady=3)

        self._lbl_mod = tk.Label(info, text="",
            bg=BG_SECAO, fg=FG_MOD, font=FONT_SM)
        self._lbl_mod.pack(side="right", padx=8, pady=3)

        self._lbl_stats = tk.Label(info, text="",
            bg=BG_SECAO, fg=FG_DIM, font=FONT_SM)
        self._lbl_stats.pack(side="right", padx=4, pady=3)

        # ── Área scrollável com as seções ─────────────────
        cont = tk.Frame(self, bg=BG)
        cont.pack(fill="both", expand=True, padx=6, pady=6)

        self._canvas = tk.Canvas(cont, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(cont, orient="vertical",
            command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=BG)
        self._win_id = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(
                self._win_id, width=e.width))

        # Scroll com roda do mouse
        for w in (self._canvas, self._inner):
            w.bind("<MouseWheel>", self._scroll)
            w.bind("<Button-4>",   self._scroll)
            w.bind("<Button-5>",   self._scroll)

    def _scroll(self, event) -> None:
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # ══════════════════════════════════════════════════════
    #  CARREGAMENTO
    # ══════════════════════════════════════════════════════

    def _dialogo_abrir(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecionar appserver.ini",
            filetypes=[("INI files", "*.ini"), ("Todos", "*.*")])
        if not caminho:
            return
        self._entry_caminho.delete(0, "end")
        self._entry_caminho.insert(0, caminho)
        self._carregar(caminho)

    def _carregar_do_campo(self) -> None:
        caminho = self._entry_caminho.get().strip()
        if not caminho:
            messagebox.showwarning("Atenção", "Informe o caminho do arquivo.")
            return
        self._carregar(caminho)

    def _carregar(self, caminho: str) -> None:
        if not os.path.exists(caminho):
            messagebox.showerror("Arquivo não encontrado",
                f"O arquivo não foi encontrado:\n{caminho}")
            return
        try:
            self._linhas    = ler_ini(caminho)
            self._arquivo   = caminho
            self._vars      = {}
            self._originais = {}
            self._modificados.clear()
            self._sec_frames  = {}
            self._sec_visible = {}
            self._sec_btns    = {}

            self._montar_editor()
            self._atualizar_info()
            self._btn_salvar.config(state="normal")
            self.atualizar_rodape(
                f"Carregado: {os.path.basename(caminho)}")
        except Exception as e:
            messagebox.showerror("Erro ao carregar arquivo", str(e))

    # ══════════════════════════════════════════════════════
    #  MONTAGEM DO EDITOR
    # ══════════════════════════════════════════════════════

    def _montar_editor(self) -> None:
        # Limpa o conteúdo anterior
        for w in self._inner.winfo_children():
            w.destroy()

        secao_atual = ""
        frame_secao  = None   # frame de chaves da seção atual
        row_count    = 0      # contador de linhas dentro da seção (para zebra)

        for ln in self._linhas:
            if ln.tipo == "secao":
                secao_atual = ln.secao
                frame_secao, row_count = self._criar_secao(ln.secao)

            elif ln.tipo == "chave" and frame_secao is not None:
                bg = BG_ROW_A if row_count % 2 == 0 else BG_ROW_B
                self._criar_linha_chave(frame_secao, ln, bg)
                row_count += 1

        # Seção "SEM SEÇÃO" — chaves antes do primeiro [...]
        # (tratadas acima se frame_secao é None, ignoramos por ora)

        # Scroll ao topo
        self._canvas.yview_moveto(0)

    def _criar_secao(self, nome: str) -> tuple[tk.Frame, int]:
        """Cria o cabeçalho expansível de uma seção e retorna o frame de chaves."""

        # Cabeçalho clicável
        header = tk.Frame(self._inner, bg=BG_SECAO, cursor="hand2")
        header.pack(fill="x", pady=(6, 0), padx=0)

        btn_toggle = tk.Button(header, text="▼",
            bg=BG_SECAO, fg=FG_SEC, font=FONT_SEC,
            relief="flat", cursor="hand2", bd=0,
            activebackground=BG_SECAO, activeforeground=FG_SEC)
        btn_toggle.pack(side="left", padx=(8, 4), pady=4)

        tk.Label(header, text=f"[{nome}]",
            bg=BG_SECAO, fg=FG_SEC, font=FONT_SEC,
        ).pack(side="left", pady=4)

        # Frame de chaves (inicialmente visível)
        frame_chaves = tk.Frame(self._inner, bg=BG_ROW_A)
        frame_chaves.pack(fill="x", padx=0)

        self._sec_frames[nome]  = frame_chaves
        self._sec_visible[nome] = True
        self._sec_btns[nome]    = btn_toggle

        # Bind no header inteiro e no botão
        def _toggle(event=None, n=nome):
            self._toggle_secao(n)

        header.bind("<Button-1>", _toggle)
        btn_toggle.config(command=lambda n=nome: self._toggle_secao(n))

        return frame_chaves, 0

    def _criar_linha_chave(self, parent: tk.Frame,
                            ln: LinhaIni, bg: str) -> None:
        """Cria uma linha com label da chave + entry do valor."""
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", padx=0)

        # Label com nome da chave (largura fixa para alinhar)
        tk.Label(row, text=ln.chave,
            bg=bg, fg=FG_KEY, font=FONT,
            width=28, anchor="w",
        ).pack(side="left", padx=(12, 4), pady=3)

        tk.Label(row, text="=",
            bg=bg, fg=FG_DIM, font=FONT,
        ).pack(side="left", padx=(0, 6))

        # StringVar ligada ao Entry
        var = tk.StringVar(value=ln.valor)
        self._vars[ln.numero]      = var
        self._originais[ln.numero] = ln.valor

        entry = tk.Entry(row, textvariable=var,
            bg=BG_ENTRY, fg=FG_VAL,
            insertbackground=FG_VAL,
            relief="flat", font=FONT_ENTRY, bd=3,
            selectbackground=ACCENT,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=3)

        # Indicador de modificado (bolinha amarela)
        lbl_ind = tk.Label(row, text="",
            bg=bg, fg=FG_MOD, font=FONT_BOLD, width=2)
        lbl_ind.pack(side="right", padx=(0, 6))

        # Detecta mudança em tempo real
        def _ao_mudar(*args, n=ln.numero, e=entry, lbl=lbl_ind, b=bg):
            novo     = self._vars[n].get()
            original = self._originais[n]
            if novo != original:
                self._modificados.add(n)
                e.config(fg=FG_MOD)
                lbl.config(text="●")
            else:
                self._modificados.discard(n)
                e.config(fg=FG_VAL)
                lbl.config(text="")
            self._atualizar_contador_mod()

        var.trace_add("write", _ao_mudar)

        # Propaga scroll do mouse pelo entry para o canvas
        entry.bind("<MouseWheel>", self._scroll)
        entry.bind("<Button-4>",   self._scroll)
        entry.bind("<Button-5>",   self._scroll)
        row.bind("<MouseWheel>",   self._scroll)
        row.bind("<Button-4>",     self._scroll)
        row.bind("<Button-5>",     self._scroll)

    # ══════════════════════════════════════════════════════
    #  EXPAND / COLLAPSE
    # ══════════════════════════════════════════════════════

    def _toggle_secao(self, nome: str) -> None:
        visivel = self._sec_visible.get(nome, True)
        frame   = self._sec_frames.get(nome)
        btn     = self._sec_btns.get(nome)
        if not frame:
            return
        if visivel:
            frame.pack_forget()
            if btn:
                btn.config(text="▶")
            self._sec_visible[nome] = False
        else:
            frame.pack(fill="x", padx=0)
            if btn:
                btn.config(text="▼")
            self._sec_visible[nome] = True

    def _toggle_todos(self, expandir: bool) -> None:
        for nome in list(self._sec_frames.keys()):
            visivel = self._sec_visible.get(nome, True)
            if expandir and not visivel:
                self._toggle_secao(nome)
            elif not expandir and visivel:
                self._toggle_secao(nome)

    # ══════════════════════════════════════════════════════
    #  FILTRO DE SEÇÃO
    # ══════════════════════════════════════════════════════

    def _filtrar(self) -> None:
        """Mostra apenas seções cujo nome contém o texto do filtro."""
        termo = self._entry_filtro.get().strip().lower()

        # Percorre os frames de seção no widget inner
        # Os headers são frames empacotados antes dos frame_chaves
        for nome, frame_chaves in self._sec_frames.items():
            combina = not termo or termo in nome.lower()

            if combina:
                # Garante que o frame de chaves está visível se a seção estava expandida
                if self._sec_visible.get(nome, True):
                    if not frame_chaves.winfo_ismapped():
                        frame_chaves.pack(fill="x", padx=0)
            else:
                if frame_chaves.winfo_ismapped():
                    frame_chaves.pack_forget()

        # Mostra/esconde headers — mais fácil rastrear pelos filhos do inner
        # Os widgets do inner alternam: Frame(header), Frame(chaves), ...
        filhos = self._inner.winfo_children()
        i = 0
        while i < len(filhos):
            w = filhos[i]
            # Headers têm bg=BG_SECAO; tentamos identificar pelo bg
            if isinstance(w, tk.Frame) and w.cget("bg") == BG_SECAO:
                # Descobre o nome da seção pelo label filho
                nome_sec = ""
                for filho in w.winfo_children():
                    if isinstance(filho, tk.Label):
                        txt = filho.cget("text")
                        if txt.startswith("["):
                            nome_sec = txt[1:-1]
                            break
                combina = not termo or termo in nome_sec.lower()
                if combina:
                    if not w.winfo_ismapped():
                        w.pack(fill="x", pady=(6, 0), padx=0)
                else:
                    if w.winfo_ismapped():
                        w.pack_forget()
            i += 1

    # ══════════════════════════════════════════════════════
    #  SALVAR
    # ══════════════════════════════════════════════════════

    def _salvar(self) -> None:
        if not self._arquivo:
            return
        if not self._modificados:
            messagebox.showinfo("Sem alterações",
                "Nenhuma chave foi modificada.")
            return

        n = len(self._modificados)
        ok = messagebox.askyesno(
            "Confirmar salvamento",
            f"Salvar {n} alteração(ões) no arquivo?\n\n"
            f"{os.path.basename(self._arquivo)}")
        if not ok:
            return

        try:
            # Monta dict com os novos valores
            novos: dict[int, str] = {}
            for num in self._modificados:
                novos[num] = self._vars[num].get()

            salvar_ini(self._arquivo, self._linhas, novos)

            # Atualiza o modelo em memória para refletir os valores salvos
            for num, novo_val in novos.items():
                for ln in self._linhas:
                    if ln.numero == num and ln.tipo == "chave":
                        ln.valor         = novo_val
                        ln.raw           = f"{ln.chave}={novo_val}"
                        self._originais[num] = novo_val
                        break

            self._modificados.clear()

            # Reseta visuais dos entries
            for num, var in self._vars.items():
                # Força o trace a re-avaliar (sem mudanca real, apenas atualiza cor)
                var.set(var.get())

            self._atualizar_contador_mod()
            self.atualizar_rodape(
                f"✔  Arquivo salvo: {os.path.basename(self._arquivo)}")
            messagebox.showinfo("Salvo", "✔ Arquivo salvo com sucesso!")

        except PermissionError:
            messagebox.showerror("Erro de Permissão",
                "Sem permissão para gravar o arquivo.\n"
                "Execute o programa como Administrador ou verifique\n"
                "as permissões da pasta.")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    # ══════════════════════════════════════════════════════
    #  INFO / STATS
    # ══════════════════════════════════════════════════════

    def _atualizar_info(self) -> None:
        nome    = os.path.basename(self._arquivo)
        n_sec   = len(self._sec_frames)
        n_chaves= sum(1 for ln in self._linhas if ln.tipo == "chave")
        n_ign   = sum(1 for ln in self._linhas if ln.tipo == "ignorada")

        self._lbl_arquivo.config(
            text=self._arquivo, fg=FG)
        self._lbl_stats.config(
            text=f"{n_sec} seções  |  {n_chaves} chaves  |  {n_ign} linhas ignoradas")
        self._atualizar_contador_mod()

    def _atualizar_contador_mod(self) -> None:
        n = len(self._modificados)
        if n:
            self._lbl_mod.config(
                text=f"⬤ {n} alteração(ões) não salva(s)", fg=FG_MOD)
        else:
            self._lbl_mod.config(text="", fg=FG_MOD)
