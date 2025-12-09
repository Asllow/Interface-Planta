# web_server.py
from flask import Flask, request, jsonify
from datetime import datetime
import queue
import threading

# Importa as filas e o estado compartilhado
from shared_state import data_queue, db_queue, shared_data, data_lock

flask_app = Flask(__name__)
last_batch_time = None

@flask_app.route('/data', methods=['POST'])
def handle_data():
    """
    Recebe um lote, calcula o intervalo, distribui para as filas
    e envia de volta o comando de setpoint.
    """
    global last_batch_time

    current_time = datetime.now()
    batch_interval_ms = 0

    if last_batch_time is not None:
        delta = current_time - last_batch_time
        batch_interval_ms = delta.total_seconds() * 1000

    last_batch_time = current_time
    data_batch = request.get_json()

    for item in data_batch:
        item['timestamp_recebimento'] = current_time.isoformat()
        item['batch_interval_ms'] = batch_interval_ms

        try:
            data_queue.put(item, block=False)
            db_queue.put(item, block=False)
        except queue.Full:
            print("Aviso: Uma das filas está cheia, descartando amostra.")
            pass

    # Lógica de resposta
    response_payload = {
        "new_setpoint": None
    }
    with data_lock:
        if shared_data["new_command_available"]:
            response_payload["new_setpoint"] = shared_data["current_setpoint"]
            shared_data["new_command_available"] = False

    return jsonify(response_payload)

def start_server_thread():
    """Inicia o servidor Flask em uma thread daemon."""
    print("Servidor Flask rodando em http://0.0.0.0:5000")
    flask_thread = threading.Thread(
        # use_reloader=False é importante ao rodar em uma thread
        target=lambda: flask_app.run(host='0.0.0.0', port=5000, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    return flask_thread