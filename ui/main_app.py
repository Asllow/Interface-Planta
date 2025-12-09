# main_app.py
import customtkinter as ctk
import sys
from core import db_writer
from config import settings

from ui.frames.live_dashboard_frame import LiveDashboardFrame 
from ui.frames.home_screen_frame import HomeScreenFrame
from ui.frames.experiment_viewer_frame import ExperimentViewerFrame

class MainApplication(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ctk.set_appearance_mode(settings.APPEARANCE_MODE)
        ctk.set_default_color_theme(settings.COLOR_THEME)
        self.title(settings.APP_TITLE)
        self.geometry(settings.DEFAULT_WINDOW_SIZE)

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

        print("Aguardando 200ms para tarefas do Tkinter finalizarem...")
        self.after(200, self.perform_shutdown)

    def perform_shutdown(self):
        print("Executando self.destroy() e sys.exit()...")

        try:
            self.destroy()
        except Exception as e:
            print(f"Erro (ignorado) durante self.destroy(): {e}")

        sys.exit(0)