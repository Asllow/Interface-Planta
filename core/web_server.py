"""
Servidor Web (Flask) para Telemetria.

Este módulo disponibiliza uma API HTTP para receber dados do microcontrolador (ESP32).
Ele gerencia:
1. A recepção de dados em lotes (batches) via POST request.
2. O cálculo de latência/intervalo entre pacotes.
3. A distribuição segura (Thread-safe) dos dados para as filas de visualização e gravação.
4. O envio de comandos de controle (Setpoints) de volta para o ESP32 na resposta.
"""

from flask import Flask, request, jsonify, Response
from datetime import datetime
import queue
import threading
from typing import Optional

import core.database as database
from core.shared_state import data_queue, db_queue, shared_data, data_lock

flask_app = Flask(__name__)

# Variável global para rastrear o tempo do último pacote recebido
last_batch_time: Optional[datetime] = None

@flask_app.route('/data', methods=['POST'])
def handle_data() -> Response:
    """
    Endpoint principal para recepção de telemetria.

    Processa um JSON contendo uma lista (batch) de amostras enviadas pelo ESP32.
    Calcula o intervalo de recebimento entre batches e enfileira os dados.

    Returns:
        Response: Objeto JSON contendo status e, opcionalmente, um novo setpoint de controle.
    """
    
    global last_batch_time
    current_time = datetime.now()
    batch_interval_ms = 0

    # Calcula o tempo decorrido desde o último pacote (para diagnóstico de rede)
    if last_batch_time is not None:
        delta = current_time - last_batch_time
        batch_interval_ms = delta.total_seconds() * 1000

    last_batch_time = current_time

    # Obtém o payload JSON (espera-se uma lista de dicionários)
    data_batch = request.get_json()

    # Proteção contra payloads vazios
    if data_batch is None:
        return jsonify({"status": "no data"}), 400

    for item in data_batch:
        # Enriquece os dados com metadados do servidor
        item['timestamp_recebimento'] = current_time.isoformat()
        item['batch_interval_ms'] = batch_interval_ms

        # 1. Envia para a fila de Visualização (Prioridade: Interface Gráfica)
        # O bloco 'try' evita que o servidor trave se a fila da GUI estiver cheia
        try:
            data_queue.put(item, block=False)
        except queue.Full:
            pass

        # 2. Envia para a fila de Banco de Dados (Apenas se a gravação estiver ativa)
        if database.is_recording_enabled:
            try:
                db_queue.put(item, block=False)
            except queue.Full:
                print("Aviso: Fila do DB cheia, descartando amostra de gravação.")
                pass

    # Verifica se há comandos pendentes (Setpoints) para enviar ao ESP32
    response_payload = {
        "new_setpoint": None
    }
    with data_lock:
        if shared_data["new_command_available"]:
            response_payload["new_setpoint"] = shared_data["current_setpoint"]
            shared_data["new_command_available"] = False

    return jsonify(response_payload)

def start_server_thread() -> threading.Thread:
    """
    Inicia o servidor Flask em uma thread separada (daemon).
    
    Isso permite que o servidor web rode simultaneamente com a interface gráfica Tkinter.
    
    Returns:
        threading.Thread: O objeto da thread iniciada.
    """
    
    print("Servidor Flask rodando em http://0.0.0.0:5000")
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=5000, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    return flask_thread