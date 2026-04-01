# Protheus Dicionário Tool

Ferramenta desktop para auxiliar desenvolvedores **TOTVS Protheus** no dia a dia.
Interface gráfica em Python + Tkinter, conexão direta ao SQL Server via ODBC.

---

## Funcionalidades

| Aba | Descrição |
|-----|-----------|
| **SX6 — Parâmetros** | Consulta parâmetros do sistema (MV_%) |
| **SX3 — Campos** | Consulta campos do dicionário de dados |
| **SX2 — Tabelas** | Consulta tabelas do sistema |
| **SIX — Índices** | Consulta índices das tabelas |
| **SX1 — Perguntas** | Consulta perguntas dos relatórios |
| **SX5 — Tab. Genéricas** | Consulta tabelas genéricas |
| **SX7 — Gatilhos** | Consulta gatilhos do dicionário |
| **SXB — Consultas F3** | Consulta consultas padrão (F3) |
| **SYS_COMPANY** | Consulta filiais cadastradas |
| **SQL Livre** | Editor SQL para consultas livres no banco |
| **Chave NF-e** | Calculadora de chave de acesso NF-e/CT-e (Módulo 11) |
| **Restaurar Base** | Restauração automatizada de banco SQL e pasta Protheus_Data |
| **API Fake** | Servidor HTTP local para simular respostas de API |
| **LogProfiler** | Análise de arquivos FWLogProfiler de performance |

---

## Pré-requisitos

- Python 3.11 ou superior
- [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/pt-br/sql/connect/odbc/download-odbc-driver-for-sql-server) instalado no Windows

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/protheus-dicionario-tool.git
cd protheus-dicionario-tool

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute
python main.py
```

### Dependências

```
pyodbc      # conexão SQL Server (obrigatório)
openpyxl    # exportação XLSX   (opcional — habilita botão XLSX)
py7zr       # extração de .7z   (opcional — necessário para backups .7z)
```

---

## Estrutura do Projeto

```
protheus_tool/
│
├── main.py                    # Ponto de entrada
├── config.py                  # Configurações e gerenciamento de perfis JSON
├── database.py                # Camada de dados — BancoDados (pyodbc)
├── historico.py               # Histórico de consultas por aba
├── requirements.txt
├── README.md
│
└── ui/
    ├── app.py                 # Janela principal — orquestra todas as abas
    ├── aba_consulta.py        # Widget reutilizável para abas SX2/SX3/SX6...
    ├── aba_sql_livre.py       # Aba SQL Livre (editor + Treeview + exportação)
    ├── aba_nfe.py             # Calculadora de Chave NF-e / CT-e
    ├── aba_restauracao.py     # Restauração de banco SQL e Protheus_Data
    ├── aba_api_fake.py        # Servidor HTTP fake configurável
    ├── aba_log_profiler.py    # Análise de arquivos FWLogProfiler
    ├── ajuda.py               # Janela modal de ajuda / documentação
    └── exportacao.py          # Funções CSV / XLSX reutilizáveis
