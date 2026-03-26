"""
ui/ajuda.py
===========
Janela modal de ajuda com instruções de configuração.
"""

import tkinter as tk
from tkinter import ttk


# Conteúdo da ajuda: lista de (titulo_aba, [(titulo_secao, texto), ...])
CONTEUDO_AJUDA = [
    ("🔐 Modo de Autenticação", [
        ("O que é?",
            "Por padrão o SQL Server aceita apenas Autenticação Windows.\n"
            "Para usar usuário e senha SQL é necessário habilitar o Modo Misto."),
        ("Passo a passo no SSMS",
            "1. Abra o SQL Server Management Studio (SSMS)\n"
            "2. Clique com botão DIREITO no servidor (raiz da árvore)\n"
            "3. Clique em 'Propriedades'\n"
            "4. Acesse a aba 'Segurança'\n"
            "5. Em 'Autenticação do Servidor' marque:\n"
            "       ● SQL Server e Autenticação do Windows\n"
            "6. Clique em OK\n"
            "7. REINICIE o serviço do SQL Server!\n"
            "   (sem reiniciar a mudança não tem efeito)"),
        ("Reiniciar o serviço",
            "Opção 1 — Pelo SSMS:\n"
            "   Clique direito no servidor > Reiniciar\n\n"
            "Opção 2 — Pelo Windows:\n"
            "   Painel de Controle > Ferramentas Administrativas\n"
            "   > Serviços > SQL Server (MSSQLSERVER) > Reiniciar"),
    ]),
    ("👤 Criar Usuário SQL", [
        ("Criar login com acesso total (sysadmin)",
            "-- Execute no SSMS:\n\n"
            "CREATE LOGIN protheus\n"
            "    WITH PASSWORD     = 'protheus$123',\n"
            "         CHECK_POLICY = OFF,\n"
            "         CHECK_EXPIRATION = OFF\n\n"
            "ALTER SERVER ROLE sysadmin\n"
            "    ADD MEMBER protheus\n\n"
            "Obs: sysadmin dá acesso total (equivale ao 'sa').\n"
            "Use apenas em ambientes de desenvolvimento/teste."),
        ("Criar login somente leitura (recomendado)",
            "-- Cria o login:\n"
            "CREATE LOGIN protheus\n"
            "    WITH PASSWORD = 'protheus$123',\n"
            "         CHECK_POLICY = OFF,\n"
            "         CHECK_EXPIRATION = OFF\n\n"
            "-- Repita para cada banco Protheus:\n"
            "USE nome_do_banco\n"
            "GO\n"
            "CREATE USER protheus FOR LOGIN protheus\n"
            "ALTER ROLE db_datareader ADD MEMBER protheus"),
        ("Habilitar / redefinir login",
            "-- Habilitar login desabilitado:\n"
            "ALTER LOGIN protheus ENABLE\n\n"
            "-- Redefinir senha:\n"
            "ALTER LOGIN protheus\n"
            "    WITH PASSWORD = 'nova_senha',\n"
            "         CHECK_POLICY = OFF"),
    ]),
    ("🔌 Driver ODBC", [
        ("Verificar drivers instalados",
            "Abra o Prompt de Comando e execute:\n\n"
            "   odbcad32\n\n"
            "Na janela, clique na aba 'Drivers' e\n"
            "verifique quais estão disponíveis."),
        ("Drivers compatíveis",
            "Use o nome EXATO no campo de Driver:\n\n"
            '   "SQL Server"                      (já vem no Windows)\n'
            '   "ODBC Driver 17 for SQL Server"   (recomendado)\n'
            '   "ODBC Driver 18 for SQL Server"   (mais recente)'),
        ("Baixar o driver",
            "Se não tiver o driver, baixe em:\n"
            "   https://learn.microsoft.com/sql/connect/odbc/\n"
            "   download-odbc-driver-for-sql-server\n\n"
            "Após instalar, reinicie a aplicação."),
        ("Erro de certificado SSL",
            "Se aparecer erro de certificado SSL, verifique\n"
            "se a string de conexão contém:\n\n"
            '   "TrustServerCertificate=yes;"\n\n'
            "Essa linha já está incluída no código da ferramenta."),
    ]),
    ("🗂 Empresa e Sufixo", [
        ("Como funciona o sufixo das tabelas",
            "No Protheus, o nome físico da tabela no banco é:\n\n"
            "   NOME_TABELA + CODIGO_EMPRESA + '0'\n\n"
            "Exemplos:\n"
            "   Empresa '01'  ->  SX2010, SX3010, SX6010 ...\n"
            "   Empresa 'T1'  ->  SX2T10, SX3T10, SX6T10 ...\n"
            "   Empresa '99'  ->  SX2990, SX3990, SX6990 ..."),
        ("Como descobrir o código da empresa",
            "Opção 1 — Pelo SSMS:\n"
            "   Execute: SELECT TOP 10 * FROM SYS_COMPANY\n"
            "   Veja a coluna M0_CODIGO\n\n"
            "Opção 2 — Pela aba SYS_COMPANY desta ferramenta:\n"
            "   Conecte e acesse a aba SYS_COMPANY - Filiais\n"
            "   O campo 'Código' mostra o código da empresa"),
        ("Erro: nome de objeto inválido",
            "Se aparecer erro 'Nome de objeto SX2010 inválido',\n"
            "o sufixo está errado.\n\n"
            "Verifique o campo EMPRESA na tela de conexão\n"
            "e corrija para o código certo da sua empresa."),
    ]),
    ("❌ Erros Comuns", [
        ("Erro 18456 — Falha de logon",
            "Causas mais comuns:\n"
            "   - Modo de autenticação apenas Windows\n"
            "   - Senha incorreta\n"
            "   - Login desabilitado\n\n"
            "Solução:\n"
            "   1. Habilite o Modo Misto (aba Modo de Autenticação)\n"
            "   2. Reinicie o serviço do SQL Server\n"
            "   3. Verifique usuário e senha"),
        ("Erro SSL — Cadeia de certificação",
            "Mensagem: 'A cadeia de certificação foi emitida\n"
            "por uma autoridade que nao e de confiança'\n\n"
            "Solução: Já resolvido no código com:\n"
            "   TrustServerCertificate=yes\n\n"
            "Se persistir, verifique o nome/IP do servidor."),
        ("Erro — Data source name not found",
            "O driver ODBC informado não está instalado.\n\n"
            "Solução:\n"
            "   1. Abra odbcad32 e veja os drivers disponíveis\n"
            "   2. Corrija o campo Driver na tela de conexão\n"
            "   3. Instale o driver correto (aba Driver ODBC)"),
        ("Erro — Cannot open server",
            "Não foi possível alcançar o servidor.\n\n"
            "Verifique:\n"
            "   - IP ou nome do servidor está correto\n"
            "   - Porta 1433 liberada no firewall\n"
            "   - Serviço SQL Server está rodando\n"
            "   - VPN ativa se o servidor for remoto"),
    ]),
]


