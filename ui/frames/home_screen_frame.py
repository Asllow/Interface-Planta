"""
Tela Inicial (Home Screen).

Este módulo define a interface de boas-vindas do aplicativo, servindo como
um menu central de navegação para as outras funcionalidades (Live Dashboard,
Visualizador de Experimentos) e fornecendo um botão de saída rápida.
"""

import customtkinter as ctk
from typing import Any

class HomeScreenFrame(ctk.CTkFrame):
    """
    Frame que representa a tela inicial do dashboard.
    Contém botões grandes para fácil navegação entre os módulos do sistema.
    """
    
    def __init__(self, master: Any, controller: Any):
        """
        Inicializa a tela inicial.

        Args:
            master: O widget pai (geralmente o container principal).
            controller: A instância da aplicação principal (MainApplication)
                        que permite a troca de telas via método 'show_frame'.
        """

        super().__init__(master)
        self.controller = controller

        # Configuração do grid para centralizar o conteúdo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Container transparente para agrupar os botões no centro
        button_container = ctk.CTkFrame(self, fg_color="transparent")
        button_container.grid(row=0, column=0, sticky="nsew", padx=50, pady=50, in_=self) 

        # Configuração das colunas do container para espaçamento uniforme
        button_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")
        button_container.grid_rowconfigure(0, weight=1)

        # --- Botões de Navegação ---

        # Botão para o Dashboard em Tempo Real
        btn_live = ctk.CTkButton(   button_container,
                                    text="Dashboard (Tempo Real)",
                                    height=60,
                                    font=ctk.CTkFont(size=14, weight="bold"),
                                    command=lambda: controller.show_frame("Live"))
        btn_live.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        # Botão Central de Saída (X) com destaque vermelho
        btn_exit = ctk.CTkButton(   button_container,
                                    text="X", width=60, height=60, corner_radius=30,
                                    font=ctk.CTkFont(size=20, weight="bold"),
                                    fg_color="#D9534F", hover_color="#C9302C",
                                    command=controller.on_closing)
        btn_exit.grid(row=0, column=1, padx=20, pady=20, sticky="") 

        # Botão para o Histórico de Experimentos
        btn_experiments = ctk.CTkButton(    button_container,
                                            text="Ver Experimentos",
                                            height=60,
                                            font=ctk.CTkFont(size=14, weight="bold"),
                                            command=lambda: controller.show_frame("Experiments"))
        btn_experiments.grid(row=0, column=2, padx=20, pady=20, sticky="ew")