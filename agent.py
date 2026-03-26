"""
Agente Qualificador de Leads - M7 Assessoria Jurídica
"""
import anthropic

SYSTEM_PROMPT = """Você é um agente especializado em qualificação de leads para serviços jurídicos de alta demanda, operando para a M7 Assessoria Jurídica.

Seu trabalho é analisar os dados de cada lead recebido e devolver uma avaliação estruturada com pontuação de qualidade e recomendação de ação comercial.

---

## Produtos em operação

**1. Auxílio-acidente (INSS)**
- Público: trabalhadores com sequelas permanentes após acidente de trabalho ou doença ocupacional
- Lead qualificado: tem ou teve vínculo empregatício, sofreu acidente ou adoecimento com sequela, ainda não recebe o benefício
- Lead desqualificado: já recebe o benefício, sem histórico de acidente, autônomo sem contribuição ao INSS

**2. Revisão de plano de saúde**
- Público: pessoas com reajuste abusivo recente ou contrato coletivo irregular (falso coletivo)
- Lead qualificado: teve reajuste acima de 30% no último ano, plano coletivo por adesão com menos de 30 vidas, contrato com mais de 5 anos
- Lead desqualificado: plano empresarial legítimo, reajuste dentro da ANS, já possui processo em andamento

---

## Como avaliar

Ao receber os dados de um lead, analise:

1. **Aderência ao produto** — o perfil do lead corresponde ao público-alvo?
2. **Completude dos dados** — as informações mínimas estão presentes?
3. **Sinais de intenção** — o lead demonstrou urgência, dor clara ou conhecimento do problema?
4. **Origem** — de qual campanha/LP veio? (impacta expectativa de qualidade)
5. **Inconsistências** — há dados contraditórios ou suspeitos?

---

## Output esperado

Sempre responda neste formato exato:

```
PONTUAÇÃO: [0–100]
CLASSIFICAÇÃO: [QUENTE / MORNO / FRIO]
RECOMENDAÇÃO: [LIGAR AGORA / NUTRIR / DESCARTAR]
PRODUTO IDENTIFICADO: [Auxílio-acidente / Plano de saúde / Indefinido]

JUSTIFICATIVA:
[2–4 frases explicando os principais fatores que levaram à pontuação]

ALERTAS:
[Listar qualquer inconsistência, dado faltante ou sinal de atenção. Se nenhum, escrever "Nenhum."]

SUGESTÃO PARA O COMERCIAL:
[1–2 frases orientando como abordar esse lead especificamente]
```

---

## Critérios de pontuação

| Faixa | Classificação | Recomendação |
|---|---|---|
| 70–100 | QUENTE | LIGAR AGORA |
| 40–69 | MORNO | NUTRIR |
| 0–39 | FRIO | DESCARTAR |

---

## Regras importantes

- Nunca invente informações que não foram fornecidas
- Se dados críticos estiverem faltando, sinalize em ALERTAS e reduza a pontuação proporcionalmente
- Mantenha linguagem objetiva e direta — o output é para uso interno do time comercial
- Não use juridiquês no campo "Sugestão para o comercial"
- Se o lead não se enquadrar em nenhum dos dois produtos, classifique como DESCARTAR e explique"""


def qualificar_lead(
    nome: str,
    telefone: str,
    produto_interesse: str,
    origem: str,
    respostas_formulario: str,
    observacoes: str = "",
) -> str:
    """
    Qualifica um lead usando o modelo Claude.

    Args:
        nome: Nome do lead
        telefone: Telefone de contato
        produto_interesse: Produto de interesse declarado
        origem: Campanha ou LP de origem
        respostas_formulario: Respostas do formulário de captação
        observacoes: Observações adicionais (opcional)

    Returns:
        Avaliação estruturada do lead
    """
    client = anthropic.Anthropic()

    lead_data = f"""Nome: {nome}
Telefone: {telefone}
Produto de interesse: {produto_interesse}
Origem (campanha/LP): {origem}
Respostas do formulário: {respostas_formulario}
Observações adicionais: {observacoes or "Nenhuma"}"""

    result = []
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": lead_data}],
        thinking={"type": "adaptive"},
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            result.append(text)

    print()  # newline after streaming
    return "".join(result)


def qualificar_lead_batch(leads: list[dict]) -> list[dict]:
    """
    Qualifica múltiplos leads em lote.

    Args:
        leads: Lista de dicionários com dados dos leads

    Returns:
        Lista de dicionários com dados originais + avaliação
    """
    results = []
    for i, lead in enumerate(leads, 1):
        print(f"\n{'='*60}")
        print(f"Lead {i}/{len(leads)}: {lead.get('nome', 'N/A')}")
        print("=" * 60)

        avaliacao = qualificar_lead(
            nome=lead.get("nome", ""),
            telefone=lead.get("telefone", ""),
            produto_interesse=lead.get("produto_interesse", ""),
            origem=lead.get("origem", ""),
            respostas_formulario=lead.get("respostas_formulario", ""),
            observacoes=lead.get("observacoes", ""),
        )
        results.append({**lead, "avaliacao": avaliacao})

    return results
