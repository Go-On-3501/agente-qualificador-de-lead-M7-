#!/usr/bin/env python3
"""
Agente Qualificador de Leads — Google Sheets
M7 Assessoria Jurídica

Lê leads da planilha, qualifica via Claude e salva o resultado na coluna F.
Leads já processados (coluna F preenchida) são ignorados.
"""

import os
import sys
import time

import anthropic
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# ─── Configuração ──────────────────────────────────────────────────────────────

load_dotenv()

SPREADSHEET_ID = "1BeUqsCsL1l7W8CIeXhWqrOGBUHkNcEz3UtlTRWFe2Mk"
SHEET_NAME = "Sheet1"          # altere se a aba tiver outro nome
CREDENTIALS_FILE = "credentials.json"

# Colunas (1-indexed)
COL_NOME = 1       # A
COL_TELEFONE = 2   # B
COL_Q1 = 3         # C  — trabalhou CLT?
COL_Q2 = 4         # D  — tem sequelas de acidente?
COL_Q3 = 5         # E  — já pediu auxílio-acidente?
COL_RESULTADO = 6  # F  — saída do agente

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

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

# ─── Funções ───────────────────────────────────────────────────────────────────


def conectar_planilha() -> gspread.Worksheet:
    """Autentica no Google Sheets e retorna a aba configurada."""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(SHEET_NAME)


def qualificar_lead(nome: str, telefone: str, q1: str, q2: str, q3: str) -> str:
    """Envia o lead para o Claude e retorna a classificação formatada."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    mensagem_usuario = (
        f"Nome: {nome}\n"
        f"Telefone: {telefone}\n"
        f"Q1 (trabalhou CLT?): {q1}\n"
        f"Q2 (tem sequelas de acidente?): {q2}\n"
        f"Q3 (já pediu auxílio-acidente?): {q3}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": mensagem_usuario}],
    )

    return response.content[0].text.strip()


def processar_planilha():
    """Lê os leads, qualifica os não processados e salva na coluna F."""
    print("Conectando ao Google Sheets...")
    ws = conectar_planilha()

    todos_registros = ws.get_all_values()

    # Ignora linha de cabeçalho (linha 1)
    linhas_dados = todos_registros[1:]

    if not linhas_dados:
        print("Nenhum lead encontrado na planilha.")
        return

    total = len(linhas_dados)
    processados = 0
    ignorados = 0

    print(f"{total} lead(s) encontrado(s).\n")

    for idx, linha in enumerate(linhas_dados, start=2):  # linha 2 no Sheets
        # Garante que a linha tem colunas suficientes
        linha = linha + [""] * (COL_RESULTADO - len(linha))

        nome = linha[COL_NOME - 1].strip()
        telefone = linha[COL_TELEFONE - 1].strip()
        q1 = linha[COL_Q1 - 1].strip()
        q2 = linha[COL_Q2 - 1].strip()
        q3 = linha[COL_Q3 - 1].strip()
        resultado_existente = linha[COL_RESULTADO - 1].strip()

        if not nome:
            continue  # linha vazia

        if resultado_existente:
            print(f"[IGNORADO] Linha {idx}: {nome} — já processado.")
            ignorados += 1
            continue

        print(f"[PROCESSANDO] Linha {idx}: {nome}...")

        try:
            resultado = qualificar_lead(nome, telefone, q1, q2, q3)
        except anthropic.APIError as e:
            print(f"  ERRO API Anthropic: {e}", file=sys.stderr)
            continue

        # Salva na célula F{idx}
        ws.update_cell(idx, COL_RESULTADO, resultado)
        processados += 1

        print(f"  → {resultado.splitlines()[0]}")  # exibe só a primeira linha

        # Pequena pausa para não ultrapassar rate limit da Sheets API
        time.sleep(0.5)

    print(f"\nConcluído. Processados: {processados} | Ignorados: {ignorados}")


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    processar_planilha()
