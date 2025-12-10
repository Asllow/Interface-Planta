"""
Worker de Escrita no Banco de Dados.

Este módulo implementa uma thread dedicada ('Worker') para retirar as operações
de I/O (Input/Output) de disco da thread principal da interface e da thread
do servidor web. Isso evita que a interface congele enquanto os dados são salvos.
"""

import threading
from typing import Optional
import core.database as database
from core.shared_state import db_queue

def database_writer_thread() -> None:
    """
    Loop principal da thread de escrita.
    
    Consome dados da 'db_queue' infinitamente e os insere no banco de dados.
    O loop é interrompido quando recebe um valor 'None' (sentinela) na fila.
    """

    print("DB Writer: Thread iniciada.")
    while True:
        try:
            # db_queue.get() é bloqueante: a thread dorme até chegar dados.
            # Isso é eficiente pois não gasta CPU enquanto ocioso.
            data = db_queue.get()

            # Verificação de sinal de parada (Sentinela)
            if data is None:
                print("DB Writer: Sinal de parada recebido. Encerrando.")
                break

            # Executa a inserção no SQLite
            database.insert_data(data)

        except Exception as e:
            # Tratamento genérico para evitar que a thread morra silenciosamente
            print(f"DB Writer: Erro crítico ao inserir dados: {e}")

    print("DB Writer: Thread finalizada.")

def start_db_writer_thread() -> threading.Thread:
    """
    Inicia a thread de escrita em background (Daemon).

    Returns:
        threading.Thread: O objeto da thread iniciada.
    """

    db_thread = threading.Thread(target=database_writer_thread, daemon=True)
    db_thread.start()
    return db_thread

def stop_db_writer_thread() -> None:
    """
    Envia um sinal de parada graciosa para a thread de escrita.
    Coloca 'None' na fila para que o loop termine após processar os pendentes.
    """

    try:
        print("Enviando sinal de parada para DB Writer...")
        db_queue.put(None)
    except Exception as e:
        print(f"Erro ao enviar sinal de parada para DB Writer: {e}")