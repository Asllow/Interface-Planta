"""
Ponto de entrada do Dashboard de Controlo Industrial.

Módulo de inicialização primária responsável pelo arranque sequencial
da camada de persistência (Base de Dados), das threads de rede (Comunicação UDP),
e do motor de renderização gráfica (CustomTkinter).
"""

from core import database
from core import udp_server
from core import db_writer
from ui.main_app import MainApplication

def main() -> None:
    """
    Rotina principal de orquestração do sistema.
    Inicia os subsistemas auxiliares e bloqueia a execução no MainLoop da interface.
    """
    
    database.init_db()
    database.startup_cleanup()

    udp_server.start_network_threads()
    db_writer.start_db_writer_thread()

    app = MainApplication()
    app.mainloop()

if __name__ == "__main__":
    main()