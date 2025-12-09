import core.database as database
from core.shared_state import db_queue
import threading

def database_writer_thread():
    print("DB Writer: Thread iniciada.")
    while True:
        try:
            data = db_queue.get()

            if data is None:
                print("DB Writer: Sinal de parada recebido. Encerrando.")
                break
            database.insert_data(data)
        except Exception as e:
            print(f"DB Writer: Erro ao inserir dados: {e}")
    print("DB Writer: Thread finalizada.")

def start_db_writer_thread():
    db_thread = threading.Thread(target=database_writer_thread, daemon=True)
    db_thread.start()
    return db_thread

def stop_db_writer_thread():
    try:
        print("Enviando sinal de parada para DB Writer...")
        db_queue.put(None)
    except Exception as e:
        print(f"Erro ao enviar sinal de parada para DB Writer: {e}")