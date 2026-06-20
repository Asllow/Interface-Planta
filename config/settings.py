"""
Configurações Globais da Aplicação.

Este módulo define as constantes utilizadas em todo o projeto para a gestão
de aparência, dimensões de janelas, armazenamento e parâmetros de rede UDP.
"""

# --- Configurações de Interface Gráfica (UI) ---

APP_TITLE: str = "Dashboard de Controlo da Planta"
DEFAULT_WINDOW_SIZE: str = "1000x600"
APPEARANCE_MODE: str = "Light"
COLOR_THEME: str = "blue"

# --- Configurações de Base de Dados ---

DB_PATH: str = "motor_data.db"

# --- Configurações de Rede (Comunicação UDP ESP32) ---

ESP_IP: str = "192.168.4.1"
BROADCAST_IP: str = "192.168.4.255"
UDP_TELEMETRY_PORT: int = 5000
UDP_COMMAND_PORT: int = 5001