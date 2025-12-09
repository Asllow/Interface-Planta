import customtkinter as ctk
import core.database as database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import messagebox

import os
from tkinter import filedialog as fd
import core.data_exporter as data_exporter

class ExperimentViewerFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.current_loaded_data = None
        self.current_loaded_exp_id = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self, height=50)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(top_bar, text="Visualizador de Experimentos", font=ctk.CTkFont(size=18, weight="bold")) \
            .pack(side="left", padx=20)
        ctk.CTkButton(  top_bar, text="Voltar ao Menu", 
                        command=lambda: self.controller.show_frame("Home")) \
            .pack(side="right", padx=20)
        ctk.CTkButton(  top_bar, text="Recarregar Lista", 
                        command=self.populate_experiment_list) \
            .pack(side="right", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Experimentos Concluídos")
        self.scroll_frame.grid( row=1, column=0, sticky="nsew", 
                                padx=(10, 5), pady=(0, 10))

        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.grid(  row=1, column=1, sticky="nsew", 
                                padx=(5, 10), pady=(0, 10))

        self.graph_frame.grid_rowconfigure(1, weight=1)
        self.graph_frame.grid_columnconfigure(0, weight=1)
        plt.style.use('seaborn-v0_8-whitegrid')
        self.fig, self.ax = plt.subplots()
        self.ax2 = None
        self.fig.set_facecolor("#f0f0f0") 
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)

        toolbar_frame = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        self.buttons_container = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        self.buttons_container.grid(row=2, column=0, pady=(10, 5), sticky="ew")

        self.buttons_container.grid_columnconfigure(0, weight=1)
        self.buttons_container.grid_columnconfigure(1, weight=1)

        self.export_button = ctk.CTkButton( self.buttons_container, 
                                            text="Exportar Experimento",
                                            command=self.on_export_pressed,
                                            state="disabled")
        self.export_button.grid(row=0, column=0, padx=5, sticky="e") 

        self.delete_button = ctk.CTkButton(
            self.buttons_container,
            text="Excluir Experimento",
            command=self.delete_current_experiment,
            state="disabled",
            fg_color="#D9534F", hover_color="#C9302C"
        )
        self.delete_button.grid(row=0, column=1, padx=5, sticky="w") 

        self.populate_experiment_list()

    def populate_experiment_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        experiments = database.get_completed_experiments()

        if not experiments:
            ctk.CTkLabel(self.scroll_frame, text="Nenhum experimento concluído encontrado.") \
                .pack(pady=10)
            return

        for exp in experiments:
            text =  f"{exp['nome']}\n" \
                    f"Início: {exp['inicio_str']} (Fim: {exp['fim_str']})\n" \
                    f"Duração: {exp['duracao_str']}"
            
            btn = ctk.CTkButton(self.scroll_frame, 
                                text=text, 
                                anchor="w",
                                command=lambda e=exp['id']: self.load_experiment_data(e))
            btn.pack(pady=5, padx=5, fill="x")

    def load_experiment_data(self, exp_id):
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
            self.ax.set_title(f"Experimento #{exp_id} - Sem Dados")
            self.canvas.draw()
            return

        try:
            self.current_loaded_data = telemetry_data
            self.current_loaded_exp_id = exp_id
            self.export_button.configure(state="normal")
            self.delete_button.configure(state="normal")

            start_time_ms = telemetry_data[0]['timestamp_amostra_ms']

            time_sec = [(d['timestamp_amostra_ms'] - start_time_ms) / 1000.0 for d in telemetry_data]
            sinal_controle = [d.get('sinal_controle', 0) for d in telemetry_data]
            tensao_mv = [d.get('tensao_mv', 0) for d in telemetry_data]

            self.ax.set_title(f"Experimento #{exp_id} - Controle e Tensão")
            self.ax.set_xlabel("Tempo (s) desde o início do experimento")

            self.ax.plot(time_sec, sinal_controle, color='tab:blue', marker='o', markersize=2, linestyle='-', label='Sinal de Controle (%)')
            self.ax.set_ylabel('Sinal de Controle (%)', color='tab:blue')
            self.ax.set_ylim(0, 100)
            self.ax.tick_params(axis='y', labelcolor='tab:blue')
            self.ax.grid(True, axis='y', linestyle='--', color='tab:blue', alpha=0.5)

            self.ax2 = self.ax.twinx()
            self.ax2.plot(time_sec, tensao_mv, color='tab:red', marker='x', markersize=2, linestyle='--', label='Tensão (mV)')
            self.ax2.set_ylabel('Tensão (mV)', color='tab:red')
            self.ax2.set_ylim(0, 3300)
            self.ax2.tick_params(axis='y', labelcolor='tab:red')
            self.ax2.grid(True, axis='y', linestyle=':', color='tab:red', alpha=0.5)

            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(f"Erro ao processar dados do gráfico: {e}")
            self.ax.clear()
            self.ax.set_title(f"Experimento #{exp_id} - Erro ao carregar dados")
            self.canvas.draw()

    def on_export_pressed(self):
        if not self.current_loaded_data:
            print("Nenhum dado carregado para exportar.")
            return

        file_types = [
            ('Arquivo CSV', '*.csv'),
            ('Arquivo de Texto (Tabulado)', '*.txt'),
            ('Arquivo NumPy', '*.npy'),
            ('Todos os arquivos', '*.*')
        ]

        default_name = f"experimento_{self.current_loaded_exp_id}.csv"

        filepath = fd.asksaveasfilename(
            title="Salvar Experimento Como...",
            initialfile=default_name,
            filetypes=file_types,
            defaultextension=".csv"
        )

        if not filepath:
            print("Exportação cancelada pelo usuário.")
            return

        _base, ext = os.path.splitext(filepath)
        ext = ext.lower()

        try:
            if ext == '.csv':
                data_exporter.export_to_csv(self.current_loaded_data, filepath)
            elif ext == '.txt':
                data_exporter.export_to_txt(self.current_loaded_data, filepath)
            elif ext == '.npy':
                data_exporter.export_to_npy(self.current_loaded_data, filepath)
            else:
                print(f"Extensão desconhecida: {ext}. Salvando como CSV por padrão.")
                data_exporter.export_to_csv(self.current_loaded_data, filepath)
            print(f"Sucesso! Experimento salvo em: {filepath}")
        except Exception as e:
            print(f"Falha na exportação: {e}")

    def delete_current_experiment(self):
        if not self.current_loaded_exp_id:
            return

        confirm = messagebox.askyesno(
            "Confirmar Exclusão", 
            f"Tem certeza que deseja excluir o experimento #{self.current_loaded_exp_id}?\nEssa ação não pode ser desfeita."
        )

        if confirm:
            success = database.delete_experiment(self.current_loaded_exp_id)

            if success:
                self.current_loaded_exp_id = None
                self.current_loaded_data = None
                self.ax.clear()
                if self.ax2: self.ax2.remove(); self.ax2 = None
                self.ax.set_title("Experimento Excluído")
                self.canvas.draw()

                self.export_button.configure(state="disabled")
                self.delete_button.configure(state="disabled")

                self.populate_experiment_list()
            else:
                messagebox.showerror("Erro", "Não foi possível excluir o experimento.")