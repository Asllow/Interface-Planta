"""
Estado Compartilhado e Sincronização entre Threads.

Este módulo armazena as estruturas de dados globais que permitem a comunicação
segura entre a thread do Servidor Web (que recebe dados), a thread de Interface
(que exibe dados) e a thread de Banco de Dados (que salva dados).

Utiliza o padrão Produtor-Consumidor através de filas (Queues) thread-safe.
"""

import queue
import threading
from typing import Dict, Any

# --- Filas de Comunicação (Queues) ---

# Fila de Visualização:
# Recebe dados do servidor e é consumida pelo gráfico em tempo real.
# Definimos maxsize=1000 para evitar que a memória exploda se a interface
# gráfica travar ou ficar lenta (backpressure). Se encher, dados velhos são descartados.
data_queue: queue.Queue = queue.Queue(maxsize=1000)

# Fila de Persistência:
# Recebe dados do servidor e é consumida pelo 'db_writer'.
# Geralmente não limitamos o tamanho (ou usamos um limite muito alto) pois
# a prioridade é não perder dados de gravação, mesmo que o disco seja lento.
db_queue: queue.Queue = queue.Queue()

# --- Variáveis de Controle e Comandos ---

# Lock para garantir acesso exclusivo ao dicionário 'shared_data'.
# Essencial para evitar 'Race Conditions' quando o usuário altera o Setpoint na UI
# ao mesmo tempo que o servidor lê esse valor para enviar ao ESP32.
data_lock: threading.Lock = threading.Lock()

# Dicionário compartilhado para troca de estados e comandos.
shared_data: Dict[str, Any] = {
    "current_setpoint": 0.0,      # Valor atual do PWM (0-100) definido pelo usuário
    "new_command_available": False # Flag que indica se há um novo comando pendente
}