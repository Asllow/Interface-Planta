"""
Estado Compartilhado e Sincronização entre Threads.

Este módulo fornece as estruturas de dados globais destinadas à comunicação
segura entre a thread de receção UDP, a thread da Interface Gráfica (UI)
e a thread de persistência na base de dados (I/O). Implementa o padrão
Produtor-Consumidor através de estruturas thread-safe.
"""

import queue
import threading
from typing import Dict, Any

# --- Filas de Comunicação (Queues) ---

# Fila de visualização alocada para os gráficos em tempo real.
# Capacidade para 5000 amostras (aproximadamente 25 segundos a 200Hz).
# Em caso de saturação (backpressure), novas amostras serão descartadas
# para priorizar a vitalidade e tempo de resposta da UI.
data_queue: queue.Queue = queue.Queue(maxsize=5000)

# Fila de persistência alocada para o subsistema de gravação SQLite.
# Configuração sem limite predefinido para garantir a integridade total
# do registo de dados, mitigando variações na latência de I/O do disco.
db_queue: queue.Queue = queue.Queue()

# --- Variáveis de Controlo e Sincronização ---

# Mutex para assegurar a exclusão mútua nas operações de leitura e escrita
# do dicionário partilhado, prevenindo 'Race Conditions'.
data_lock: threading.Lock = threading.Lock()

# Estrutura de dados partilhada para orquestração de comandos bidirecionais.
shared_data: Dict[str, Any] = {
    "current_setpoint": 0.0,
    "new_command_available": False
}