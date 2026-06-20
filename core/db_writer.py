"""
Thread de Persistência Assíncrona e Buffering (Write-Ahead Logging).

Este módulo implementa o agendador de I/O em formato híbrido (Tempo + Volume).
Garante que a fila contínua de telemetria UDP (200Hz) não sature os ciclos
de leitura/escrita do disco SSD/SD Card, agrupando as métricas e consolidando
o lote a cada 1 segundo rígido.
"""

import threading
import time
import queue
import core.database as database
from core.shared_state import db_queue


def database_writer_thread() -> None:
    """
    Loop primário do Daemon de Escrita.
    
    Estratégia de Descarga (Flush):
    1. Baseado em Tempo: A cada 1.0 segundos.
    2. Baseado em Volume: A cada 500 amostras acumuladas.
    3. Sinal de Shutdown: Descarga mandatória do buffer pendente.
    """
    print("DB Writer: Daemon alocado e a aguardar fluxos de telemetria.")
    
    batch = []
    flush_interval_sec = 1.0
    batch_size_limit = 500
    last_flush_time = time.time()
    
    while True:
        try:
            # Suspensão da thread até 0.1s. Evita bloqueio I/O contínuo e polling agressivo.
            item = db_queue.get(timeout=0.1)
            
            if item is None:  # Sinal de Shutdown/Poison Pill
                if batch:
                    database.insert_data_batch(batch)
                print("DB Writer: Sinal de interrupção recebido. Buffer purgado. A encerrar.")
                break

            batch.append(item)
            
        except queue.Empty:
            # Timeout esperado. Segue para a validação das condições de flush.
            pass
        except Exception as e:
            print(f"DB Writer: Falha operacional no agendador de fila: {e}")
            
        current_time = time.time()
        time_to_flush = (current_time - last_flush_time) >= flush_interval_sec
        size_to_flush = len(batch) >= batch_size_limit

        # Condição Híbrida: Aciona a gravação SQLite estritamente se houver dados e gatilho ativo.
        if batch and (time_to_flush or size_to_flush):
            database.insert_data_batch(batch)
            batch.clear()
            last_flush_time = time.time()

    print("DB Writer: Daemon finalizado em segurança.")


def start_db_writer_thread() -> threading.Thread:
    """Injeta o ciclo de I/O numa subrotina desacoplada."""
    db_thread = threading.Thread(target=database_writer_thread, daemon=True)
    db_thread.start()
    return db_thread


def stop_db_writer_thread() -> None:
    """Injeta a diretiva de paragem estrita (Poison Pill) na fila de persistência."""
    try:
        print("Enviando sinal de suspensão para o DB Writer...")
        db_queue.put(None)
    except Exception as e:
        print(f"Erro ao sinalizar o bloqueio do DB Writer: {e}")