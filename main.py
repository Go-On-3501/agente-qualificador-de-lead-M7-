#!/usr/bin/env python3
"""
CLI para o Agente Qualificador de Leads - M7 Assessoria Jurídica
"""
import argparse
import json
import sys
from agent import qualificar_lead, qualificar_lead_batch


def interativo():
    """Modo interativo: coleta dados do lead via terminal."""
    print("\n" + "=" * 60)
    print("  AGENTE QUALIFICADOR DE LEADS — M7 ASSESSORIA JURÍDICA")
    print("=" * 60)
    print("\nPreencha os dados do lead:\n")

    nome = input("Nome: ").strip()
    telefone = input("Telefone: ").strip()
    produto_interesse = input("Produto de interesse: ").strip()
    origem = input("Origem (campanha/LP): ").strip()

    print("Respostas do formulário (pressione Enter duas vezes para finalizar):")
    linhas = []
    while True:
        linha = input()
        if linha == "" and linhas and linhas[-1] == "":
            break
        linhas.append(linha)
    respostas_formulario = "\n".join(linhas).strip()

    observacoes = input("\nObservações adicionais (opcional): ").strip()

    print("\n" + "-" * 60)
    print("AVALIAÇÃO DO LEAD:")
    print("-" * 60 + "\n")

    qualificar_lead(
        nome=nome,
        telefone=telefone,
        produto_interesse=produto_interesse,
        origem=origem,
        respostas_formulario=respostas_formulario,
        observacoes=observacoes,
    )


def arquivo(path: str):
    """Modo arquivo: lê leads de um JSON e processa em lote."""
    try:
        with open(path, encoding="utf-8") as f:
            leads = json.load(f)
    except FileNotFoundError:
        print(f"Erro: arquivo '{path}' não encontrado.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Erro ao ler JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(leads, list):
        leads = [leads]

    resultados = qualificar_lead_batch(leads)

    output_path = path.replace(".json", "_avaliados.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n\nResultados salvos em: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Agente Qualificador de Leads — M7 Assessoria Jurídica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py                          # modo interativo
  python main.py --arquivo leads.json     # processar arquivo JSON
  python main.py --exemplo                # qualificar lead de exemplo
        """,
    )
    parser.add_argument(
        "--arquivo",
        metavar="PATH",
        help="Caminho para arquivo JSON com lista de leads",
    )
    parser.add_argument(
        "--exemplo",
        action="store_true",
        help="Qualificar um lead de exemplo para demonstração",
    )

    args = parser.parse_args()

    if args.arquivo:
        arquivo(args.arquivo)
    elif args.exemplo:
        print("\n" + "=" * 60)
        print("  AGENTE QUALIFICADOR DE LEADS — M7 ASSESSORIA JURÍDICA")
        print("  [LEAD DE EXEMPLO]")
        print("=" * 60 + "\n")

        qualificar_lead(
            nome="Carlos Mendes",
            telefone="(11) 99876-5432",
            produto_interesse="Auxílio-acidente INSS",
            origem="Facebook - campanha acidente trabalho",
            respostas_formulario=(
                "Sofreu acidente: Sim\n"
                "Data do acidente: março de 2022\n"
                "Ficou com sequela: Sim, limitação no ombro direito\n"
                "Recebia pelo INSS: Recebi auxílio-doença por 8 meses, depois tive alta\n"
                "Atualmente trabalha: Sim, voltei ao trabalho mas com restrição\n"
                "Já recebe auxílio-acidente: Não"
            ),
            observacoes="Lead chegou perguntando se ainda tem direito mesmo tendo tido alta",
        )
    else:
        interativo()


if __name__ == "__main__":
    main()
