"""
Subsistema de Comunicação UDP de Alta Performance (Serialização Binária).

Este módulo instancia os sockets UDP bidirecionais para a comunicação com
o microcontrolador ESP32-S3. Implementa o desempacotamento de estruturas 
binárias nativas (C-structs), eliminando a latência e a sobrecarga de 
alocação de memória (Garbage Collection) associadas ao parsing de strings e JSON.
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

# Definição do formato dimensional da estrutura binária proveniente do firmware.
# '<'  : Endianness Little-Endian (Padrão arquitetura Xtensa do ESP32).
# 'I'  : Inteiro sem sinal de 32-bits (4 bytes) destinado ao timestamp.
# '8f' : Vetor contíguo de 8 números de Ponto Flutuante (32 bytes) para telemetria.
# Total do Payload Alocado: 36 bytes absolutos.
TELEMETRY_STRUCT_FORMAT = '<I8f'
TELEMETRY_STRUCT_SIZE = struct.calcsize(TELEMETRY_STRUCT_FORMAT)

# Formato do comando de atuação na malha de controlo (1 Float estrito).
COMMAND_STRUCT_FORMAT = '<f'


def _telemetry_receiver_loop() -> None:
    """
    Laço de execução infinito para a receção passiva de datagramas UDP.
    
    Desempacota a estrutura binária em tempo real (200Hz), reconstrói 
    o mapa de registos analíticos e efetua a injeção não-bloqueante 
    nas filas de orquestração de UI e de persistência I/O.
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
            # Receção do datagrama bruto predefinido.
            data, _ = sock.recvfrom(1024)
            
            # Validação rigorosa de integridade dimensional para mitigação de buffer overflows.
            if len(data) != TELEMETRY_STRUCT_SIZE:
                continue

            # Desempacotamento vetorial binário (O(1)).
            unpacked_data = struct.unpack(TELEMETRY_STRUCT_FORMAT, data)

            current_time = datetime.now()
            batch_interval_ms = 0.0

            if last_batch_time is not None:
                delta = current_time - last_batch_time
                batch_interval_ms = delta.total_seconds() * 1000.0

            last_batch_time = current_time

            # Mapeamento do tuplo extraído para a hierarquia de chaves consumida pelo Dashboard.
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
            # Descarte silencioso por falha de alinhamento binário ou datagrama corrompido.
            pass
        except Exception:
            break


def _command_sender_loop() -> None:
    """
    Laço de execução contínuo para transmissão ativa de diretivas LQR.
    
    Inspeciona mutações na memória partilhada, executa o cast do tipo
    Python para binário nativo e emite o bloco de 4 bytes via Unicast.
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
    Orquestração e alocação de threads em modo Daemon.
    
    Assegura o isolamento de concorrência face à thread gráfica do interpretador
    e garante a libertação automática dos recursos de rede (Sockets) no encerramento.
    """
    receiver_thread = threading.Thread(target=_telemetry_receiver_loop, daemon=True)
    sender_thread = threading.Thread(target=_command_sender_loop, daemon=True)
    
    receiver_thread.start()
    sender_thread.start()