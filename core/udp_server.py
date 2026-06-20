"""
Subsistema de Comunicação UDP para Telemetria e Controlo.

Este módulo é responsável por instanciar os sockets UDP bidirecionais
para a comunicação com o microcontrolador ESP32-S3 em ambiente de Ponto de Acesso.
Divide-se em duas rotinas assíncronas concorrentes:
1. Receção passiva de datagramas de telemetria em broadcast.
2. Transmissão ativa de datagramas de comando em unicast.
"""

import socket
import json
import threading
import time
from datetime import datetime
import queue
from typing import Optional

import config.settings as settings
import core.database as database
from core.shared_state import data_queue, db_queue, shared_data, data_lock


def _telemetry_receiver_loop() -> None:
    """
    Laço de execução infinito para a receção de pacotes UDP de telemetria.
    
    Efetua o parsing do payload JSON, calcula a latência relativa e injeta
    os registos nas filas de interface e de base de dados.
    """
    last_batch_time: Optional[datetime] = None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # A interface escuta de forma passiva no IP genérico ou no endereço local.
        sock.bind(('', settings.UDP_TELEMETRY_PORT))
    except socket.error as err:
        return

    while True:
        try:
            data, _ = sock.recvfrom(65536)
            if not data:
                continue

            current_time = datetime.now()
            batch_interval_ms = 0.0

            if last_batch_time is not None:
                delta = current_time - last_batch_time
                batch_interval_ms = delta.total_seconds() * 1000.0

            last_batch_time = current_time

            payload_str = data.decode('utf-8')
            payload_str = payload_str.replace(':nan', ':null')
            payload_str = payload_str.replace(':inf', ':null')
            payload_str = payload_str.replace(':-inf', ':null')
            
            data_batch = json.loads(payload_str)

            if isinstance(data_batch, dict):
                data_batch = [data_batch]

            for item in data_batch:
                item['timestamp_recebimento'] = current_time.isoformat()
                item['batch_interval_ms'] = batch_interval_ms

                try:
                    data_queue.put(item, block=False)
                except queue.Full:
                    pass

                if database.is_recording_enabled and database.current_run_id is not None:
                    item['id_experimento'] = database.current_run_id
                    try:
                        db_queue.put(item, block=False)
                    except queue.Full:
                        pass

        except json.JSONDecodeError:
            pass
        except Exception:
            break


def _command_sender_loop() -> None:
    """
    Laço de execução contínuo para transmissão de comandos de controlo.
    
    Verifica a presença de novas diretivas na estrutura partilhada e
    encaminha o novo 'setpoint' para o endereço estático do ESP32 via UDP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while True:
        try:
            with data_lock:
                if shared_data["new_command_available"]:
                    payload = json.dumps({"new_setpoint": shared_data["current_setpoint"]})
                    sock.sendto(payload.encode('utf-8'), (settings.ESP_IP, settings.UDP_COMMAND_PORT))
                    shared_data["new_command_available"] = False
                    
            # Tempo de suspensão nominal para mitigar a exaustão de ciclos de CPU (Tick de 10ms)
            time.sleep(0.01)
            
        except Exception:
            time.sleep(0.1)


def start_network_threads() -> None:
    """
    Inicializa os daemons responsáveis pela comunicação UDP.
    
    As threads são alocadas como 'daemons' para assegurar a finalização
    automática durante o encerramento do processo principal.
    """
    receiver_thread = threading.Thread(target=_telemetry_receiver_loop, daemon=True)
    sender_thread = threading.Thread(target=_command_sender_loop, daemon=True)
    
    receiver_thread.start()
    sender_thread.start()