# live_dashboard_frame.py
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import os

import core.database as database
from core.shared_state import data_queue, shared_data, data_lock
from ui.plot_manager import GraphManager

class LiveDashboardFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
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
        ctk.CTkLabel(self.sidebar_frame, text="Selecionar Gráfico", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Controle e Tensão", command=lambda: self.select_graph('controle_tensao')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Valor ADC", command=lambda: self.select_graph('valor_adc')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Intervalo Amostras", command=lambda: self.select_graph('ciclo')).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar_frame, text="Intervalo de Rede", command=lambda: self.select_graph('batch_interval')).pack(pady=10, padx=20)

        self.main_frame = ctk.CTkFrame(self) 
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.graph_controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.graph_controls_frame.grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        self.pause_button = ctk.CTkButton(self.graph_controls_frame, text="Pausar", width=100, command=self.toggle_pause)
        self.pause_button.pack(side="right", padx=(5, 0))
        self.save_button = ctk.CTkButton(self.graph_controls_frame, text="Salvar Gráfico", width=120, command=self.save_graph)
        self.save_button.pack(side="right")

        plt.style.use('seaborn-v0_8-whitegrid')
        self.fig, self.ax = plt.subplots()
        self.plotter = GraphManager(self.fig, self.ax, max_points=100)
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
        ctk.CTkLabel(self.bottom_bar, text="Duty Cycle (%)").pack(side="left", padx=10)
        validate_cmd = self.register(self.validate_numeric_input) 
        self.entry_pwm = ctk.CTkEntry(self.bottom_bar, validate="key", validatecommand=(validate_cmd, '%P'))
        self.entry_pwm.pack(side="left", fill="x", expand=True)
        self.entry_pwm.bind("<Return>", self.send_pwm_command)
        self.btn_send = ctk.CTkButton(self.bottom_bar, text="Enviar", width=100, command=self.send_pwm_command)
        self.btn_send.pack(side="left", padx=10)

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

        self.update_rec_buttons()

    def toggle_recording(self):
        if database.is_experiment_running():
            database.close_current_experiment()
        else:
            database.start_new_experiment()
        self.update_rec_buttons()

    def update_rec_buttons(self):
        if database.is_experiment_running():
            self.btn_rec.configure(text="PARAR Gravação", fg_color="#D9534F", hover_color="#C9302C")
            self.status_label.configure(text="Status: GRAVANDO", text_color="#D9534F")
        else:
            self.btn_rec.configure(text="Iniciar Gravação", fg_color="#5CB85C", hover_color="#4CAE4C")
            self.status_label.configure(text="Status: EM ESPERA", text_color="gray")

    def start_loops(self):
        if self.is_running: return 
        print("Iniciando loops do Dashboard Live (UI)...")
        self.is_running = True
        self.update_rec_buttons()
        self.anim = animation.FuncAnimation(self.fig, self.plotter.animation_update_callback, interval=30, blit=False, cache_frame_data=False)
        self.process_queue()

    def stop_loops(self):
        if not self.is_running: return 
        print("Parando loops do Dashboard Live (UI)...")
        self.is_running = False

        if self.anim:
            try:
                if self.anim.event_source:
                    self.anim.event_source.stop()
            except Exception:
                pass
            self.anim = None

        if self._after_id_process_queue:
            try: self.after_cancel(self._after_id_process_queue)
            except Exception: pass
            self._after_id_process_queue = None

    def on_closing(self):
        self.stop_loops()
    
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.anim.pause()
            self.pause_button.configure(text="Retomar")
            print("Gráfico pausado.")
        else:
            self.anim.resume()
            self.pause_button.configure(text="Pausar")
            print("Gráfico retomado.")

    def save_graph(self):
        try:
            os.makedirs("images", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"grafico_{timestamp}.png"
            full_path = os.path.join("images", filename)
            self.fig.savefig(full_path, dpi=150, bbox_inches='tight')
            print(f"Gráfico salvo com sucesso em: {full_path}")
        except Exception as e:
            print(f"ERRO ao salvar o gráfico: {e}")

    def _update_stats_bar(self):
        try:
            stats = self.plotter.get_current_stats()
            if not stats:
                return

            self.label_last_x.configure(text=f"Tempo (s): {stats.get('last_x', '--')}")

            if 'last_y1' in stats:
                self.label_last_y.configure(text=f"Sinal: {stats.get('last_y1', '--')} %")
                self.label_avg_y.configure(text=f"Tensão: {stats.get('last_y2', '--')} mV")
            else:
                # É um gráfico simples
                self.label_last_y.configure(text=f"Último Valor: {stats.get('last_y', '--')}")
                self.label_avg_y.configure(text=f"Média: {stats.get('avg_y', '--')}")
        except Exception as e:
            print(f"ERRO em _update_stats_bar: {e}")

    def send_pwm_command(self, event=None):
        try:
            value = float(self.entry_pwm.get())
            with data_lock:
                shared_data["current_setpoint"] = value
                shared_data["new_command_available"] = True
            print(f"Comando enviado: {value}")
            self.entry_pwm.delete(0, 'end')
        except ValueError:
            print("Erro: Valor inválido no campo de PWM.")

    def select_graph(self, graph_key):
        if not self.is_graph_visible:
            self.initial_message_label.grid_forget()
            self.canvas_widget.grid(row=1, column=0, sticky="nsew")
            self.is_graph_visible = True
        self.plotter.select_graph(graph_key)
        self.canvas.draw()

    def process_queue(self):
        if not self.is_running:
            print("Loop 'process_queue' interrompido.")
            return
        try:
            data_processed = False
            while not data_queue.empty():
                data = data_queue.get_nowait()
                self.plotter.append_plot_data(data)
                data_processed = True

            if data_processed:
                self._update_stats_bar()
                
        finally:
            if self.is_running:
                self.after_id_process_queue = self.after(30, self.process_queue)
    
    def validate_numeric_input(self, value_if_allowed):
        if value_if_allowed == "" or value_if_allowed == "-":
            return True
        try:
            float(value_if_allowed)
            return True
        except ValueError:
            return False