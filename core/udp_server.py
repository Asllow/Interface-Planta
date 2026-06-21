"""
Subsistema de Comunicação UDP de Alta Performance (Serialização Binária).

Este módulo gerencia os túneis de comunicação com o microcontrolador ESP32-S3,
implementando a extração em lote (batching) estrito de amostras empacotadas.
Opera sob a diretriz arquitetural de 1000Hz (1ms), recebendo 5 amostras 
agrupadas em buffers contíguos de 180 bytes.
"""

import socket
import struct
import threading
import time
from datetime import datetime
import queue
from typing import Optional, Dict, Any

import config.settings as settings
import core.database as database
from core.shared_state import data_queue, db_queue, shared_data, data_lock


# --- Parâmetros de Loteamento e Estrutura Binária ---
EXPECTED_BUFFER_SIZE: int = 180
SAMPLES_PER_PACKET: int = 5
BYTES_PER_SAMPLE: int = 36

# Estrutura RX (Telemetria): <I8f (1 uint32_t, 8 floats)
TELEMETRY_STRUCT_FORMAT: str = '<I8f'

# Estrutura TX (Comando): <f (1 float contendo a Tensão Alvo em Volts)
COMMAND_STRUCT_FORMAT: str = '<f'


def _telemetry_receiver_loop() -> None:
    """
    Laço de execução infinito para a recepção passiva de datagramas UDP.
    
    Aplica validação rígida de comprimento de buffer (180 bytes) e executa
    a extração de 5 amostras sequenciais via ponteiros de memória (offset),
    injetando-as nas filas de processamento assíncrono.
    """
    last_batch_time: Optional[datetime] = None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('', settings.UDP_TELEMETRY_PORT))
    except socket.error:
        return

    while True:
        try:
            buffer, _ = sock.recvfrom(512)
            
            # Validação estrita do loteamento exigido pela arquitetura de 1000Hz
            if len(buffer) == EXPECTED_BUFFER_SIZE:
                current_time = datetime.now()
                batch_interval_ms = 0.0

                if last_batch_time is not None:
                    delta = current_time - last_batch_time
                    batch_interval_ms = (delta.total_seconds() * 1000.0) / SAMPLES_PER_PACKET

                last_batch_time = current_time

                for i in range(SAMPLES_PER_PACKET):
                    offset = i * BYTES_PER_SAMPLE
                    unpacked_data = struct.unpack_from(TELEMETRY_STRUCT_FORMAT, buffer, offset)

                    item: Dict[str, Any] = {
                        'timestamp_amostra_ms': unpacked_data[0],
                        'sinal_controle': unpacked_data[1],
                        'tensao_mv': unpacked_data[2],
                        'valor_adc': unpacked_data[3],
                        'tensao_estimada_mv': unpacked_data[4],
                        'erro_obs_mv': unpacked_data[5],
                        'estado_1': unpacked_data[6],
                        'estado_2': unpacked_data[7],
                        'estado_3': unpacked_data[8],
                        'timestamp_recebimento': current_time.isoformat(),
                        'batch_interval_ms': batch_interval_ms
                    }

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

        except struct.error:
            pass
        except Exception:
            break


def _command_sender_loop() -> None:
    """
    Laço de execução contínuo para transmissão ativa de comandos LQR.
    
    Encapsula o setpoint físico (Tensão Alvo em Volts) em binário nativo e
    emite um datagrama restrito de 4 bytes para o microcontrolador.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while True:
        try:
            with data_lock:
                if shared_data["new_command_available"]:
                    payload = struct.pack(COMMAND_STRUCT_FORMAT, shared_data["current_setpoint"])
                    sock.sendto(payload, (settings.ESP_IP, settings.UDP_COMMAND_PORT))
                    shared_data["new_command_available"] = False
                    
            time.sleep(0.01)
            
        except Exception:
            time.sleep(0.1)


def start_network_threads() -> None:
    """
    Orquestração e alocação de threads de rede em modo Daemon.
    """
    receiver_thread = threading.Thread(target=_telemetry_receiver_loop, daemon=True)
    sender_thread = threading.Thread(target=_command_sender_loop, daemon=True)
    
    receiver_thread.start()
    sender_thread.start()