```

---

## Configuração de Conexão

Na primeira execução, preencha os campos no painel superior:

| Campo | Exemplo | Descrição |
|-------|---------|-----------|
| Servidor | `192.168.1.10` ou `SERVIDOR\INSTANCIA` | IP ou nome do SQL Server |
| Banco | `P12PRODUCAO` | Nome do banco de dados |
| Usuário | `protheus` | Login SQL Server |
| Senha | `****` | Senha do login |
| Empresa | `T1` | Código da empresa no Protheus |

Clique em **💾 Salvar** para criar um perfil nomeado. As conexões são salvas em `protheus_connections.json` na pasta do projeto — adicione este arquivo ao `.gitignore` para não versionar credenciais.

> **Dica:** Para usar autenticação SQL (usuário/senha), o SQL Server precisa estar em **Modo Misto**. Veja o guia completo no botão **❓ AJUDA** dentro da ferramenta.

---

## Aba SQL Livre

Execute qualquer `SELECT` diretamente no banco conectado.

- Atalho **F5** para executar
- Resultado em tabela com exportação CSV / XLSX
- Útil para consultas ad-hoc nas tabelas do Protheus

---

## Calculadora de Chave NF-e

Gera a chave de acesso de 44 dígitos para NF-e, CT-e e NFC-e.

- Algoritmo **Módulo 11** conforme padrão SEFAZ
- Seletor de UF com código IBGE
- Exibe decomposição completa do cálculo
- Copia a chave automaticamente para a área de transferência

---

## Restauração de Base de Testes

Automatiza a restauração completa do ambiente de testes:

**Banco SQL Server:**
- Baixa ZIP do servidor (Artifactory, Nexus etc.) **ou** usa arquivo local (`.bak`, `.zip`, `.7z`)
- Executa `RESTORE DATABASE` com `WITH MOVE` automático (detecta os caminhos corretos via `RESTORE FILELISTONLY`)
- Lida com bancos em estado `RESTORING` automaticamente

**Pasta Protheus_Data:**
- Baixa ZIP do servidor **ou** usa ZIP local
- Remove atributos `read-only` dos arquivos antes de substituir
- Confirma antes de deletar a pasta destino

---

## API Fake

Sobe um servidor HTTP local para simular respostas de APIs durante o desenvolvimento.

- Porta configurável (padrão `8080`)
- Múltiplos endpoints com método, path, status HTTP, delay e JSON de resposta
- CORS habilitado (`Access-Control-Allow-Origin: *`)
- Log em tempo real com contadores de 2xx / 4xx+5xx
- Teste rápido via `curl` ou `Invoke-RestMethod` (PowerShell)

**Exemplo de uso:**
```
Método: GET
Path:   /api/clientes
Status: 200
Body:   {"lista": [{"id": 1, "nome": "João"}]}
```
Acesse `http://localhost:8080/api/clientes` no Postman ou browser.

---

## LogProfiler

Analisa arquivos gerados pelo **FWLogProfiler** do Protheus para identificar gargalos de performance.

**O que é o FWLogProfiler?**
Arquivo gerado pelo AppServer que registra todas as funções executadas em uma requisição, com quantidade de chamadas e tempo de processamento de cada uma.

**O que a aba oferece:**
- Resumo do log (data/hora, serviço, método, thread, tempo total da request)
- Tabela de funções ordenada por tempo total, tempo máximo ou número de chamadas
- Colorização por criticidade: 🔴 ≥ 2s | 🟡 ≥ 0.5s | 🟢 ≥ 0.1s
- Filtro por nome de função ou arquivo
- Detalhes de callers (de onde cada função foi chamada, com linha do fonte)
- Gráfico de barras horizontal com top 15 funções
- Exportação para CSV / XLSX

---

## Geração de Executável

Para distribuir sem necessidade de Python instalado:

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --name "ProtheusDicionarioTool" main.py
```

O executável será gerado em `dist/ProtheusDicionarioTool.exe`.

Para incluir ícone personalizado:
```bash
pyinstaller --onefile --windowed --name "ProtheusDicionarioTool" --icon icone.ico main.py
```

---

## .gitignore Recomendado

```gitignore
# Credenciais — nunca versionar
protheus_connections.json

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# PyInstaller
build/
dist/
*.spec

# Logs e temporários
*.log
C:/Temp/
```

---

## Contribuindo

1. Fork o repositório
2. Crie uma branch: `git checkout -b feature/minha-funcionalidade`
3. Commit: `git commit -m "feat: adiciona minha funcionalidade"`
4. Push: `git push origin feature/minha-funcionalidade`
5. Abra um Pull Request

---

## Tecnologias

- **Python 3.11+**
- **Tkinter / ttk** — interface gráfica nativa
- **pyodbc** — conexão com SQL Server
- **openpyxl** — exportação Excel
- **py7zr** — extração de arquivos 7-Zip
- **http.server** — servidor HTTP da biblioteca padrão (API Fake)

---

## Autor

João Marcos Martins

---

## Licença

Este projeto é de uso interno. Adapte conforme a política da sua organização.
