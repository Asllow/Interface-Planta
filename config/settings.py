"""
Configurações Globais da Aplicação.

Este módulo define constantes utilizadas em todo o projeto para controle
de aparência (temas), dimensões de janela e caminhos de arquivos.
Centralizar essas configurações facilita a manutenção e a alteração
de parâmetros visuais sem precisar caçar números mágicos no código.
"""

# --- Configurações de Interface Gráfica (UI) ---

# Título exibido na barra superior da janela principal
APP_TITLE: str = "Dashboard de Controle da Planta"

# Tamanho inicial da janela (Largura x Altura)
DEFAULT_WINDOW_SIZE: str = "1000x600"

# Modo de aparência do CustomTkinter: "System" (segue o SO), "Dark", "Light"
APPEARANCE_MODE: str = "Light" 

# Tema de cor dos widgets (botões, sliders, etc.): "blue", "green", "dark-blue"
COLOR_THEME: str = "blue"

# --- Configurações de Banco de Dados ---

# Caminho para o arquivo de banco de dados SQLite
DB_PATH: str = "motor_data.db"