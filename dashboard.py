"""
Dashboard de leads — M7 Assessoria Jurídica

Exibe um painel visual no terminal com estatísticas dos leads qualificados.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from sheets_tool import Lead

console = Console()

# ─── Paleta de cores ──────────────────────────────────────────────────────────

COR = {
    "QUENTE": "bold red",
    "MORNO": "bold yellow",
    "FRIO": "bold blue",
    "LIGAR AGORA": "bold green",
    "NUTRIR": "bold yellow",
    "DESCARTAR": "dim",
    "header": "bold white on dark_blue",
}

EMOJI = {
    "QUENTE": "🔥",
    "MORNO": "🌡️ ",
    "FRIO": "❄️ ",
    "LIGAR AGORA": "📞",
    "NUTRIR": "💧",
    "DESCARTAR": "🗑️ ",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _barra(valor: int, total: int, largura: int = 20, cor: str = "green") -> Text:
    """Retorna uma barra de progresso simples em texto rich."""
    if total == 0:
        preenchido = 0
    else:
        preenchido = round(valor / total * largura)
    vazio = largura - preenchido
    pct = f"{valor / total * 100:.0f}%" if total else "—"
    barra_texto = Text()
    barra_texto.append("█" * preenchido, style=cor)
    barra_texto.append("░" * vazio, style="dim")
    barra_texto.append(f"  {valor} ({pct})", style="bold")
    return barra_texto


# ─── Seções do dashboard ──────────────────────────────────────────────────────

def _painel_resumo(leads: list[Lead]) -> Panel:
    total = len(leads)
    processados = sum(1 for l in leads if l.processado)
    pendentes = total - processados

    t = Table.grid(padding=(0, 4))
    t.add_column(justify="right", style="dim")
    t.add_column(justify="left", style="bold white")

    t.add_row("Total de leads", str(total))
    t.add_row("Qualificados", Text(str(processados), style="bold green"))
    t.add_row("Pendentes", Text(str(pendentes), style="bold yellow") if pendentes else Text("0", style="dim"))

    return Panel(t, title="[bold]Visão Geral[/bold]", border_style="blue", padding=(1, 2))


def _painel_classificacao(leads: list[Lead]) -> Panel:
    processados = [l for l in leads if l.processado]
    total = len(processados)

    contagem = Counter(l.classificacao for l in processados)
    ordem = ["QUENTE", "MORNO", "FRIO"]

    t = Table.grid(padding=(0, 2))
    t.add_column(width=16)
    t.add_column()

    for chave in ordem:
        n = contagem.get(chave, 0)
        emoji = EMOJI.get(chave, "")
        cor = COR.get(chave, "white")
        label = Text(f"{emoji} {chave}", style=cor)
        t.add_row(label, _barra(n, total, cor=cor.replace("bold ", "")))

    return Panel(t, title="[bold]Classificação[/bold]", border_style="blue", padding=(1, 2))


def _painel_recomendacao(leads: list[Lead]) -> Panel:
    processados = [l for l in leads if l.processado]
    total = len(processados)

    contagem = Counter(l.recomendacao for l in processados)
    ordem = ["LIGAR AGORA", "NUTRIR", "DESCARTAR"]

    t = Table.grid(padding=(0, 2))
    t.add_column(width=16)
    t.add_column()

    for chave in ordem:
        n = contagem.get(chave, 0)
        emoji = EMOJI.get(chave, "")
        cor = COR.get(chave, "white")
        label = Text(f"{emoji} {chave}", style=cor)
        t.add_row(label, _barra(n, total, cor=cor.replace("bold ", "")))

    return Panel(t, title="[bold]Recomendação[/bold]", border_style="blue", padding=(1, 2))


def _tabela_quentes(leads: list[Lead]) -> Panel:
    quentes = [l for l in leads if l.classificacao == "QUENTE"]

    if not quentes:
        return Panel(
            Text("Nenhum lead QUENTE ainda.", style="dim italic"),
            title="[bold red]🔥 Leads Quentes — Ligar Agora[/bold red]",
            border_style="red",
            padding=(1, 2),
        )

    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white")
    t.add_column("Nome", style="bold")
    t.add_column("Telefone", style="cyan")
    t.add_column("Resumo", style="white")

    for lead in quentes:
        t.add_row(lead.nome, lead.telefone, lead.resumo or "—")

    return Panel(
        t,
        title=f"[bold red]🔥 Leads Quentes — Ligar Agora ({len(quentes)})[/bold red]",
        border_style="red",
        padding=(1, 2),
    )


# ─── Função principal ─────────────────────────────────────────────────────────

def exibir(leads: list[Lead]) -> None:
    """Renderiza o dashboard completo no terminal."""
    console.print()
    console.rule("[bold dark_blue]  M7 ASSESSORIA JURÍDICA — Dashboard de Leads  [/bold dark_blue]")
    console.print()

    # Linha superior: resumo + classificação + recomendação
    console.print(
        Columns(
            [
                _painel_resumo(leads),
                _painel_classificacao(leads),
                _painel_recomendacao(leads),
            ],
            equal=False,
            expand=True,
        )
    )

    # Tabela de leads quentes
    console.print(_tabela_quentes(leads))
    console.print()
