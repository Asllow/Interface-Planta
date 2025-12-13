"""
Tela de Dashboard em Tempo Real (Live Dashboard).

Este módulo implementa a visualização principal do sistema, onde os dados
de telemetria são exibidos graficamente à medida que chegam do microcontrolador.

Funcionalidades principais:
- Exibição de gráficos animados usando Matplotlib + FuncAnimation.
- Consumo da fila de dados (data_queue) em background.
- Envio de comandos de controle (PWM) para a planta.
- Controle manual de gravação (Iniciar/Parar Experimento).
"""

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import os
from typing import Optional, Any

# Módulos internos
import core.database as database
from core.shared_state import data_queue, shared_data, data_lock
from ui.plot_manager import GraphManager, apply_style_from_settings

class LiveDashboardFrame(ctk.CTkFrame):
    """
    Frame responsável pelo dashboard de monitoramento em tempo real.
    
    Gerencia a integração entre o loop de eventos do Tkinter e o loop de
    animação do Matplotlib, garantindo que a interface permaneça responsiva
    enquanto processa dados de alta frequência.
    """

    def __init__(self, master: Any, controller: Any):
        """
        Inicializa os componentes visuais e lógicos do dashboard.

        Args:
            master: Widget pai (Container).
            controller: Controlador principal da aplicação (MainApplication).
        """

        super().__init__(master)
        self.controller = controller

        # --- Estado Interno ---
        self.is_running = False
        self.anim = None
        self._after_id_process_queue = None
        
        self.is_paused = False
        self.is_graph_visible = False

        # --- Layout Principal ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Barra Lateral (Menu de Gráficos)
        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsew") 
        ctk.CTkLabel(self.sidebar_frame, text="Selecionar Gráfico", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Controle e Tensão", command=lambda: self.select_graph('controle_tensao')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Valor ADC", command=lambda: self.select_graph('valor_adc')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Intervalo Amostras", command=lambda: self.select_graph('ciclo')).pack(pady=10, padx=20)

        self.filter_var = ctk.BooleanVar(value=False)
        self.filter_switch = ctk.CTkSwitch(
            self.sidebar_frame, 
            text="Filtro (Média 20)",
            variable=self.filter_var,
            command=self.on_filter_toggle
        )
        self.filter_switch.pack(pady=30, padx=20)

        # 2. Área Central (Gráfico)
        self.main_frame = ctk.CTkFrame(self) 
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Controles sobre o gráfico (Pausar/Salvar)
        self.graph_controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.graph_controls_frame.grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        self.pause_button = ctk.CTkButton(self.graph_controls_frame, text="Pausar", width=100, command=self.toggle_pause)
        self.pause_button.pack(side="right", padx=(5, 0))
        self.save_button = ctk.CTkButton(self.graph_controls_frame, text="Salvar Gráfico", width=120, command=self.save_graph)
        self.save_button.pack(side="right")

        # Inicialização do Matplotlib
        apply_style_from_settings() # Aplica tema Dark/Light global
        self.fig, self.ax = plt.subplots()
        self.plotter = GraphManager(self.fig, self.ax, max_points=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, sticky="nsew")
        self.initial_message_label = ctk.CTkLabel(self.main_frame, text="Selecione um Gráfico", font=ctk.CTkFont(size=24, weight="bold"))
        self.initial_message_label.grid(row=1, column=0)
        self.canvas_widget.grid_remove()

        # 3. Barra de Estatísticas (Valores numéricos)
        self.stats_bar_frame = ctk.CTkFrame(self, height=40) 
        self.stats_bar_frame.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="ew") 
        self.stats_bar_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.label_last_x = ctk.CTkLabel(self.stats_bar_frame, text="Tempo (s): --")
        self.label_last_x.grid(row=0, column=0)
        self.label_last_y = ctk.CTkLabel(self.stats_bar_frame, text="Último Valor: --")
        self.label_last_y.grid(row=0, column=1)
        self.label_avg_y = ctk.CTkLabel(self.stats_bar_frame, text="Média: --")
        self.label_avg_y.grid(row=0, column=2)

        # 4. Barra de Controle Inferior (Envio de PWM)
        self.bottom_bar = ctk.CTkFrame(self, height=50) 
        self.bottom_bar.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(self.bottom_bar, text="Duty Cycle (%)").pack(side="left", padx=10)
        validate_cmd = self.register(self.validate_numeric_input) 
        self.entry_pwm = ctk.CTkEntry(self.bottom_bar, validate="key", validatecommand=(validate_cmd, '%P'))
        self.entry_pwm.pack(side="left", fill="x", expand=True)
        self.entry_pwm.bind("<Return>", self.send_pwm_command)
        self.btn_send = ctk.CTkButton(self.bottom_bar, text="Enviar", width=100, command=self.send_pwm_command)
        self.btn_send.pack(side="left", padx=10)

        # 5. Painel de Controle de Gravação (Sidebar Inferior)
        control_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        control_frame.pack(side="bottom", pady=20, padx=20, fill="x")
        
        self.status_label = ctk.CTkLabel(control_frame, text="Status: AGUARDANDO", text_color="gray", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=(0, 5))

        self.btn_rec = ctk.CTkButton(
            control_frame, 
            text="Iniciar Gravação",
            command=self.toggle_recording,
            fg_color="green", 
            hover_color="darkgreen"
        )
        self.btn_rec.pack(pady=5, fill="x")

        ctk.CTkButton(control_frame, text="Voltar ao Menu",
                        command=lambda: self.controller.show_frame("Home"),
                        fg_color="gray") \
                        .pack(pady=(20, 5), fill="x")

        # Define estado inicial dos botões
        self.update_rec_buttons()

    def start_loops(self) -> None:
        """
        Inicia os loops de processamento e animação.
        Chamado automaticamente quando esta tela é exibida.
        """

        if self.is_running: return 
        print("Iniciando loops do Dashboard Live (UI)...")
        self.is_running = True

        # Atualiza status visual do botão de gravação
        self.update_rec_buttons()

        # Cria a animação se não existir
        if self.anim is None:
            self.anim = animation.FuncAnimation(
                self.fig, 
                self.plotter.animation_update_callback, 
                interval=30, 
                blit=False, 
                cache_frame_data=False
            )

        # Tenta iniciar o timer de eventos do Matplotlib
        try:
            self.anim.event_source.start()
        except Exception:
            pass

        # Inicia o consumo da fila de dados
        self.process_queue()

    def stop_loops(self) -> None:
        """
        Para os loops de animação e processamento.
        Chamado quando o usuário sai desta tela para poupar CPU.
        """

        if not self.is_running: return 
        print("Parando loops do Dashboard Live (UI)...")
        self.is_running = False

        # Pausa a animação sem destruir o objeto
        if self.anim and self.anim.event_source:
            try:
                self.anim.event_source.stop()
            except Exception:
                pass

        # Cancela o agendamento do process_queue
        if self._after_id_process_queue:
            try: self.after_cancel(self._after_id_process_queue)
            except Exception: pass
            self._after_id_process_queue = None

    def on_closing(self) -> None:
        """Chamado pelo MainApplication antes de fechar o programa."""
        self.stop_loops()

    def on_filter_toggle(self):
        """Callback acionado ao clicar no Switch de filtro."""
        is_active = self.filter_var.get()
        if hasattr(self, 'plotter'):
            self.plotter.toggle_filter(is_active)
            self.canvas.draw_idle() # Solicita redesenho

    def toggle_pause(self) -> None:
        """
        Alterna entre Pausar e Retomar a atualização visual do gráfico.
        Nota: O processamento de dados em background continua para não perder histórico.
        """

        self.is_paused = not self.is_paused
        
        if self.anim and self.anim.event_source:
            if self.is_paused:
                self.anim.event_source.stop()
                self.pause_button.configure(text="Retomar")
                print("Gráfico visualmente pausado (Buffer continua recebendo dados).")
            else:
                self.anim.event_source.start()
                self.pause_button.configure(text="Pausar")
                print("Gráfico retomado.")

    def process_queue(self):
        """
        Loop recursivo (via tk.after) que consome dados da fila e atualiza o plotter.
        
        Garante que a GUI não trave ao processar múltiplos pacotes de dados.
        """

        if not self.is_running:
            return #Interrompe a recursão se a tela foi fechada

        try:
            data_processed = False
            # Consome tudo o que estiver disponível na fila (sem bloquear)
            while not data_queue.empty():
                data = data_queue.get_nowait()
                self.plotter.append_plot_data(data)
                data_processed = True

            # Atualiza os números da barra lateral se houver dados novos e não estiver pausado
            if data_processed and not self.is_paused:
                self._update_stats_bar()

        finally:
            # Reagenda a próxima execução para daqui a 30ms
            if self.is_running:
                self._after_id_process_queue = self.after(30, self.process_queue)

    # --- Lógica de Interface e Comandos ---

    def toggle_recording(self) -> None:
        """Alterna o estado de gravação no banco de dados (Liga/Desliga)."""
        if database.is_experiment_running():
            database.close_current_experiment()
        else:
            database.start_new_experiment()
        self.update_rec_buttons()

    def update_rec_buttons(self) -> None:
        """Atualiza a cor e o texto do botão de gravação baseado no estado do DB."""
        if database.is_experiment_running():
            self.btn_rec.configure(text="PARAR Gravação", fg_color="#D9534F", hover_color="#C9302C")
            self.status_label.configure(text="Status: GRAVANDO", text_color="#D9534F")
        else:
            self.btn_rec.configure(text="Iniciar Gravação", fg_color="#5CB85C", hover_color="#4CAE4C")
            self.status_label.configure(text="Status: EM ESPERA", text_color="gray")

    def save_graph(self) -> None:
        """Salva a imagem atual do gráfico em um arquivo PNG na pasta 'images'."""
        try:
            os.makedirs("images", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"grafico_{timestamp}.png"
            full_path = os.path.join("images", filename)
            self.fig.savefig(full_path, dpi=150, bbox_inches='tight')
            print(f"Gráfico salvo com sucesso em: {full_path}")
        except Exception as e:
            print(f"ERRO ao salvar o gráfico: {e}")

    def _update_stats_bar(self) -> None:
        """Busca as estatísticas calculadas pelo Plotter e atualiza os Labels."""
        try:
            stats = self.plotter.get_current_stats()
            if not stats:
                return

            self.label_last_x.configure(text=f"Tempo (s): {stats.get('last_x', '--')}")

            if 'last_y1' in stats:
                # Gráfico combinado (Controle + Tensão)
                self.label_last_y.configure(text=f"Sinal: {stats.get('last_y1', '--')} %")
                self.label_avg_y.configure(text=f"Tensão: {stats.get('last_y2', '--')} mV")
            else:
                #Gráfico simples
                self.label_last_y.configure(text=f"Último Valor: {stats.get('last_y', '--')}")
                self.label_avg_y.configure(text=f"Média: {stats.get('avg_y', '--')}")
        except Exception as e:
            print(f"ERRO em _update_stats_bar: {e}")

    def send_pwm_command(self, event=None) -> None:
        """
        Lê o valor do campo de entrada e envia o comando de setpoint.
        Utiliza locks para thread-safety na atualização da variável compartilhada.
        """

        try:
            value = float(self.entry_pwm.get())
            with data_lock:
                shared_data["current_setpoint"] = value
                shared_data["new_command_available"] = True
            print(f"Comando enviado: {value}")
            self.entry_pwm.delete(0, 'end')
        except ValueError:
            print("Erro: Valor inválido no campo de PWM.")

    def select_graph(self, graph_key: str) -> None:
        """
        Troca o gráfico exibido e exibe o canvas caso esteja oculto.
        
        Args:
            graph_key (str): Identificador do gráfico ('controle_tensao', 'valor_adc', etc).
        """

        if not self.is_graph_visible:
            self.initial_message_label.grid_forget()
            self.canvas_widget.grid(row=1, column=0, sticky="nsew")
            self.is_graph_visible = True
        self.plotter.select_graph(graph_key)
        self.canvas.draw()

    def validate_numeric_input(self, value_if_allowed: str) -> bool:
        """Validador para o campo de entrada (aceita apenas números float)."""

        if value_if_allowed == "" or value_if_allowed == "-":
            return True
        try:
            float(value_if_allowed)
            return True
        except ValueError:
            return False