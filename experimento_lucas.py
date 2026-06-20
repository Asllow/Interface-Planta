import time
import json
import random
from datetime import datetime
from flask import Flask
from flask_sock import Sock

import core.database as database
from core.shared_state import db_queue
from core.db_writer import start_db_writer_thread, stop_db_writer_thread

app = Flask(__name__)
sock = Sock(app)

# --- CONFIGURAÇÕES DA FASE 2: ENSAIO DE MODELAGEM ("O Certinho") ---
SEQUENCE = [50, 60, 50, 40, 60, 40, 50]
STEP_DURATION = 30       # Tempo em cada degrau (segundos)
STABILIZATION_TIME = 10  # Tempo esperando a planta estabilizar nos 50% ANTES de gravar

# --- CONFIGURAÇÕES DA FASE 3: ENSAIO DE VALIDAÇÃO (AMPLITUDE FIXA, TEMPO ALEATÓRIO) ---
NUM_VALIDATION_STEPS = 8 
# Valores de PWM redondos que o script pode escolher
VALID_PWM_VALUES = [40, 45, 50, 55, 60]
# Limites de tempo (em segundos) para a duração de cada degrau
MIN_TIME_S = 10
MAX_TIME_S = 30

@sock.route('/ws')
def handle_ws(ws):
    print("\n[WS] >>> ESP32 Ligado! <<<")
    
    # ---------------------------------------------------------
    # FASE 1: ESTABILIZAÇÃO (Leva ao ponto de operação sem gravar)
    # ---------------------------------------------------------
    initial_setpoint = SEQUENCE[0]
    payload = json.dumps({"new_setpoint": initial_setpoint})
    ws.send(payload)
    
    print(f"\n[ESTABILIZAÇÃO] Motor acionado em {initial_setpoint}%.")
    print(f"[ESTABILIZAÇÃO] A aguardar {STABILIZATION_TIME} segundos para a planta estabilizar...")
    
    start_stab = time.time()
    while time.time() - start_stab < STABILIZATION_TIME:
        try:
            ws.receive(timeout=1.0)
        except Exception:
            pass

    print("[ESTABILIZAÇÃO] Concluída! A planta está no ponto de operação.")
    


    # ---------------------------------------------------------
    # FASE 3: GRAVAÇÃO DO ENSAIO DE VALIDAÇÃO (AMPLITUDE FIXA, TEMPO ALEATÓRIO)
    # ---------------------------------------------------------
    print("\n==================================================")
    print("  A INICIAR FASE 3: VALIDAÇÃO (AMPLIT. FIXA, TEMPO ALEAT.) ")
    print("==================================================")
    
    database.start_new_experiment()
    print(f"[DB] Experimento de Validação #{database.current_run_id} INICIADO!")
    
    try:
        for step in range(NUM_VALIDATION_STEPS):
            # MUDANÇA AQUI:
            # Sorteia o PWM da lista restrita
            rnd_setpoint = random.choice(VALID_PWM_VALUES)
            # Sorteia o tempo de forma verdadeiramente aleatória (inteiro) entre os limites
            rnd_duration = random.randint(MIN_TIME_S, MAX_TIME_S)
            
            print(f"\n[VALIDAÇÃO] Degrau {step+1}/{NUM_VALIDATION_STEPS} -> Setpoint: {rnd_setpoint}%, Duração: {rnd_duration}s")
            
            payload = json.dumps({"new_setpoint": rnd_setpoint})
            ws.send(payload)
            
            start_step_time = time.time()
            while time.time() - start_step_time < rnd_duration:
                try:
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
                        raise e
                        
        print(f"\n[FIM FASE 3] Experimento de validação concluído!")
        
    except Exception as e:
        print(f"\n[ERRO] Conexão interrompida durante a validação: {e}")
    finally:
        database.close_current_experiment()
        print("[DB] Gravação da Validação encerrada com sucesso.")
        
    print("\n>>> TODOS OS ENSAIOS FINALIZADOS! <<<")
    ws.close()

if __name__ == "__main__":
    print("A inicializar Banco de Dados...")
    database.init_db()
    
    print("A limpar experiências inacabadas anteriores...")
    database.startup_cleanup()
    
    print("A ligar o trabalhador de gravação (DB Writer)...")
    writer_thread = start_db_writer_thread()
    
    try:
        print("\nServidor de Experiência Automática a correr...")
        print("A aguardar conexão do ESP32 em ws://0.0.0.0:5000/ws")
        app.run(host='0.0.0.0', port=5000, use_reloader=False)
    finally:
        print("\nA encerrar sistema e a guardar últimos dados...")
        stop_db_writer_thread()
        writer_thread.join(timeout=3.0)
        print("Finalizado.")