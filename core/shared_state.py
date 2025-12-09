import queue
import threading

data_queue = queue.Queue(maxsize=1000) 

db_queue = queue.Queue(maxsize=1000) 

shared_data = {
    "current_setpoint": 0.0, 
    "new_command_available": False,
}
data_lock = threading.Lock()