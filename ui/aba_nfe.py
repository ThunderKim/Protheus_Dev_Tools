"""
ui/aba_nfe.py
=============
Aba calculadora de Chave de Acesso NF-e / CT-e.
Algoritmo: Módulo 11 — padrão SEFAZ.
Sem dependência de banco ou config.
"""

import tkinter as tk
from tkinter import ttk, messagebox


# Tabela de UFs IBGE
UFS_IBGE = [
    ("11 — Rondônia",           "11"),
    ("12 — Acre",                "12"),
    ("13 — Amazonas",            "13"),
    ("14 — Roraima",             "14"),
    ("15 — Pará",               "15"),
    ("16 — Amapá",              "16"),
    ("17 — Tocantins",           "17"),
    ("21 — Maranhão",           "21"),
    ("22 — Piauí",              "22"),
    ("23 — Ceará",              "23"),
    ("24 — Rio Grande do Norte", "24"),
    ("25 — Paraíba",            "25"),
    ("26 — Pernambuco",          "26"),
    ("27 — Alagoas",             "27"),
    ("28 — Sergipe",             "28"),
    ("29 — Bahia",               "29"),
    ("31 — Minas Gerais",        "31"),
    ("32 — Espírito Santo",     "32"),
    ("33 — Rio de Janeiro",      "33"),
    ("35 — São Paulo",          "35"),
    ("41 — Paraná",             "41"),
    ("42 — Santa Catarina",      "42"),
    ("43 — Rio Grande do Sul",   "43"),
    ("50 — Mato Grosso do Sul",  "50"),
    ("51 — Mato Grosso",         "51"),
    ("52 — Goiás",              "52"),
    ("53 — Distrito Federal",    "53"),
]


