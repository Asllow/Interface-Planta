"""
Worker de Escrita no Banco de Dados (Otimizado com Batching).
"""

import threading
from typing import Optional
import core.database as database
from core.shared_state import db_queue

def database_writer_thread() -> None:
    print("DB Writer: Thread iniciada.")
    batch = []
    
    while True:
        try:
            # 1. Pega 1 item (bloqueia o processador e descansa se a fila estiver vazia)
            data = db_queue.get()

            if data is None:
                # Se mandaram parar, salva o que sobrou no lote antes de morrer
                if batch:
                    database.insert_data_batch(batch)
                print("DB Writer: Sinal de parada recebido. Encerrando.")
                break

            batch.append(data)

            # 2. Varre a fila rapidamente pegando tudo o que chegou enquanto ele descansava
            while not db_queue.empty():
                item = db_queue.get_nowait()
                if item is None:
                    if batch:
                        database.insert_data_batch(batch)
                    print("DB Writer: Sinal de parada recebido. Encerrando.")
                    return
                
                batch.append(item)
                
                # Trava de segurança: agrupa de 2000 em 2000 para não estourar a RAM
                if len(batch) >= 2000:
                    break

            # 3. Manda o lote inteiro pro SSD (Abre e fecha o BD apenas 1 vez!)
            if batch:
                database.insert_data_batch(batch)
                batch.clear()

        except Exception as e:
            print(f"DB Writer: Erro crítico ao inserir dados: {e}")
            batch.clear()

    print("DB Writer: Thread finalizada.")

def start_db_writer_thread() -> threading.Thread:
    db_thread = threading.Thread(target=database_writer_thread, daemon=True)
    db_thread.start()
    return db_thread

def stop_db_writer_thread() -> None:
    try:
        print("Enviando sinal de parada para DB Writer...")
        db_queue.put(None)
    except Exception as e:
        print(f"Erro ao enviar sinal de parada para DB Writer: {e}")