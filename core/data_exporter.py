import csv
import numpy as np

def export_to_csv(data, filename):
    if not data:
        print("Exportar CSV: Nenhum dado para exportar.")
        return

    headers = data[0].keys()

    print(f"Exportando {len(data)} linhas para CSV em {filename}...")
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        print("Exportação CSV concluída.")
    except Exception as e:
        print(f"ERRO ao exportar para CSV: {e}")

def export_to_txt(data, filename):
    if not data:
        print("Exportar TXT: Nenhum dado para exportar.")
        return

    headers = data[0].keys()

    print(f"Exportando {len(data)} linhas para TXT em {filename}...")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\t'.join(headers) + '\n')
            for row in data:
                values = [str(row.get(h, '')) for h in headers]
                f.write('\t'.join(values) + '\n')
        print("Exportação TXT concluída.")
    except Exception as e:
        print(f"ERRO ao exportar para TXT: {e}")

def export_to_npy(data, filename):
    if not data:
        print("Exportar NPY: Nenhum dado para exportar.")
        return

    print(f"Convertendo e exportando {len(data)} linhas para NPY em {filename}...")
    try:
        dtype = [
            ('timestamp_amostra_ms', 'i8'),
            ('valor_adc', 'i4'),
            ('tensao_mv', 'i4'),
            ('sinal_controle', 'f8')
        ]

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