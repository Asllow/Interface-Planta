# main_app.py
import customtkinter as ctk
import sys
import db_writer 

from live_dashboard_frame import LiveDashboardFrame 
from home_screen_frame import HomeScreenFrame
from experiment_viewer_frame import ExperimentViewerFrame

class MainApplication(ctk.CTk):
    
    # ... (__init__ e show_frame continuam iguais) ...
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctk.set_appearance_mode("light")
        self.title("Dashboard de Controle da Planta")
        self.geometry("1000x600")
        container = ctk.CTkFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F, key in ( (HomeScreenFrame, "Home"), 
                        (LiveDashboardFrame, "Live"), 
                        (ExperimentViewerFrame, "Experiments")):
            frame = F(container, self)
            self.frames[key] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("Home")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_frame(self, page_key):
        if page_key != "Live":
            self.frames["Live"].stop_loops()
        frame = self.frames[page_key]
        frame.tkraise()
        if page_key == "Live":
            self.frames["Live"].start_loops()

    def on_closing(self):
        print("Iniciando desligamento...")
        
        try:
            self.frames["Live"].on_closing()
        except Exception as e:
            print(f"Erro ao fechar frame: {e}")
        
        try:
            db_writer.stop_db_writer_thread()
        except Exception as e:
            print(f"Erro ao parar DB Writer: {e}")
            
        # O delay de 200ms ainda é bom para reduzir o "ruído"
        print("Aguardando 200ms para tarefas do Tkinter finalizarem...")
        self.after(200, self.perform_shutdown)

    # --- FUNÇÃO ATUALIZADA ---
    def perform_shutdown(self):
        """
        Executa a destruição real da janela e força o processo
        a sair.
        """
        print("Executando self.destroy() e sys.exit()...")
        try:
            self.destroy() # Tenta destruir a UI
        except Exception as e:
            print(f"Erro (ignorado) durante self.destroy(): {e}")
            
        # --- CORREÇÃO AQUI ---
        # Força o encerramento do processo.
        # Isso mata a thread 'daemon' do Flask e
        # resolve o "terminal não fechou".
        sys.exit(0)