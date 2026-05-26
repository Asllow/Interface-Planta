"""
Servidor Web (Flask + WebSocket) para Telemetria.

Este módulo disponibiliza um endpoint WebSocket para comunicação bidirecional 
em tempo real com o microcontrolador (ESP32).
"""

from flask import Flask
from flask_sock import Sock
from datetime import datetime
import queue
import threading
import json
from typing import Optional

import core.database as database
from core.shared_state import data_queue, db_queue, shared_data, data_lock

flask_app = Flask(__name__)
sock = Sock(flask_app)

# Variável global para rastrear o tempo do último pacote recebido
last_batch_time: Optional[datetime] = None

@sock.route('/ws')
def handle_ws(ws):
    """
    Endpoint WebSocket principal.
    Mantém a conexão aberta, recebe os lotes de telemetria e envia os comandos de controle.
    """
    global last_batch_time
    print("\n[WS] >>> ESP32 Conectado via WebSocket! <<<\n")
    
    while True:
        try:
            # 1. Aguarda receber dados do ESP32 (Fica bloqueado aqui até chegar algo)
            data = ws.receive()
            if not data:
                continue

            current_time = datetime.now()
            batch_interval_ms = 0

            if last_batch_time is not None:
                delta = current_time - last_batch_time
                batch_interval_ms = delta.total_seconds() * 1000

            last_batch_time = current_time
            data = data.replace(':nan', ':null')
            data = data.replace(':inf', ':null')
            data = data.replace(':-inf', ':null')
            data_batch = json.loads(data)

            # 3. Processa o array de amostras
            for item in data_batch:
                item['timestamp_recebimento'] = current_time.isoformat()
                item['batch_interval_ms'] = batch_interval_ms

                # Fila da Interface Gráfica
                try:
                    data_queue.put(item, block=False)
                except queue.Full:
                    pass

                # Fila do Banco de Dados
                if database.is_recording_enabled and database.current_run_id is not None:
                    # Carimba a amostra com o ID atual para ela não se perder!
                    item['id_experimento'] = database.current_run_id
                    try:
                        db_queue.put(item, block=False)
                    except queue.Full:
                        pass

            # 4. Resposta Imediata: Verifica se o usuário digitou um novo PWM na interface
            with data_lock:
                if shared_data["new_command_available"]:
                    # Monta o pacote e empurra pelo mesmo túnel WebSocket
                    payload = json.dumps({"new_setpoint": shared_data["current_setpoint"]})
                    ws.send(payload)
                    
                    shared_data["new_command_available"] = False
                    print(f"[WS] Enviado novo setpoint: {shared_data['current_setpoint']}")

        except json.JSONDecodeError:
            print("[WS] Erro: JSON inválido recebido.")
            print(f"String recebida: {data}")
        except Exception as e:
            # Se o ESP32 desligar, reiniciar ou a rede cair, o loop quebra aqui
            print(f"\n[WS] Conexão WebSocket encerrada: {e}\n")
            break

def start_server_thread() -> threading.Thread:
    """Inicia o servidor em uma thread separada para não travar o Tkinter."""
    print("Servidor rodando. Aguardando conexão do ESP32 em ws://0.0.0.0:5000/ws")
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=5000, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    return flask_thread