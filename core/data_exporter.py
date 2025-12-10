"""
Módulo de Exportação de Dados.

Este módulo fornece funcionalidades para exportar os dados de telemetria
recuperados do banco de dados para formatos de arquivo comuns (CSV, TXT, NPY),
facilitando a análise externa em ferramentas como Excel, MATLAB ou scripts Python.
"""

import csv
import numpy as np
from typing import List, Dict, Any

def export_to_csv(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Exporta uma lista de dados para um arquivo CSV (Comma Separated Values).

    O arquivo gerado inclui um cabeçalho com os nomes das chaves do dicionário.

    Args:
        data (List[Dict[str, Any]]): Lista de dicionários contendo os dados a serem exportados.
        filename (str): Caminho completo (incluindo nome e extensão) do arquivo de saída.
    """

    if not data:
        print("Exportar CSV: Nenhum dado para exportar.")
        return

    # Assume que todos os dicionários têm as mesmas chaves
    headers = data[0].keys()

    print(f"Exportando {len(data)} linhas para CSV em {filename}...")
    try:
        # newline='' é importante no Windows para evitar linhas em branco extras
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        print("Exportação CSV concluída.")
    except Exception as e:
        print(f"ERRO ao exportar para CSV: {e}")

def export_to_txt(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Exporta uma lista de dados para um arquivo de texto tabulado (.txt).

    Os valores são separados por tabulação ('\\t'), útil para importação
    em softwares que não suportam CSV padrão ou para visualização simples.

    Args:
        data (List[Dict[str, Any]]): Lista de dicionários contendo os dados.
        filename (str): Caminho do arquivo de saída.
    """

    if not data:
        print("Exportar TXT: Nenhum dado para exportar.")
        return

    headers = data[0].keys()

    print(f"Exportando {len(data)} linhas para TXT em {filename}...")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Escreve o cabeçalho separado por tabs
            f.write('\t'.join(headers) + '\n')

            # Escreve as linhas de dados
            for row in data:
                values = [str(row.get(h, '')) for h in headers]
                f.write('\t'.join(values) + '\n')
        print("Exportação TXT concluída.")
    except Exception as e:
        print(f"ERRO ao exportar para TXT: {e}")

def export_to_npy(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Exporta os dados para um arquivo binário NumPy (.npy).

    Cria um 'Structured Array' do NumPy com tipos de dados definidos,
    ideal para carregamento rápido em análises posteriores com Python/NumPy.

    Tipos definidos:
    - timestamp_amostra_ms: Inteiro 64-bit (i8)
    - valor_adc: Inteiro 32-bit (i4)
    - tensao_mv: Inteiro 32-bit (i4)
    - sinal_controle: Ponto flutuante 64-bit (f8)

    Args:
        data (List[Dict[str, Any]]): Lista de dicionários contendo os dados.
        filename (str): Caminho do arquivo de saída.
    """

    if not data:
        print("Exportar NPY: Nenhum dado para exportar.")
        return

    print(f"Convertendo e exportando {len(data)} linhas para NPY em {filename}...")
    try:
        # Define o esquema (schema) do array estruturado
        dtype = [
            ('timestamp_amostra_ms', 'i8'),
            ('valor_adc', 'i4'),
            ('tensao_mv', 'i4'),
            ('sinal_controle', 'f8')
        ]

        # Converte a lista de dicts para uma lista de tuplas compatível com o dtype
        lista_de_tuplas = [
            (
                d.get('timestamp_amostra_ms', 0),
                d.get('valor_adc', 0),
                d.get('tensao_mv', 0),
                d.get('sinal_controle', 0.0)
            )
            for d in data
        ]

        structured_array = np.array(lista_de_tuplas, dtype=dtype)

        np.save(filename, structured_array)
        print("Exportação NPY concluída.")
    except Exception as e:
        print(f"ERRO ao exportar para NPY: {e}")