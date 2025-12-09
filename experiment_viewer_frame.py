# experiment_viewer_frame.py
import customtkinter as ctk
import database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# --- Imports para a função de exportar ---
import os
from tkinter import filedialog as fd
import data_exporter
# --- Fim dos imports ---

class ExperimentViewerFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        
        # --- Variáveis para armazenar o experimento carregado ---
        self.current_loaded_data = None
        self.current_loaded_exp_id = None
        
        # --- LAYOUT ---
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=300) # Coluna da lista
        self.grid_columnconfigure(1, weight=1)              # Coluna do gráfico
        
        # --- BARRA SUPERIOR (com Voltar e Recarregar) ---
        top_bar = ctk.CTkFrame(self, height=50)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(top_bar, text="Visualizador de Experimentos", font=ctk.CTkFont(size=18, weight="bold")) \
            .pack(side="left", padx=20)
        ctk.CTkButton(top_bar, text="Voltar ao Menu", 
                      command=lambda: self.controller.show_frame("Home")) \
            .pack(side="right", padx=20)
        ctk.CTkButton(top_bar, text="Recarregar Lista", 
                      command=self.populate_experiment_list) \
            .pack(side="right", padx=5)

        # --- COLUNA ESQUERDA (Lista Rolável) ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Experimentos Concluídos")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", 
                               padx=(10, 5), pady=(0, 10))

        # --- COLUNA DIREITA (Gráfico e Controles) ---
        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.grid(row=1, column=1, sticky="nsew", 
                              padx=(5, 10), pady=(0, 10))
        
        # Configuração do Grid do Frame Direito
        self.graph_frame.grid_rowconfigure(1, weight=1) # Canvas expande
        self.graph_frame.grid_columnconfigure(0, weight=1) # Conteúdo centraliza

        # --- Configuração do Matplotlib ---
        plt.style.use('seaborn-v0_8-whitegrid')
        self.fig, self.ax = plt.subplots()
        self.ax2 = None # Placeholder para o segundo eixo Y
        self.fig.set_facecolor("#f0f0f0") 
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        
        # --- Barra de Ferramentas (ROW 0) ---
        toolbar_frame = ctk.CTkFrame(self.graph_frame, fg_color="transparent")
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # --- Canvas (Gráfico) (ROW 1) ---
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        # --- BOTÃO "Exportar Experimento" (ROW 2) ---
        self.export_button = ctk.CTkButton(self.graph_frame, 
                                           text="Exportar Experimento",
                                           command=self.on_export_pressed,
                                           state="disabled") # Começa desabilitado
        
        self.export_button.grid(row=2, column=0, pady=(10, 5)) 

        # Popula a lista na primeira vez
        self.populate_experiment_list()

    def populate_experiment_list(self):
        """Busca experimentos do DB e cria os botões na lista."""
        
        # Limpa widgets antigos (necessário para o "Recarregar")
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        experiments = database.get_completed_experiments()
        
        if not experiments:
            ctk.CTkLabel(self.scroll_frame, text="Nenhum experimento concluído encontrado.") \
                .pack(pady=10)
            return

        for exp in experiments:
            text = f"{exp['nome']}\n" \
                   f"Início: {exp['inicio_str']} (Fim: {exp['fim_str']})\n" \
                   f"Duração: {exp['duracao_str']}"
            
            btn = ctk.CTkButton(self.scroll_frame, 
                                text=text, 
                                anchor="w", # Alinha texto à esquerda
                                command=lambda e=exp['id']: self.load_experiment_data(e))
            btn.pack(pady=5, padx=5, fill="x")

    def load_experiment_data(self, exp_id):
        """Busca dados de um ID e plota no gráfico (com eixo duplo)."""
        
        # 1. Limpa os dados antigos e desabilita o botão
        self.current_loaded_data = None
        self.current_loaded_exp_id = None
        self.export_button.configure(state="disabled")

        telemetry_data = database.get_telemetry_for_experiment(exp_id)
        
        # 2. Limpa os eixos do gráfico
        self.ax.clear()
        if self.ax2:
            self.ax2.remove()
            self.ax2 = None
            
        if not telemetry_data:
            self.ax.set_title(f"Experimento #{exp_id} - Sem Dados")
            self.canvas.draw()
            return

        try:
            # --- DADOS CARREGADOS COM SUCESSO ---
            # 3. Armazena os dados e habilita o botão
            self.current_loaded_data = telemetry_data
            self.current_loaded_exp_id = exp_id
            self.export_button.configure(state="normal")
            # --- FIM DA ADIÇÃO ---

            start_time_ms = telemetry_data[0]['timestamp_amostra_ms']
            
            # Cria os eixos de dados
            time_sec = [(d['timestamp_amostra_ms'] - start_time_ms) / 1000.0 for d in telemetry_data]
            sinal_controle = [d.get('sinal_controle', 0) for d in telemetry_data]
            tensao_mv = [d.get('tensao_mv', 0) for d in telemetry_data]
            
            # --- Plota o gráfico combinado ---
            self.ax.set_title(f"Experimento #{exp_id} - Controle e Tensão")
            self.ax.set_xlabel("Tempo (s) desde o início do experimento")
            
            # Eixo 1 (Sinal)
            self.ax.plot(time_sec, sinal_controle, color='tab:blue', marker='o', markersize=2, linestyle='-', label='Sinal de Controle (%)')
            self.ax.set_ylabel('Sinal de Controle (%)', color='tab:blue')
            self.ax.set_ylim(0, 100)
            self.ax.tick_params(axis='y', labelcolor='tab:blue')
            self.ax.grid(True, axis='y', linestyle='--', color='tab:blue', alpha=0.5)
            
            # Eixo 2 (Tensão)
            self.ax2 = self.ax.twinx()
            self.ax2.plot(time_sec, tensao_mv, color='tab:red', marker='x', markersize=2, linestyle='--', label='Tensão (mV)')
            self.ax2.set_ylabel('Tensão (mV)', color='tab:red')
            self.ax2.set_ylim(0, 3300)
            self.ax2.tick_params(axis='y', labelcolor='tab:red')
            self.ax2.grid(True, axis='y', linestyle=':', color='tab:red', alpha=0.5)
            
            # Ajusta o layout para caber tudo
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Erro ao processar dados do gráfico: {e}")
            self.ax.clear()
            self.ax.set_title(f"Experimento #{exp_id} - Erro ao carregar dados")
            self.canvas.draw()

    # --- MÉTODO NOVO PARA EXPORTAR ---
    def on_export_pressed(self):
        """
        Chamado quando o botão 'Exportar Experimento' é clicado.
        Abre o diálogo 'Salvar como...'.
        """
        if not self.current_loaded_data:
            print("Nenhum dado carregado para exportar.")
            return
            
        # Define os tipos de arquivo para o diálogo
        file_types = [
            ('Arquivo CSV', '*.csv'),
            ('Arquivo de Texto (Tabulado)', '*.txt'),
            ('Arquivo NumPy', '*.npy'),
            ('Todos os arquivos', '*.*')
        ]
        
        # Sugere um nome de arquivo padrão
        default_name = f"experimento_{self.current_loaded_exp_id}.csv"
        
        # Abre o diálogo "Salvar como..."
        filepath = fd.asksaveasfilename(
            title="Salvar Experimento Como...",
            initialfile=default_name,
            filetypes=file_types,
            defaultextension=".csv"
        )
        
        # Se o usuário cancelar, 'filepath' será uma string vazia
        if not filepath:
            print("Exportação cancelada pelo usuário.")
            return
            
        # Pega a extensão que o usuário escolheu (ou digitou)
        _base, ext = os.path.splitext(filepath)
        ext = ext.lower() # Garante que seja minúscula
        
        try:
            # Chama o exportador correto com base na extensão
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
            # (Aqui poderíamos mostrar um pop-up de erro para o usuário)