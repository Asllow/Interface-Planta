"""
Módulo de Visualização de Histórico (Experiment Viewer).

Gere a interface gráfica destinada à análise assíncrona de dados persistidos.
Permite o carregamento de matrizes de telemetria de experiências passadas,
renderização estática de gráficos vetoriais (Sinal vs. Tensão) e exportação
para formatos de integração externa (CSV, TXT, NumPy).
"""

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import messagebox, filedialog as fd
import os
from typing import Any

import core.database as database
import core.data_exporter as data_exporter
from ui.plot_manager import apply_style_from_settings


class ExperimentViewerFrame(ctk.CTkFrame):
    """
    Componente estrutural para análise pós-operação.
    
    Orquestra a listagem I/O de registos consolidados e a instanciação
    de contextos estáticos do motor Matplotlib.
    """

    def __init__(self, master: Any, controller: Any):
        """
        Alocação estática dos componentes do visualizador.

        Args:
            master (Any): Componente contentor de ordem superior.
            controller (Any): Orquestrador de transição de domínios (MainApp).
        """
        super().__init__(master)
        self.controller = controller

        self.current_loaded_data = None
        self.current_loaded_exp_id = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1)

        # --- 1. Barra de Acesso Rápido (Top Bar) ---
        top_bar = ctk.CTkFrame(self, height=50)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(top_bar, text="Análise de Telemetria Consolidada", font=ctk.CTkFont(size=18, weight="bold")) \
            .pack(side="left", padx=20)
        ctk.CTkButton(top_bar, text="Retornar à Raiz", command=lambda: self.controller.show_frame("Home")) \
            .pack(side="right", padx=20)
        ctk.CTkButton(top_bar, text="Sincronizar Registo I/O", command=self.populate_experiment_list) \
            .pack(side="right", padx=5)

        # --- 2. Painel Lateral de Navegação de Dados ---
        sidebar_container = ctk.CTkFrame(self, fg_color="transparent")
        sidebar_container.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
        
        sidebar_container.grid_rowconfigure(0, weight=1)
        sidebar_container.grid_columnconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(sidebar_container, label_text="Experimentos Indexados")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew")

        # --- 3. Viewport Gráfico Central ---
        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
        self.graph_frame.grid_rowconfigure(1, weight=1)
        self.graph_frame.grid_columnconfigure(0, weight=1)

        apply_style_from_settings()

        self.fig, self.ax = plt.subplots()
        self.ax2 = None
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        canvas_widget = self.canvas.get_tk_widget()

        canvas_widget.configure(highlightthickness=0, bd=0)
        canvas_widget.grid(row=1, column=0, sticky="nsew")

        toolbar_frame = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        if ctk.get_appearance_mode() == "Dark":
            toolbar_color = "#909090" 
            toolbar.config(background=toolbar_color, highlightthickness=0, bd=0)

            for widget in toolbar.winfo_children():
                widget.config(background=toolbar_color, highlightthickness=0, bd=0)

        # --- 4. Contentor de Comandos Estruturais ---
        self.buttons_container = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        self.buttons_container.grid(row=2, column=0, pady=(10, 5), sticky="ew")
        self.buttons_container.grid_columnconfigure(0, weight=1)
        self.buttons_container.grid_columnconfigure(1, weight=1)

        self.export_button = ctk.CTkButton(self.buttons_container, 
                                           text="Exportar Matriz de Dados",
                                           command=self.on_export_pressed,
                                           state="disabled")
        self.export_button.grid(row=0, column=0, padx=5, sticky="e") 

        self.delete_button = ctk.CTkButton(self.buttons_container,
                                           text="Expurgar Registo",
                                           command=self.delete_current_experiment,
                                           state="disabled",
                                           fg_color="#D9534F", hover_color="#C9302C")
        self.delete_button.grid(row=0, column=1, padx=5, sticky="w") 

        self.populate_experiment_list()

    def populate_experiment_list(self) -> None:
        """
        Executa a varredura do SQLite e instancia os nós de interface
        para cada matriz de dados consolidada.
        """
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        experiments = database.get_completed_experiments()

        if not experiments:
            ctk.CTkLabel(self.scroll_frame, text="Nenhum registo persistido foi encontrado.") \
                .pack(pady=10)
            return

        for exp in experiments:
            text =  f"{exp['nome']}\n" \
                    f"Cronologia: {exp['inicio_str']} -> {exp['fim_str']}\n" \
                    f"Intervalo Total: {exp['duracao_str']}"
            
            btn = ctk.CTkButton(self.scroll_frame, 
                                text=text, 
                                anchor="w",
                                command=lambda e=exp['id']: self.load_experiment_data(e))
            btn.pack(pady=5, padx=5, fill="x")

    def load_experiment_data(self, exp_id: int) -> None:
        """
        Executa a extração em lote da base de dados e gera o mapa vetorial estático.

        Args:
            exp_id (int): Identificador primário da sessão de teste.
        """
        self.current_loaded_data = None
        self.current_loaded_exp_id = None
        self.export_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")

        telemetry_data = database.get_telemetry_for_experiment(exp_id)

        self.ax.clear()
        if self.ax2:
            self.ax2.remove()
            self.ax2 = None

        if not telemetry_data:
            self.ax.set_title(f"Sessão #{exp_id} - Matriz Vazia")
            self.canvas.draw()
            return

        try:
            self.current_loaded_data = telemetry_data
            self.current_loaded_exp_id = exp_id
            self.export_button.configure(state="normal")
            self.delete_button.configure(state="normal")

            start_time_ms = telemetry_data[0]['timestamp_amostra_ms']

            time_sec = [(d['timestamp_amostra_ms'] - start_time_ms) / 1000.0 for d in telemetry_data]
            sinal_controle = [d.get('sinal_controle', 0.0) for d in telemetry_data]
            tensao_mv = [d.get('tensao_mv', 0.0) for d in telemetry_data]

            self.ax.set_title(f"Análise Consolidada - Sessão #{exp_id}")
            self.ax.set_xlabel("Cronologia Relativa (s)")

            self.ax.plot(time_sec, sinal_controle, color='tab:blue', marker='o', markersize=2, linestyle='-', label='Sinal de Controlo LQR (%)')
            self.ax.set_ylabel('Sinal LQR (%)', color='tab:blue')
            self.ax.set_ylim(0, 100)
            self.ax.tick_params(axis='y', labelcolor='tab:blue')
            self.ax.grid(True, axis='y', linestyle='--', color='tab:blue', alpha=0.5)

            self.ax2 = self.ax.twinx()
            self.ax2.plot(time_sec, tensao_mv, color='tab:red', marker='x', markersize=2, linestyle='-', label='Tensão Real (mV)')

            self.ax2.set_ylabel('Potencial (mV)', color='tab:red')
            self.ax2.set_ylim(0, 3300)
            self.ax2.tick_params(axis='y', labelcolor='tab:red')
            self.ax2.grid(True, axis='y', linestyle=':', color='tab:red', alpha=0.5)

            lines1, labels1 = self.ax.get_legend_handles_labels()
            lines2, labels2 = self.ax2.get_legend_handles_labels()
            self.ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

            self.fig.tight_layout()
            self.canvas.draw()
        except Exception:
            self.ax.clear()
            self.ax.set_title(f"Erro de processamento vetorial - Sessão #{exp_id}")
            self.canvas.draw()

    def on_export_pressed(self) -> None:
        """
        Gere a ponte de diálogo de sistema operativo e aciona o módulo de 
        desserialização em formatos standard de processamento (CSV, TXT, NPY).
        """
        if not self.current_loaded_data:
            return

        file_types = [
            ('Vetor Separado por Vírgulas (CSV)', '*.csv'),
            ('Matriz de Texto (Tabulação)', '*.txt'),
            ('Objeto Binário NumPy', '*.npy'),
            ('Todos os arquivos', '*.*')
        ]

        default_name = f"sessao_telemetria_{self.current_loaded_exp_id}.csv"

        filepath = fd.asksaveasfilename(
            title="Exportar Matriz Consolidada",
            initialfile=default_name,
            filetypes=file_types,
            defaultextension=".csv"
        )

        if not filepath:
            return

        _base, ext = os.path.splitext(filepath)
        ext = ext.lower()

        data_to_export = self.current_loaded_data

        try:
            if ext == '.csv':
                data_exporter.export_to_csv(data_to_export, filepath)
            elif ext == '.txt':
                data_exporter.export_to_txt(data_to_export, filepath)
            elif ext == '.npy':
                data_exporter.export_to_npy(data_to_export, filepath)
            else:
                data_exporter.export_to_csv(data_to_export, filepath)
        except Exception:
            pass

    def delete_current_experiment(self) -> None:
        """
        Emite rotina de destruição de referências SQL e atualiza a view.
        Protegido por confirmação estrita do operador.
        """
        if not self.current_loaded_exp_id:
            return

        confirm = messagebox.askyesno(
            "Verificação de Integridade", 
            f"Confirma o expurgo definitivo dos dados da Sessão #{self.current_loaded_exp_id}?\nNão existe reversão para este comando I/O."
        )

        if confirm:
            success = database.delete_experiment(self.current_loaded_exp_id)

            if success:
                self.current_loaded_exp_id = None
                self.current_loaded_data = None
                self.ax.clear()
                if self.ax2: 
                    self.ax2.remove()
                    self.ax2 = None
                self.ax.set_title("Registo Expurgado com Sucesso")
                self.canvas.draw()

                self.export_button.configure(state="disabled")
                self.delete_button.configure(state="disabled")

                self.populate_experiment_list()
            else:
                messagebox.showerror("Falha Operacional", "Falha de transação na exclusão do registo SQL.")