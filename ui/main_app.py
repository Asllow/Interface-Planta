"""
Aplicação Principal da Interface Gráfica.

Este módulo define a classe raiz (MainApplication) que herda de ctk.CTk.
Ele atua como o container principal para todas as telas (Frames) e gerencia:
1. A inicialização da janela e configurações de tema.
2. A navegação entre telas (Roteamento).
3. O ciclo de vida da aplicação (Inicialização e Encerramento Seguro).
"""

import customtkinter as ctk
import sys
from typing import Dict, Type

# Módulos internos
from core import db_writer
from config import settings

# Importação das telas (Frames)
from ui.frames.live_dashboard_frame import LiveDashboardFrame 
from ui.frames.home_screen_frame import HomeScreenFrame
from ui.frames.experiment_viewer_frame import ExperimentViewerFrame

class MainApplication(ctk.CTk):
    """
    Classe principal da janela da aplicação.
    Gerencia a troca de frames e o encerramento de threads em background.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa a janela principal, configura o tema e instancia todas as telas.
        """

        super().__init__(*args, **kwargs)

        # Configurações Visuais Globais
        ctk.set_appearance_mode(settings.APPEARANCE_MODE)
        ctk.set_default_color_theme(settings.COLOR_THEME)
        self.title(settings.APP_TITLE)
        self.geometry(settings.DEFAULT_WINDOW_SIZE)

        # Container principal que empilha todas as telas (Frames)
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Dicionário para armazenar as instâncias das telas
        self.frames = {}
        
        # Loop para instanciar e registrar todas as telas disponíveis
        # (Adicione novas telas nesta tupla se o projeto crescer)
        for F, key in ( (HomeScreenFrame, "Home"), 
                        (LiveDashboardFrame, "Live"), 
                        (ExperimentViewerFrame, "Experiments")):
            frame = F(container, self)
            self.frames[key] = frame
            # Coloca todos os frames na mesma célula do grid (empilhados)
            frame.grid(row=0, column=0, sticky="nsew")

        # Inicia exibindo a tela Home
        self.show_frame("Home")

        # Intercepta o evento de fechar a janela (X) para garantir shutdown seguro
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_frame(self, page_key: str) -> None:
        """
        Eleva a tela solicitada para o topo da pilha de visualização.
        
        Também gerencia o início/fim dos loops de atualização do gráfico em tempo real
        para economizar recursos quando o usuário não está na tela 'Live'.

        Args:
            page_key (str): A chave identificadora da tela ("Home", "Live", "Experiments").
        """

        # Otimização: Se sair da tela Live, para a animação
        if page_key != "Live":
            self.frames["Live"].stop_loops()

        # Traz o frame desejado para frente
        frame = self.frames[page_key]
        frame.tkraise()

        # Se entrar na tela Live, inicia a animação
        if page_key == "Live":
            self.frames["Live"].start_loops()

    def on_closing(self) -> None:
        """
        Manipulador de evento para o fechamento da janela.
        
        Garante que todas as threads secundárias (DB Writer, Animações) sejam
        notificadas para parar antes de destruir a janela, evitando erros de
        'Thread não finalizada' ou corrupção de dados.
        """

        print("Iniciando desligamento...")

        # 1. Tenta parar os loops da interface (Gráficos)
        try:
            self.frames["Live"].on_closing()
        except Exception as e:
            print(f"Erro ao fechar frame: {e}")

        # 2. Envia sinal de parada para a thread de escrita no banco
        try:
            db_writer.stop_db_writer_thread()
        except Exception as e:
            print(f"Erro ao parar DB Writer: {e}")

        # 3. Aguarda um curto período para processamento pendente e força saída
        print("Aguardando 200ms para tarefas do Tkinter finalizarem...")
        self.after(200, self.perform_shutdown)

    def perform_shutdown(self) -> None:
        """
        Executa a destruição final da janela e encerra o processo Python.
        """

        print("Executando self.destroy() e sys.exit()...")

        try:
            self.destroy()
        except Exception as e:
            print(f"Erro (ignorado) durante self.destroy(): {e}")

        # Encerramento forçado para garantir que threads 'daemon' (Flask) morram
        sys.exit(0)