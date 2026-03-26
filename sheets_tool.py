"""
Ferramenta de acesso ao Google Sheets — M7 Assessoria Jurídica

Responsabilidades:
  - Autenticar via conta de serviço (credentials.json)
  - Ler todos os leads da planilha
  - Salvar resultados na coluna F
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

# ─── Constantes ───────────────────────────────────────────────────────────────

SPREADSHEET_ID = "1BeUqsCsL1l7W8CIeXhWqrOGBUHkNcEz3UtlTRWFe2Mk"
SHEET_NAME = "Sheet1"
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Índices de coluna (1-based, para gspread)
COL_NOME = 1        # A
COL_TELEFONE = 2    # B
COL_Q1 = 3          # C — trabalhou CLT?
COL_Q2 = 4          # D — tem sequelas de acidente?
COL_Q3 = 5          # E — já pediu auxílio-acidente?
COL_RESULTADO = 6   # F — saída do agente


# ─── Modelo de dados ──────────────────────────────────────────────────────────

@dataclass
class Lead:
    linha: int                        # número real da linha na planilha (2+)
    nome: str
    telefone: str
    q1: str                           # trabalhou CLT?
    q2: str                           # tem sequelas?
    q3: str                           # já pediu auxílio-acidente?
    resultado: str = ""               # conteúdo atual da coluna F

    # campos extraídos do resultado (populados por parse_resultado)
    classificacao: str = ""           # QUENTE / MORNO / FRIO
    recomendacao: str = ""            # LIGAR AGORA / NUTRIR / DESCARTAR
    resumo: str = ""

    @property
    def processado(self) -> bool:
        return bool(self.resultado.strip())

    def parse_resultado(self) -> None:
        """Extrai classificação/recomendação/resumo do texto salvo na coluna F."""
        for linha_texto in self.resultado.splitlines():
            linha_texto = linha_texto.strip()
            if linha_texto.startswith("CLASSIFICAÇÃO:"):
                self.classificacao = linha_texto.split(":", 1)[1].strip()
            elif linha_texto.startswith("RECOMENDAÇÃO:"):
                self.recomendacao = linha_texto.split(":", 1)[1].strip()
            elif linha_texto.startswith("RESUMO:"):
                self.resumo = linha_texto.split(":", 1)[1].strip()


# ─── Funções públicas ─────────────────────────────────────────────────────────

def conectar() -> gspread.Worksheet:
    """
    Autentica e retorna o worksheet configurado.

    Tenta dois métodos em ordem:
      1. st.secrets["gcp_service_account"] — usado no Streamlit Cloud
      2. credentials.json local — usado em desenvolvimento
    """
    try:
        import streamlit as st  # só disponível quando rodando via Streamlit
        info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)

    gc = gspread.authorize(creds)
    return gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)


def ler_leads(ws: gspread.Worksheet) -> list[Lead]:
    """
    Lê todas as linhas da planilha (ignorando o cabeçalho) e retorna
    uma lista de objetos Lead, com resultados já parseados.
    """
    todas = ws.get_all_values()
    leads: list[Lead] = []

    for idx, row in enumerate(todas[1:], start=2):  # start=2: linha real na planilha
        # Garante que a linha tem pelo menos 6 colunas
        row = row + [""] * (COL_RESULTADO - len(row))

        nome = row[COL_NOME - 1].strip()
        if not nome:
            continue  # linha vazia

        lead = Lead(
            linha=idx,
            nome=nome,
            telefone=row[COL_TELEFONE - 1].strip(),
            q1=row[COL_Q1 - 1].strip(),
            q2=row[COL_Q2 - 1].strip(),
            q3=row[COL_Q3 - 1].strip(),
            resultado=row[COL_RESULTADO - 1].strip(),
        )

        if lead.processado:
            lead.parse_resultado()

        leads.append(lead)

    return leads


def salvar_resultado(ws: gspread.Worksheet, linha: int, resultado: str) -> None:
    """Grava o resultado do agente na célula F{linha}."""
    ws.update_cell(linha, COL_RESULTADO, resultado)
