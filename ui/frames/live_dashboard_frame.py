"""
Módulo de Visualização em Tempo Real (HMI).

Supervisiona a integração de threads paralelas e a orquestração de 
eventos de renderização gráfica acelerada por software (Blitting).
Gere os túneis bidirecionais de sinalização com o firmware.
"""

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import os
from typing import Any

import core.database as database
from core.shared_state import data_queue, shared_data, data_lock
from ui.plot_manager import GraphManager, apply_style_from_settings


class LiveDashboardFrame(ctk.CTkFrame):
    """
    Controlador central da interface de monitorização dinâmica.
    """

    def __init__(self, master: Any, controller: Any):
        super().__init__(master)
        self.controller = controller

        self.is_running = False
        self.anim = None
        self._after_id_process_queue = None
        self.is_paused = False
        self.is_graph_visible = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsew") 
        
        ctk.CTkLabel(self.sidebar_frame, text="Gráficos", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Controle e Tensão", command=lambda: self.select_graph('controle_tensao')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Valor ADC", command=lambda: self.select_graph('valor_adc')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Erro do Observador", command=lambda: self.select_graph('erro_observador'), fg_color="#8E44AD", hover_color="#732D91").pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Tempo de Ciclo", command=lambda: self.select_graph('ciclo')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Estados do Sistema", command=lambda: self.select_graph('estados_sistema'), fg_color="#2E86C1", hover_color="#1B4F72").pack(pady=10, padx=20)

        self.main_frame = ctk.CTkFrame(self) 
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.graph_controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.graph_controls_frame.grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        self.pause_button = ctk.CTkButton(self.graph_controls_frame, text="Pausar Gráfico", width=100, command=self.toggle_pause)
        self.pause_button.pack(side="right", padx=(5, 0))
        self.save_button = ctk.CTkButton(self.graph_controls_frame, text="Salvar Gráfico", width=120, command=self.save_graph)
        self.save_button.pack(side="right")

        apply_style_from_settings()
        self.fig, self.ax = plt.subplots()
        # Inicializado para 3000 pontos (3 segundos de histórico visível a 1000Hz)
        self.plotter = GraphManager(self.fig, self.ax, max_points=3000)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, sticky="nsew")
        
        self.initial_message_label = ctk.CTkLabel(self.main_frame, text="Selecione um Gráfico", font=ctk.CTkFont(size=24, weight="bold"))
        self.initial_message_label.grid(row=1, column=0)
        self.canvas_widget.grid_remove()

        self.stats_bar_frame = ctk.CTkFrame(self, height=40) 
        self.stats_bar_frame.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="ew") 
        self.stats_bar_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.label_last_x = ctk.CTkLabel(self.stats_bar_frame, text="Tempo (s): --")
        self.label_last_x.grid(row=0, column=0)
        self.label_last_y = ctk.CTkLabel(self.stats_bar_frame, text="Último Valor: --")
        self.label_last_y.grid(row=0, column=1)
        self.label_avg_y = ctk.CTkLabel(self.stats_bar_frame, text="Média: --")
        self.label_avg_y.grid(row=0, column=2)

        self.bottom_bar = ctk.CTkFrame(self, height=50) 
        self.bottom_bar.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(self.bottom_bar, text="Referência (Setpoint):").pack(side="left", padx=10)
        validate_cmd = self.register(self.validate_numeric_input) 
        self.entry_pwm = ctk.CTkEntry(self.bottom_bar, validate="key", validatecommand=(validate_cmd, '%P'))
        self.entry_pwm.pack(side="left", fill="x", expand=True)
        self.entry_pwm.bind("<Return>", self.send_pwm_command)
        self.btn_send = ctk.CTkButton(self.bottom_bar, text="Enviar Comando", width=120, command=self.send_pwm_command)
        self.btn_send.pack(side="left", padx=10)

        control_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        control_frame.pack(side="bottom", pady=20, padx=20, fill="x")
        
        self.status_label = ctk.CTkLabel(control_frame, text="Status: PARADO", text_color="gray", font=("Arial", 12, "bold"))
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

        self.update_rec_buttons()

    def start_loops(self) -> None:
        """Inicializa os motores assíncronos e o relógio vetorial (33ms)."""
        if self.is_running: return 
        self.is_running = True
        self.update_rec_buttons()

        if self.anim is None:
            self.anim = animation.FuncAnimation(
                self.fig, 
                self.plotter.animation_update_callback, 
                interval=33, 
                blit=True, 
                cache_frame_data=False
            )

        try:
            self.anim.event_source.start()
        except Exception:
            pass

        self.process_queue()

    def stop_loops(self) -> None:
        """Suspende a execução de processamento da tela atual."""
        if not self.is_running: return 
        self.is_running = False

        if self.anim and self.anim.event_source:
            try:
                self.anim.event_source.stop()
            except Exception:
                pass

        if self._after_id_process_queue:
            try: self.after_cancel(self._after_id_process_queue)
            except Exception: pass
            self._after_id_process_queue = None

    def on_closing(self) -> None:
        self.stop_loops()

    def toggle_pause(self) -> None:
        """Congela a atualização do gráfico sem perder a coleta de dados de fundo."""
        self.is_paused = not self.is_paused
        
        if self.anim and self.anim.event_source:
            if self.is_paused:
                self.anim.event_source.stop()
                self.pause_button.configure(text="Retomar Gráfico")
            else:
                self.anim.event_source.start()
                self.pause_button.configure(text="Pausar Gráfico")

    def process_queue(self) -> None:
        """Extrai blocos de telemetria da fila garantindo integridade de frame."""
        if not self.is_running:
            return

        try:
            data_processed = False
            while not data_queue.empty():
                data = data_queue.get_nowait()
                self.plotter.append_plot_data(data)
                data_processed = True

            if data_processed and not self.is_paused:
                self._update_stats_bar()

        finally:
            if self.is_running:
                self._after_id_process_queue = self.after(33, self.process_queue)

    def toggle_recording(self) -> None:
        if database.is_experiment_running():
            database.close_current_experiment()
        else:
            database.start_new_experiment()
        self.update_rec_buttons()

    def update_rec_buttons(self) -> None:
        if database.is_experiment_running():
            self.btn_rec.configure(text="Parar Gravação", fg_color="#D9534F", hover_color="#C9302C")
            self.status_label.configure(text="Status: GRAVANDO", text_color="#D9534F")
        else:
            self.btn_rec.configure(text="Iniciar Gravação", fg_color="#5CB85C", hover_color="#4CAE4C")
            self.status_label.configure(text="Status: PARADO", text_color="gray")

    def save_graph(self) -> None:
        try:
            os.makedirs("images", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"grafico_{timestamp}.png"
            full_path = os.path.join("images", filename)
            self.fig.savefig(full_path, dpi=150, bbox_inches='tight')
        except Exception:
            pass

    def _update_stats_bar(self) -> None:
        try:
            stats = self.plotter.get_current_stats()
            if not stats:
                return

            self.label_last_x.configure(text=f"Tempo (s): {stats.get('last_x', '--')}")

            if 'last_y1' in stats:
                self.label_last_y.configure(text=f"Controle: {stats.get('last_y1', '--')} %")
                self.label_avg_y.configure(text=f"Tensão: {stats.get('last_y2', '--')} mV")
            elif self.plotter.current_graph == 'erro_observador':
                self.label_last_y.configure(text=f"Erro Inst.: {stats.get('last_y', '--')} mV")
                self.label_avg_y.configure(text=f"Média: {stats.get('avg_y', '--')}")
            else:
                self.label_last_y.configure(text=f"Último Valor: {stats.get('last_y', '--')}")
                self.label_avg_y.configure(text=f"Média: {stats.get('avg_y', '--')}")
        except Exception:
            pass

    def send_pwm_command(self, event=None) -> None:
        try:
            value = float(self.entry_pwm.get())
            with data_lock:
                shared_data["current_setpoint"] = value
                shared_data["new_command_available"] = True
            self.entry_pwm.delete(0, 'end')
        except ValueError:
            pass

    def select_graph(self, graph_key: str) -> None:
        if not self.is_graph_visible:
            self.initial_message_label.grid_forget()
            self.canvas_widget.grid(row=1, column=0, sticky="nsew")
            self.is_graph_visible = True
            
        self.plotter.select_graph(graph_key)
        self.canvas.draw()

    def validate_numeric_input(self, value_if_allowed: str) -> bool:
        if value_if_allowed == "" or value_if_allowed == "-":
            return True
        try:
            float(value_if_allowed)
            return True
        except ValueError:
            return False