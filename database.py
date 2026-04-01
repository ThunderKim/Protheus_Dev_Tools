"""
database.py
===========
Camada de dados: conexão e consultas ao SQL Server via pyodbc.
Sem dependências de UI.

Thread-safety:
    Cada chamada a executar_consulta abre um cursor novo e fecha ao final.
    A Connection do pyodbc suporta múltiplos cursors sequenciais em uma
    mesma thread sem problemas. Para chamadas concorrentes de threads
    diferentes, o pyodbc pode se comportar de forma imprevisível com uma
    única Connection compartilhada, por isso cada consulta é protegida por
    um threading.Lock — garantindo execução serializada e segura.
"""

import threading
import pyodbc
from config import CONFIG


class BancoDados:
    """Responsável por conectar e consultar o SQL Server."""

    def __init__(self) -> None:
        self._conn_str: str = ""
        self._lock = threading.Lock()

    # ── Conexão ───────────────────────────────────────────

    def conectar(self) -> bool:
        """Valida a conexão e salva a string para uso posterior."""
        self._conn_str = (
            f"DRIVER={{{CONFIG['driver']}}};"
            f"SERVER={CONFIG['server']};"
            f"DATABASE={CONFIG['database']};"
            f"UID={CONFIG['username']};"
            f"PWD={CONFIG['password']};"
            "TrustServerCertificate=yes;"
        )
        # Abre uma conexão de teste para validar as credenciais
        conn = pyodbc.connect(self._conn_str, timeout=10)
        conn.close()
        return True

    def desconectar(self) -> None:
        """Limpa a string de conexão (conexões são abertas por demanda)."""
        self._conn_str = ""

    def _nova_conexao(self) -> pyodbc.Connection:
        """Abre uma nova conexão dedicada para a query atual."""
        return pyodbc.connect(self._conn_str, timeout=30)

    # ── Execução genérica ─────────────────────────────────

    def executar_consulta(
        self, sql: str, parametros: tuple = ()
    ) -> tuple[list[str], list]:
        """Executa *sql* e retorna (colunas, linhas).

        Abre uma conexão dedicada por chamada para evitar conflitos entre
        threads concorrentes.
        """
        conn = self._nova_conexao()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, parametros)
            colunas = [d[0] for d in cursor.description]
            linhas  = cursor.fetchall()
            cursor.close()
            return colunas, linhas
        finally:
            conn.close()


    # ── Sufixo dinâmico ───────────────────────────────────

    def _sufixo(self) -> str:
        """Retorna o sufixo físico da tabela: EMPRESA + '0'.

        Exemplos:
            empresa "01"  →  "010"  →  SX2010, SX3010 …
            empresa "T1"  →  "T10"  →  SX2T10, SX3T10 …
            empresa "99"  →  "990"  →  SX2990, SX3990 …
        """
        return CONFIG["empresa"] + "0"

    # ── Consultas do dicionário ───────────────────────────

    def consultar_sx6(self, filtro: str = "") -> tuple:
        """SX6 — Parâmetros do sistema."""
        tabela = f"SX6{self._sufixo()}"
        sql = f"""
            SELECT
                X6_CONTEUD  AS [Conteúdo],
                X6_VAR      AS [Parâmetro],
                X6_DESCRIC  AS [Descrição],
                X6_TIPO     AS [Tipo]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND X6_VAR LIKE ?
            ORDER BY X6_VAR
        """
        return self.executar_consulta(sql, (f"%{filtro}%",))

    def consultar_sx3(self, filtro: str = "") -> tuple:
        """SX3 — Campos do dicionário."""
        tabela = f"SX3{self._sufixo()}"
        sql = f"""
            SELECT
                X3_ARQUIVO  AS [Tabela],
                X3_CAMPO    AS [Campo],
                X3_DESCRIC  AS [Descrição],
                X3_TIPO     AS [Tipo],
                X3_TAMANHO  AS [Tamanho],
                X3_DECIMAL  AS [Decimal],
                X3_TITULO   AS [Título]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (X3_CAMPO LIKE ? OR X3_ARQUIVO LIKE ? OR X3_DESCRIC LIKE ?)
            ORDER BY X3_ARQUIVO, X3_CAMPO
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f, f))

    def consultar_sx2(self, filtro: str = "") -> tuple:
        """SX2 — Tabelas do sistema."""
        tabela = f"SX2{self._sufixo()}"
        sql = f"""
            SELECT
                X2_CHAVE    AS [Chave],
                X2_NOME     AS [Nome],
                X2_MODO     AS [Modo],
                X2_ROTINA   AS [Rotina],
                X2_UNICO    AS [Único]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (X2_CHAVE LIKE ? OR X2_NOME LIKE ?)
            ORDER BY X2_CHAVE
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f))

    def consultar_six(self, filtro: str = "") -> tuple:
        """SIX — Índices das tabelas."""
        tabela = f"SIX{self._sufixo()}"
        sql = f"""
            SELECT
                INDICE      AS [Tabela],
                ORDEM       AS [Ordem],
                CHAVE       AS [Chave],
                DESCRICAO   AS [Descrição],
                PROPRI      AS [Propriedade]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (INDICE LIKE ? OR CHAVE LIKE ?)
            ORDER BY INDICE, ORDEM
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f))

    def consultar_sx1(self, filtro: str = "") -> tuple:
        """SX1 — Perguntas dos relatórios."""
        tabela = f"SX1{self._sufixo()}"
        sql = f"""
            SELECT
                X1_GRUPO    AS [Grupo],
                X1_ORDEM    AS [Ordem],
                X1_PERGUNT  AS [Pergunta],
                X1_TIPO     AS [Tipo],
                X1_TAMANHO  AS [Tamanho],
                X1_GSC      AS [GSC],
                X1_HELP     AS [Help]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (X1_GRUPO LIKE ? OR X1_PERGUNT LIKE ?)
            ORDER BY X1_GRUPO, X1_ORDEM
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f))

    def consultar_sx5(self, filtro: str = "") -> tuple:
        """SX5 — Tabelas genéricas."""
        tabela = f"SX5{self._sufixo()}"
        sql = f"""
            SELECT
                X5_TABELA   AS [Tabela],
                X5_CHAVE    AS [Chave],
                X5_DESCRI   AS [Descrição]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (X5_TABELA LIKE ? OR X5_CHAVE LIKE ? OR X5_DESCRI LIKE ?)
            ORDER BY X5_TABELA, X5_CHAVE
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f, f))

    def consultar_sx7(self, filtro: str = "") -> tuple:
        """SX7 — Gatilhos do dicionário de dados."""
        tabela = f"SX7{self._sufixo()}"
        sql = f"""
            SELECT
                X7_CAMPO    AS [Campo Origem],
                X7_SEQUENC  AS [Sequência],
                X7_REGRA    AS [Regra],
                X7_CDOMIN   AS [Campo Retorno],
                X7_TIPO     AS [Fase],
                X7_SEEK     AS [Condição],
                X7_ALIAS    AS [Alias],
                X7_ORDEM    AS [Chave Busca],
                X7_CHAVE    AS [Chave],
                X7_CONDIC   AS [Condição Extra],
                X7_PROPRI   AS [Propriedade]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (X7_CAMPO LIKE ? OR X7_CDOMIN LIKE ? OR X7_ALIAS LIKE ?)
            ORDER BY X7_CAMPO, X7_SEQUENC
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f, f))

    def consultar_sxb(self, filtro: str = "") -> tuple:
        """SXB — Consultas padrão (F3)."""
        tabela = f"SXB{self._sufixo()}"
        sql = f"""
            SELECT
                XB_ALIAS    AS [Alias],
                XB_TIPO     AS [Tipo],
                XB_SEQ      AS [Sequência],
                XB_COLUNA   AS [Coluna],
                XB_DESCRI   AS [Descrição],
                XB_CONTEM   AS [Conteúdo]
            FROM {tabela}
            WHERE D_E_L_E_T_ = ' '
              AND (XB_ALIAS LIKE ? OR XB_DESCRI LIKE ?)
            ORDER BY XB_ALIAS, XB_TIPO, XB_SEQ
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f))

    def consultar_sql_livre(self, sql: str) -> tuple:
        """Executa um SQL livre informado pelo usuário."""
        return self.executar_consulta(sql)

    def consultar_sys_company(self, filtro: str = "") -> tuple:
        """SYS_COMPANY — Dados das filiais."""
        sql = """
            SELECT
                M0_CODIGO   AS [Código],
                M0_CODFIL   AS [Filial],
                M0_NOME     AS [Nome],
                M0_CGC      AS [CNPJ],
                M0_INSC     AS [INSCR EST],
                M0_ENDENT   AS [Endereço],
                M0_CIDENT   AS [Cidade],
                M0_CEPENT   AS [CEP],
                M0_CODMUN   AS [Cód Mun],
                M0_ESTCOB   AS [Estado]
            FROM SYS_COMPANY
            WHERE D_E_L_E_T_ = ' '
              AND (M0_CODFIL LIKE ? OR M0_NOME LIKE ? OR M0_CGC LIKE ?)
            ORDER BY M0_CODIGO, M0_CODFIL
        """
        f = f"%{filtro}%"
        return self.executar_consulta(sql, (f, f, f))
