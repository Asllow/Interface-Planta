# home_screen_frame.py
import customtkinter as ctk

# REMOVA as importações de 'live_dashboard_frame' e 'experiment_viewer_frame'

class HomeScreenFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        button_container = ctk.CTkFrame(self, fg_color="transparent")
        button_container.grid(row=0, column=0, sticky="nsew", padx=50, pady=50, in_=self) 
        
        button_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")
        button_container.grid_rowconfigure(0, weight=1)
        
        # --- MUDANÇA NOS COMANDOS ---
        btn_live = ctk.CTkButton(button_container,
                                 text="Dashboard (Tempo Real)",
                                 height=60,
                                 font=ctk.CTkFont(size=14, weight="bold"),
                                 command=lambda: controller.show_frame("Live"))
        btn_live.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        btn_exit = ctk.CTkButton(button_container,
                                 text="X", width=60, height=60, corner_radius=30,
                                 font=ctk.CTkFont(size=20, weight="bold"),
                                 fg_color="#D9534F", hover_color="#C9302C",
                                 command=controller.on_closing)
        btn_exit.grid(row=0, column=1, padx=20, pady=20, sticky="") 

        btn_experiments = ctk.CTkButton(button_container,
                                        text="Ver Experimentos",
                                        height=60,
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        command=lambda: controller.show_frame("Experiments"))
        btn_experiments.grid(row=0, column=2, padx=20, pady=20, sticky="ew")