def abrir_ajuda(parent: tk.Tk) -> None:
    """Abre a janela modal de ajuda."""
    win = tk.Toplevel(parent)
    win.title("Instruções de Configuração")
    win.geometry("800x640")
    win.configure(bg="#13131f")
    win.resizable(False, False)
    win.grab_set()
    win.focus_set()

    tk.Label(win,
        text="⚙  INSTRUÇÕES DE CONFIGURAÇÃO",
        bg="#13131f", fg="#f5f8fa", font=("Consolas", 13, "bold"),
    ).pack(pady=(16, 2))

    tk.Label(win,
        text="Protheus Dicionário Tool — Guia de configuração inicial",
        bg="#13131f", fg="#6b6b8a", font=("Consolas", 8),
    ).pack(pady=(0, 4))

    tk.Label(win,
        text="Autor: João Marcos Martins",
        bg="#13131f", fg="#6b6b8a", font=("Consolas", 8),
    ).pack(pady=(0, 10))

    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    for titulo_aba, secoes in CONTEUDO_AJUDA:
        frame_aba = tk.Frame(nb, bg="#1a1a2e")
        nb.add(frame_aba, text=f"  {titulo_aba}  ")

        canvas = tk.Canvas(frame_aba, bg="#1a1a2e", highlightthickness=0)
        scroll = ttk.Scrollbar(frame_aba, orient="vertical", command=canvas.yview)
        frame_scroll = tk.Frame(canvas, bg="#1a1a2e")

        frame_scroll.bind(
            "<Configure>",
            lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")),
        )
        canvas.create_window((0, 0), window=frame_scroll, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.bind(
            "<MouseWheel>",
            lambda e, c=canvas: c.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        for titulo_sec, texto in secoes:
            tk.Label(frame_scroll, text=titulo_sec,
                bg="#1a1a2e", fg="#a78bfa",
                font=("Consolas", 9, "bold"), anchor="w",
            ).pack(fill="x", padx=20, pady=(14, 2))

            tk.Frame(frame_scroll, bg="#2a2a4e", height=1).pack(fill="x", padx=20)

            tk.Label(frame_scroll, text=texto,
                bg="#1a1a2e", fg="#c0c0d8",
                font=("Consolas", 9),
                justify="left", anchor="w", wraplength=700,
            ).pack(fill="x", padx=28, pady=(6, 2))

    tk.Button(win, text="  FECHAR  ",
        bg="#004064", fg="white",
        font=("Consolas", 10, "bold"),
        relief="flat", cursor="hand2",
        activebackground="#006090",
        command=win.destroy,
    ).pack(pady=(0, 14))
