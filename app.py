"""
Plataforma de Qualificação de Leads — M7 Assessoria Jurídica
Streamlit app: lê Google Sheets, exibe relatório e aciona o agente Claude.
"""

from __future__ import annotations

import os
import time

import anthropic
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

import sheets_tool as sheets

load_dotenv()

# ─── Configuração da página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="M7 — Qualificação de Leads",
    page_icon="⚖️",
    layout="wide",
)

# ─── System prompt (mesmo do main.py) ────────────────────────────────────────

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

# ─── Helpers ──────────────────────────────────────────────────────────────────

COR_CLASSE = {"QUENTE": "🔥 QUENTE", "MORNO": "🌡️ MORNO", "FRIO": "❄️ FRIO"}
COR_BADGE = {"QUENTE": "#c0392b", "MORNO": "#e67e22", "FRIO": "#2980b9"}


@st.cache_data(ttl=60, show_spinner="Carregando dados da planilha...")
def carregar_leads() -> list[sheets.Lead]:
    ws = sheets.conectar()
    return sheets.ler_leads(ws)


def leads_para_df(leads: list[sheets.Lead]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Nome": l.nome,
                "Telefone": l.telefone,
                "CLT (Q1)": l.q1,
                "Sequelas (Q2)": l.q2,
                "Pediu auxílio (Q3)": l.q3,
                "Classificação": l.classificacao or ("—" if l.processado else "Pendente"),
                "Recomendação": l.recomendacao or ("—" if l.processado else "Pendente"),
                "Resumo": l.resumo or "",
                "Linha": l.linha,
            }
            for l in leads
        ]
    )


def _qualificar_lead(lead: sheets.Lead) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)
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


# ─── Seções da UI ─────────────────────────────────────────────────────────────

def secao_metricas(leads: list[sheets.Lead]) -> None:
    total = len(leads)
    processados = sum(1 for l in leads if l.processado)
    pendentes = total - processados
    quentes = sum(1 for l in leads if l.classificacao == "QUENTE")
    mornos = sum(1 for l in leads if l.classificacao == "MORNO")
    frios = sum(1 for l in leads if l.classificacao == "FRIO")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total de Leads", total)
    c2.metric("Qualificados", processados)
    c3.metric("Pendentes", pendentes, delta=f"-{pendentes}" if pendentes else None,
              delta_color="inverse")
    c4.metric("🔥 Quentes", quentes)
    c5.metric("🌡️ Mornos", mornos)
    c6.metric("❄️ Frios", frios)


def secao_graficos(leads: list[sheets.Lead]) -> None:
    processados = [l for l in leads if l.processado]
    if not processados:
        st.info("Nenhum lead qualificado ainda. Rode o agente para ver os gráficos.")
        return

    col1, col2 = st.columns(2)

    # Gráfico de classificação
    with col1:
        contagem_classe = pd.Series(
            [l.classificacao for l in processados]
        ).value_counts().reset_index()
        contagem_classe.columns = ["Classificação", "Quantidade"]
        ordem = ["QUENTE", "MORNO", "FRIO"]
        cores = {"QUENTE": "#c0392b", "MORNO": "#e67e22", "FRIO": "#2980b9"}
        fig = px.bar(
            contagem_classe,
            x="Classificação",
            y="Quantidade",
            color="Classificação",
            color_discrete_map=cores,
            category_orders={"Classificação": ordem},
            title="Leads por Classificação",
            text="Quantidade",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig, use_container_width=True)

    # Gráfico de recomendação (pizza)
    with col2:
        contagem_rec = pd.Series(
            [l.recomendacao for l in processados]
        ).value_counts().reset_index()
        contagem_rec.columns = ["Recomendação", "Quantidade"]
        cores_rec = {
            "LIGAR AGORA": "#27ae60",
            "NUTRIR": "#e67e22",
            "DESCARTAR": "#7f8c8d",
        }
        fig2 = px.pie(
            contagem_rec,
            names="Recomendação",
            values="Quantidade",
            color="Recomendação",
            color_discrete_map=cores_rec,
            title="Distribuição de Recomendações",
            hole=0.4,
        )
        fig2.update_layout(height=340)
        st.plotly_chart(fig2, use_container_width=True)


def secao_quentes(leads: list[sheets.Lead]) -> None:
    quentes = [l for l in leads if l.classificacao == "QUENTE"]
    st.subheader(f"🔥 Ligar Agora — {len(quentes)} lead(s)")

    if not quentes:
        st.info("Nenhum lead QUENTE qualificado ainda.")
        return

    df = pd.DataFrame(
        [{"Nome": l.nome, "Telefone": l.telefone, "Resumo": l.resumo} for l in quentes]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


def secao_tabela_completa(leads: list[sheets.Lead]) -> None:
    st.subheader("Todos os Leads")

    df = leads_para_df(leads).drop(columns=["Linha"])

    def colorir_linha(row: pd.Series):
        cor = {"QUENTE": "#fde8e8", "MORNO": "#fef3e2", "FRIO": "#e8f0fe"}.get(
            row["Classificação"], ""
        )
        return [f"background-color: {cor}" if cor else ""] * len(row)

    st.dataframe(
        df.style.apply(colorir_linha, axis=1),
        use_container_width=True,
        hide_index=True,
    )


def secao_agente(leads: list[sheets.Lead]) -> None:
    pendentes = [l for l in leads if not l.processado]
    st.subheader("⚡ Rodar Agente de Qualificação")

    if not pendentes:
        st.success("Todos os leads já foram qualificados.")
        return

    st.info(f"{len(pendentes)} lead(s) pendente(s) de qualificação.")

    if st.button(f"Qualificar {len(pendentes)} lead(s) agora", type="primary"):
        ws = sheets.conectar()
        barra = st.progress(0, text="Iniciando...")
        erros = 0

        for i, lead in enumerate(pendentes):
            barra.progress(i / len(pendentes), text=f"Qualificando: {lead.nome}…")
            try:
                resultado = _qualificar_lead(lead)
                sheets.salvar_resultado(ws, lead.linha, resultado)
            except Exception as e:
                st.error(f"Erro em {lead.nome}: {e}")
                erros += 1
            time.sleep(0.3)

        barra.progress(1.0, text="Concluído!")
        carregar_leads.clear()  # invalida o cache para recarregar os dados

        if erros == 0:
            st.success(f"{len(pendentes)} lead(s) qualificado(s) com sucesso!")
        else:
            st.warning(f"Concluído com {erros} erro(s).")

        st.rerun()


# ─── Layout principal ─────────────────────────────────────────────────────────

def main() -> None:
    st.title("⚖️ M7 Assessoria Jurídica")
    st.caption("Plataforma de Qualificação de Leads — Auxílio-Acidente INSS")

    leads = carregar_leads()

    if not leads:
        st.warning("Nenhum lead encontrado na planilha.")
        return

    # Atualizar dados manualmente
    if st.button("🔄 Atualizar dados", key="refresh"):
        carregar_leads.clear()
        st.rerun()

    st.divider()

    # KPIs
    secao_metricas(leads)
    st.divider()

    # Gráficos
    secao_graficos(leads)
    st.divider()

    # Leads quentes (prioridade)
    secao_quentes(leads)
    st.divider()

    # Tabela completa
    secao_tabela_completa(leads)
    st.divider()

    # Painel do agente
    secao_agente(leads)


if __name__ == "__main__":
    main()
