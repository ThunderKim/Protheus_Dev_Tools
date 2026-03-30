"""
main.py
=======
Ponto de entrada da aplicação Protheus Dev Tools.

Uso:
    python main.py
"""

import sys
import os

# Garante que o diretório raiz do pacote esteja no path,
# permitindo imports como "from config import CONFIG" em qualquer módulo.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
