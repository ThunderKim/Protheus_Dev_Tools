"""
historico.py
============
Armazena as últimas N pesquisas por aba, sem duplicatas consecutivas.
Sem dependências de UI — pode ser testado isoladamente.
"""


class HistoricoConsultas:
    """Mantém um histórico de filtros por aba (máx. MAX_POR_ABA itens)."""

    MAX_POR_ABA = 20

    def __init__(self) -> None:
        self._historico: dict[str, list[str]] = {}

    def registrar(self, nome_aba: str, filtro: str) -> None:
        """Adiciona *filtro* ao histórico da aba.

        Regras:
        - Strings vazias são ignoradas.
        - Não duplica o item mais recente.
        - Move o item para o topo se já existir na lista.
        - Descarta o item mais antigo quando excede MAX_POR_ABA.
        """
        if not filtro:
            return
        lista = self._historico.setdefault(nome_aba, [])
        if lista and lista[0] == filtro:
            return
        if filtro in lista:
            lista.remove(filtro)
        lista.insert(0, filtro)
        if len(lista) > self.MAX_POR_ABA:
            lista.pop()

    def obter(self, nome_aba: str) -> list[str]:
        """Retorna cópia da lista de histórico da aba."""
        return list(self._historico.get(nome_aba, []))

    def limpar(self, nome_aba: str) -> None:
        """Apaga todo o histórico de uma aba."""
        self._historico[nome_aba] = []
