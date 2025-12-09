# main.py
import database
import web_server
import db_writer
from main_app import MainApplication
# import sys  <-- REMOVIDO DAQUI

def main():
    
    print("Inicializando o banco de dados...")
    database.init_db()
    
    print("Limpando experimentos antigos...")
    database.startup_cleanup()
    
    print("Iniciando serviços de background...")
    web_server.start_server_thread()
    db_writer.start_db_writer_thread()
    
    print("Iniciando Roteador Principal...")
    app = MainApplication()
    app.mainloop() # Esta linha agora será interrompida por sys.exit()

    # O 'sys.exit(0)' foi REMOVIDO daqui.
    print("Mainloop encerrado.")
    
if __name__ == "__main__":
    main()