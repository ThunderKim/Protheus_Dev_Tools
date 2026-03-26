"""
config.py
=========
Configurações globais, gerenciamento de perfis de conexão e
detecção de dependências opcionais.
"""

import os
import json

# ── Dependências opcionais ────────────────────────────────
try:
    import py7zr
    PY7ZR_DISPONIVEL = True
except ImportError:
    PY7ZR_DISPONIVEL = False

try:
    import openpyxl
    OPENPYXL_DISPONIVEL = True
except ImportError:
    OPENPYXL_DISPONIVEL = False

# ── Localização do arquivo de perfis ─────────────────────
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "protheus_connections.json",
)

# ── Valores padrão de conexão ────────────────────────────
CONFIG_PADRAO: dict = {
    "driver":   "ODBC Driver 17 for SQL Server",
    "server":   "",
    "database": "",
    "username": "protheus",
    "password": "",
    "empresa":  "T1",
}

# CONFIG ativo em memória — compartilhado por todos os módulos
CONFIG: dict = dict(CONFIG_PADRAO)


# ── Funções de persistência ───────────────────────────────

def carregar_conexoes() -> dict:
    """Lê o arquivo JSON e retorna dict {nome: {campos...}}."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def salvar_conexoes(conexoes: dict) -> None:
    """Persiste o dict de conexões no arquivo JSON."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(conexoes, f, indent=2, ensure_ascii=False)
