# shared_state.py
import queue
import threading

# Fila para a interface gráfica (rápida)
# Adicionei um maxsize para evitar consumo ilimitado de memória se a GUI travar
data_queue = queue.Queue(maxsize=1000) 

# Fila para o banco de dados (pode ser lenta)
db_queue = queue.Queue(maxsize=1000) 

# Dados compartilhados entre o Flask (escrita) e a App (leitura)
shared_data = {
    "current_setpoint": 0.0, 
    "new_command_available": False,
}
data_lock = threading.Lock()