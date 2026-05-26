import time
import json
from datetime import datetime
from flask import Flask
from flask_sock import Sock

import core.database as database
from core.shared_state import db_queue
from core.db_writer import start_db_writer_thread, stop_db_writer_thread

app = Flask(__name__)
sock = Sock(app)

# --- CONFIGURAÇÕES DO ENSAIO ---
SEQUENCE = [50, 60, 50, 40, 60, 40, 50]
STEP_DURATION = 30       # Tempo em cada degrau (segundos)
STABILIZATION_TIME = 10  # Tempo esperando a planta estabilizar nos 50% ANTES de gravar

@sock.route('/ws')
def handle_ws(ws):
    print("\n[WS] >>> ESP32 Conectado! <<<")
    
    # ---------------------------------------------------------
    # FASE 1: ESTABILIZAÇÃO (Leva ao ponto de operação sem gravar)
    # ---------------------------------------------------------
    initial_setpoint = SEQUENCE[0]
    payload = json.dumps({"new_setpoint": initial_setpoint})
    ws.send(payload)
    
    print(f"\n[ESTABILIZAÇÃO] Motor acionado em {initial_setpoint}%.")
    print(f"[ESTABILIZAÇÃO] Aguardando {STABILIZATION_TIME} segundos para a planta acomodar...")
    
    start_stab = time.time()
    while time.time() - start_stab < STABILIZATION_TIME:
        try:
            # Timeout relaxado (1.0s) para ler pacotes gigantes (30 KB) sem corromper
            ws.receive(timeout=1.0)
        except Exception:
            pass

    print("[ESTABILIZAÇÃO] Concluída! A planta está no ponto de operação.")
    
    # ---------------------------------------------------------
    # FASE 2: GRAVAÇÃO DO ENSAIO OFICIAL
    # ---------------------------------------------------------
    database.start_new_experiment()
    print(f"\n[DB] Experimento #{database.current_run_id} INICIADO e gravando no Banco de Dados!")
    
    start_time = time.time()
    last_sent_setpoint = initial_setpoint 
    
    while True:
        elapsed = time.time() - start_time
        step_index = int(elapsed // STEP_DURATION)
        
        if step_index >= len(SEQUENCE):
            print(f"\n[FIM] Experimento de {len(SEQUENCE) * STEP_DURATION} segundos concluído!")
            break
            
        current_setpoint = SEQUENCE[step_index]
        
        if current_setpoint != last_sent_setpoint:
            payload = json.dumps({"new_setpoint": current_setpoint})
            ws.send(payload)
            last_sent_setpoint = current_setpoint
            print(f"[{elapsed:05.1f}s] Degrau alterado -> Enviando PWM: {current_setpoint}%")
        
        try:
            # Novamente, timeout folgado para manter a sincronia da string JSON perfeita
            data = ws.receive(timeout=1.0)
            
            if data:
                data_batch = json.loads(data)
                current_time = datetime.now()
                
                for item in data_batch:
                    item['timestamp_recebimento'] = current_time.isoformat()
                    item['id_experimento'] = database.current_run_id
                    db_queue.put(item)
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            if "timeout" not in str(e).lower():
                print(f"\n[ERRO] Conexão interrompida: {e}")
                break

    database.close_current_experiment()
    print("[DB] Gravação encerrada com sucesso.")
    ws.close()

if __name__ == "__main__":
    print("Inicializando Banco de Dados...")
    database.init_db()
    
    print("Ligando o trabalhador de gravação (DB Writer)...")
    writer_thread = start_db_writer_thread()
    
    try:
        print("\nServidor de Experimento Automático rodando...")
        print("Aguardando conexão do ESP32 em ws://0.0.0.0:5000/ws")
        app.run(host='0.0.0.0', port=5000, use_reloader=False)
    finally:
        print("\nEncerrando sistema e salvando últimos dados...")
        stop_db_writer_thread()
        writer_thread.join(timeout=3.0)
        print("Finalizado.")