class AbaNfe(tk.Frame):
    """Calculadora de Chave de Acesso NF-e / CT-e."""

    def __init__(self, notebook: ttk.Notebook, atualizar_rodape) -> None:
        super().__init__(notebook, bg="#004064")
        notebook.add(self, text="  🔑 Chave NF-e  ")

        self.atualizar_rodape = atualizar_rodape
        self._vars: dict[str, tk.StringVar] = {}

        self._construir()

    # ── Construção da UI ──────────────────────────────────

    def _construir(self) -> None:
        tk.Label(
            self, text="Gerador de Chave de Acesso NF-e / CT-e",
            bg="#004064", fg="#ffffff", font=("Consolas", 12, "bold"),
        ).pack(pady=(14, 2))

        tk.Label(
            self, text="Algoritmo: Módulo 11  |  Padrão SEFAZ",
            bg="#004064", fg="#ffffff", font=("Consolas", 8),
        ).pack(pady=(0, 10))

        frame_campos = tk.Frame(self, bg="#004064")
        frame_campos.pack(padx=30, pady=4, fill="x")

        # Combo UF
        linha_uf = tk.Frame(frame_campos, bg="#004064")
        linha_uf.pack(fill="x", pady=3)

        tk.Label(
            linha_uf, text="cUF — Estado (IBGE):",
            bg="#004064", fg="#ffffff",
            font=("Consolas", 9), width=30, anchor="w",
        ).pack(side="left")

        self._vars["nfe_cuf"] = tk.StringVar(value="35")

        combo_uf = ttk.Combobox(
            linha_uf,
            textvariable=self._vars["nfe_cuf"],
            values=[label for label, _ in UFS_IBGE],
            state="readonly", width=28, font=("Consolas", 9),
        )
        combo_uf.pack(side="left", padx=(0, 10))
        combo_uf.current([label for label, _ in UFS_IBGE].index("35 — São Paulo"))

        def ao_selecionar_uf(event):
            self._vars["nfe_cuf"].set(combo_uf.get().split(" ")[0])

        combo_uf.bind("<<ComboboxSelected>>", ao_selecionar_uf)

        tk.Label(
            linha_uf, text="Selecione o estado do emitente",
            bg="#004064", fg="#ffffff", font=("Consolas", 8),
        ).pack(side="left")

        # Campos texto
        campos = [
            ("Ano/Mês Emissão",   "nfe_aamm",   "2603",          6,  "AAMM  Ex: 2602 = fev/2026"),
            ("CNPJ do Emitente",  "nfe_cnpj",   "43718433000190", 16, "14 dígitos sem pontuação"),
            ("Modelo",            "nfe_modelo",  "57",             4,  "55=NF-e  57=CT-e  65=NFC-e"),
            ("Série",             "nfe_serie",   "633",            5,  "3 dígitos com zeros à esquerda"),
            ("Número da NF",      "nfe_numero",  "100000100",     10,  "9 dígitos com zeros à esquerda"),
            ("Tipo Emissão",      "nfe_tpemis",  "1",              3,  "1=Normal  6=Contingência SVC-AN"),
            ("Código Numérico",   "nfe_cnf",     "99999938",      10,  "8 dígitos (código de segurança)"),
        ]

        for label, nome, exemplo, larg, dica in campos:
            linha = tk.Frame(frame_campos, bg="#004064")
            linha.pack(fill="x", pady=3)

            tk.Label(
                linha, text=f"{label}:",
                bg="#004064", fg="#ffffff",
                font=("Consolas", 9), width=30, anchor="w",
            ).pack(side="left")

            var = tk.StringVar(value=exemplo)
            self._vars[nome] = var

            tk.Entry(
                linha, textvariable=var, width=larg,
                bg="#2a2a3e", fg="#e0e0f0",
                insertbackground="#ffffff",
                relief="flat", font=("Consolas", 10), bd=4,
            ).pack(side="left", padx=(0, 10))

            tk.Label(
                linha, text=dica,
                bg="#004064", fg="#ffffff", font=("Consolas", 8),
            ).pack(side="left")

        # Botão calcular
        tk.Button(
            self, text="  ⚡  CALCULAR CHAVE  ",
            bg="#7c3aed", fg="white",
            font=("Consolas", 11, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#6d28d9",
            command=self.calcular,
        ).pack(pady=14)

        # Resultado
        frame_result = tk.Frame(self, bg="#13131f")
        frame_result.pack(padx=30, pady=4, fill="x")

        tk.Label(
            frame_result, text="Chave de Acesso (44 dígitos):",
            bg="#13131f", fg="#a0a0c0", font=("Consolas", 9),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        frame_copia = tk.Frame(frame_result, bg="#13131f")
        frame_copia.pack(fill="x", padx=12, pady=(0, 6))

        self._resultado = tk.Entry(
            frame_copia,
            bg="#0d0d1a", fg="#4ade80",
            font=("Consolas", 14, "bold"),
            relief="flat", bd=8,
            state="readonly", readonlybackground="#0d0d1a",
        )
        self._resultado.pack(side="left", fill="x", expand=True)

        tk.Button(
            frame_copia, text="  📋 COPIAR  ",
            bg="#059669", fg="white",
            font=("Consolas", 9, "bold"),
            relief="flat", cursor="hand2",
            activebackground="#047857",
            command=self.copiar,
        ).pack(side="left", padx=(6, 0))

        tk.Label(
            frame_result, text="Detalhes do cálculo Módulo 11:",
            bg="#13131f", fg="#a0a0c0", font=("Consolas", 9),
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self._detalhe = tk.Text(
            frame_result,
            bg="#0d0d1a", fg="#a0a0c0",
            font=("Consolas", 8),
            height=6, relief="flat", bd=8, state="disabled",
        )
        self._detalhe.pack(fill="x", padx=12, pady=(0, 12))

    # ── Lógica ────────────────────────────────────────────

    def calcular(self) -> None:
        """Executa o cálculo Módulo 11 e exibe a chave."""
        try:
            cuf    = self._vars["nfe_cuf"].get().strip().zfill(2)
            aamm   = self._vars["nfe_aamm"].get().strip().zfill(4)
            cnpj   = (
                self._vars["nfe_cnpj"].get().strip()
                .replace(".", "").replace("/", "").replace("-", "")
                .zfill(14)
            )
            modelo = self._vars["nfe_modelo"].get().strip().zfill(2)
            serie  = self._vars["nfe_serie"].get().strip().zfill(3)
            numero = self._vars["nfe_numero"].get().strip().zfill(9)
            tpemis = self._vars["nfe_tpemis"].get().strip().zfill(1)
            cnf    = self._vars["nfe_cnf"].get().strip().zfill(8)

            chave43 = cuf + aamm + cnpj + modelo + serie + numero + tpemis + cnf

            pesos = [2, 3, 4, 5, 6, 7, 8, 9]
            soma = sum(
                d * pesos[i % len(pesos)]
                for i, d in enumerate(reversed([int(c) for c in chave43]))
            )
            resto = soma % 11
            dv = 0 if resto in (0, 1) else 11 - resto
            chave_final = chave43 + str(dv)

            # Exibe resultado
            self._resultado.config(state="normal")
            self._resultado.delete(0, "end")
            self._resultado.insert(0, chave_final)
            self._resultado.config(state="readonly")

            # Detalhes
            dv_exp = "(resto 0 ou 1 → DV=0)" if resto in (0, 1) else f"(11 - {resto} = {dv})"
            detalhe = (
                f"Composição : {cuf} | {aamm} | {cnpj} | {modelo} | {serie} | {numero} | {tpemis} | {cnf}\n"
                f"43 dígitos : {chave43}\n"
                f"Pesos      : 2,3,4,5,6,7,8,9 (cíclico da direita p/ esquerda)\n"
                f"Soma       : {soma}\n"
                f"Resto (÷11): {resto}\n"
                f"DV         : {dv}  {dv_exp}\n"
                f"Chave Final: {chave_final}"
            )
            self._detalhe.config(state="normal")
            self._detalhe.delete("1.0", "end")
            self._detalhe.insert("1.0", detalhe)
            self._detalhe.config(state="disabled")

            # Copia automaticamente
            self.clipboard_clear()
            self.clipboard_append(chave_final)
            self.atualizar_rodape(f"✔  Chave copiada: {chave_final}")

        except ValueError:
            messagebox.showerror("Erro", "Todos os campos devem conter apenas números!")
        except Exception as e:
            messagebox.showerror("Erro inesperado", str(e))

    def copiar(self) -> None:
        chave = self._resultado.get()
        if chave:
            self.clipboard_clear()
            self.clipboard_append(chave)
            self.atualizar_rodape(f"✔  Chave copiada: {chave}")
        else:
            messagebox.showwarning("Atenção", "Calcule a chave antes de copiar!")
