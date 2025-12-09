from core import database
from core import web_server
from core import db_writer
from ui.main_app import MainApplication

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
    app.mainloop()

    print("Mainloop encerrado.")

if __name__ == "__main__":
    main()