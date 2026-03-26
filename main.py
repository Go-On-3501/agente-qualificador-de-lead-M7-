#!/usr/bin/env python3
"""
Agente Qualificador de Leads — M7 Assessoria Jurídica

Modos:
  python main.py               → qualifica todos os leads pendentes
  python main.py --dashboard   → exibe painel de estatísticas
  python main.py --tudo        → qualifica pendentes e exibe painel
"""

import argparse
import os
import sys
import time

import anthropic
from dotenv import load_dotenv

import dashboard as dash
import sheets_tool as sheets

load_dotenv()

# ─── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é um agente especializado em qualificação de leads para a M7 Assessoria Jurídica, \
focado em casos de auxílio-acidente do INSS.

Analise as respostas do formulário abaixo e classifique o lead com base nos critérios:

Q1 — Trabalhou com carteira assinada (CLT)?
Q2 — Ficou com alguma sequela após acidente de trabalho ou doença ocupacional?
Q3 — Já solicitou ou recebe auxílio-acidente?

CRITÉRIOS DE QUALIFICAÇÃO:
- QUENTE (LIGAR AGORA): Q1=Sim, Q2=Sim, Q3=Não → perfil ideal, nunca solicitou e tem direito
- MORNO (NUTRIR): Q1=Sim, Q2=Sim, Q3=Sim → já solicitou; verificar situação; pode haver revisão
- FRIO (DESCARTAR): Q1=Não ou Q2=Não → sem base para o benefício

Responda EXATAMENTE neste formato, sem texto adicional:

CLASSIFICAÇÃO: [QUENTE / MORNO / FRIO]
RECOMENDAÇÃO: [LIGAR AGORA / NUTRIR / DESCARTAR]
RESUMO: [1 frase curta para o time comercial]"""


# ─── Qualificação via Claude ───────────────────────────────────────────────────

def _qualificar(lead: sheets.Lead) -> str:
    """Envia o lead ao Claude e retorna o texto de classificação."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    conteudo = (
        f"Nome: {lead.nome}\n"
        f"Telefone: {lead.telefone}\n"
        f"Q1 (trabalhou CLT?): {lead.q1}\n"
        f"Q2 (tem sequelas de acidente?): {lead.q2}\n"
        f"Q3 (já pediu auxílio-acidente?): {lead.q3}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": conteudo}],
    )

    return response.content[0].text.strip()


# ─── Modos de execução ────────────────────────────────────────────────────────

def processar(mostrar_dashboard: bool = False) -> None:
    """Qualifica todos os leads pendentes e salva na planilha."""
    print("Conectando ao Google Sheets...")
    ws = sheets.conectar()
    leads = sheets.ler_leads(ws)

    if not leads:
        print("Nenhum lead encontrado na planilha.")
        return

    pendentes = [l for l in leads if not l.processado]
    ja_feitos = len(leads) - len(pendentes)

    print(f"{len(leads)} lead(s) encontrado(s) | {ja_feitos} já qualificado(s) | {len(pendentes)} pendente(s).\n")

    for lead in pendentes:
        print(f"[PROCESSANDO] Linha {lead.linha}: {lead.nome}...")

        try:
            resultado = _qualificar(lead)
        except anthropic.APIError as e:
            print(f"  ERRO API Anthropic: {e}", file=sys.stderr)
            continue

        sheets.salvar_resultado(ws, lead.linha, resultado)
        lead.resultado = resultado
        lead.parse_resultado()

        print(f"  → {lead.classificacao} | {lead.recomendacao}")
        time.sleep(0.5)  # evita rate limit da Sheets API

    total_processados = sum(1 for l in leads if l.processado)
    print(f"\nConcluído. {total_processados}/{len(leads)} lead(s) qualificado(s).")

    if mostrar_dashboard:
        dash.exibir(leads)


def exibir_dashboard() -> None:
    """Lê a planilha e exibe o painel de estatísticas sem processar nada."""
    print("Conectando ao Google Sheets...")
    ws = sheets.conectar()
    leads = sheets.ler_leads(ws)

    if not leads:
        print("Nenhum lead encontrado na planilha.")
        return

    dash.exibir(leads)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agente Qualificador de Leads — M7 Assessoria Jurídica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py               Qualifica leads pendentes
  python main.py --dashboard   Exibe painel de estatísticas
  python main.py --tudo        Qualifica pendentes e exibe painel
        """,
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Exibe painel de estatísticas dos leads já qualificados",
    )
    parser.add_argument(
        "--tudo",
        action="store_true",
        help="Qualifica leads pendentes e exibe o painel ao final",
    )

    args = parser.parse_args()

    if args.dashboard:
        exibir_dashboard()
    elif args.tudo:
        processar(mostrar_dashboard=True)
    else:
        processar(mostrar_dashboard=False)


if __name__ == "__main__":
    main()
