"""
Gerenciador de Gráficos (Plot Manager).

Este módulo é responsável pela manipulação direta da biblioteca Matplotlib,
gerenciando a atualização de dados em tempo real, a troca de tipos de gráficos
e a aplicação de estilos visuais (Dark/Light) conforme as configurações globais.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from collections import deque
import numpy as np
import config.settings as settings
from typing import Dict, Optional, Any, Tuple, List

def calculate_moving_average(data: List[float], alpha: float = 0.15) -> List[float]:
    """
    Calcula a Média Móvel Exponencial (EMA).
    Reduz o atraso (lag) comparado à média simples.
    
    Args:
        data: Lista de valores brutos.
        alpha: Fator de suavização (0 < alpha <= 1).
               Valores maiores (ex: 0.3) = Menos lag, menos filtro.
               Valores menores (ex: 0.05) = Mais filtro, mais lag.
               0.15 é um bom equilíbrio para substituir uma janela de 20.
    """
    if not data:
        return []
    
    # O EMA pode ser calculado muito rápido com Pandas, mas para manter
    # dependência apenas de NumPy/Python puro, usamos este loop otimizado:
    if not data: return []
    
    ema = []
    current_ema = data[0]
    ema.append(current_ema)
    
    for value in data[1:]:
        current_ema = (value * alpha) + (current_ema * (1 - alpha))
        ema.append(current_ema)
        
    return ema

def apply_style_from_settings() -> None:
    """
    Aplica o tema visual (Dark/Light) ao Matplotlib baseando-se nas configurações.

    Lê `settings.APPEARANCE_MODE` e atualiza `plt.rcParams` para garantir que
    o fundo, eixos, texto e grid combinem com a interface CustomTkinter.
    """

    mode = settings.APPEARANCE_MODE.lower()

    if mode == "dark":
        plt.style.use('dark_background')
        # Cores ajustadas para combinar com CustomTkinter Dark (#2b2b2b)
        bg_color = '#2b2b2b' 
        plot_bg = '#212121'
        text_color = '#e0e0e0'

        plt.rcParams.update({
            'figure.facecolor': bg_color,
            'axes.facecolor': plot_bg,
            'savefig.facecolor': bg_color,

            'text.color': text_color,
            'axes.labelcolor': text_color,
            'axes.edgecolor': '#404040',
            'xtick.color': text_color,
            'ytick.color': text_color,

            'grid.color': "#898989",
            'grid.alpha': 0.8
        })

    else:
        plt.style.use('seaborn-v0_8-whitegrid')

        plt.rcParams.update({
            'figure.facecolor': '#f0f0f0',
            'axes.facecolor': 'white',
            'text.color': 'black',
            'grid.alpha': 0.4
        })

class GraphManager:
    """
    Controlador lógico para figuras do Matplotlib em tempo real.

    Gerencia os buffers de dados (usando deque para performance), a renderização
    dos eixos e a atualização da animação.
    """

    def __init__(self, fig: Figure, ax: Axes, max_points: int = 100):
        """
        Inicializa o gerenciador de gráficos.

        Args:
            fig (Figure): A instância da figura Matplotlib.
            ax (Axes): O eixo principal para plotagem.
            max_points (int): Tamanho máximo do buffer de dados (janela deslizante).
        """

        self.fig = fig
        self.ax = ax
        self.ax2: Optional[Axes] = None
        self.max_points = max_points
        self.show_filter = False  # Estado do Toggle

        # Estrutura de dados para armazenar buffers de diferentes tipos de gráficos
        self.plot_data: Dict[str, Dict[str, Any]] = {
            'controle_tensao': {
                'x': deque(maxlen=self.max_points), 
                'y1': deque(maxlen=self.max_points),
                'y2': deque(maxlen=self.max_points),
                'y2_filtered': deque(maxlen=self.max_points),
                'y_est': deque(maxlen=self.max_points),
                'label': 'Sinal de Controle e Tensão'
            },
            'valor_adc': {
                'x': deque(maxlen=self.max_points), 
                'y': deque(maxlen=self.max_points), 
                'label': 'Valor ADC'
            },
            'ciclo': {
                'x': deque(maxlen=self.max_points), 
                'y': deque(maxlen=self.max_points), 
                'label': 'Intervalo entre Amostras (ms)'
            },
            'erro_observador': {
                'x': deque(maxlen=self.max_points), 
                'y': deque(maxlen=self.max_points), 
                'label': 'Erro do Observador (mV)'
            },
            'estados_sistema': {
                'x': deque(maxlen=self.max_points), 
                'y1': deque(maxlen=self.max_points), # Estado 1 (ex: Posição / Tensão)
                'y2': deque(maxlen=self.max_points), # Estado 2 (ex: Velocidade)
                'y3': deque(maxlen=self.max_points), # Estado 3 (ex: Erro Integral)
                'label': 'Estados do Sistema (LQR / Observador)'
            },
        }

        self.current_graph: Optional[str] = None
        self.last_sample_time: Optional[int] = None
        self.sample_index: int = 0
        self.start_time_ms: Optional[int] = None

        self.line1, = self.ax.plot([], [], marker='o', markersize=2, linestyle='-', label='Sinal de Controle')
        self.line2 = None
        self.line3 = None
        self.line4 = None

        self.line_est1 = None
        self.line_est2 = None
        self.line_est3 = None

    def toggle_filter(self, enabled: bool):
        """Ativa ou desativa a visualização da linha de tensão filtrada."""
        self.show_filter = enabled
        if self.line3:
            self.line3.set_visible(enabled)
            # Atualiza a legenda apenas do eixo de tensão (ax2)
            if self.ax2:
                self.ax2.legend(loc='upper left')

    def select_graph(self, graph_key: str) -> None:
        """
        Alterna o gráfico exibido na área de plotagem.

        Limpa a figura atual e reconfigura títulos, labels e limites
        para o novo tipo de dado solicitado.
        """

        if self.current_graph == graph_key:
            return

        self.current_graph = graph_key

        # Limpa TODA a figura para podermos reestruturar a quantidade de subplots livremente
        self.fig.clear()
        self.ax2 = None

        data = self.plot_data[graph_key]

        # Configuração específica para o gráfico dividido (Controle em cima, Tensão embaixo)
        if graph_key == 'controle_tensao':
            # Cria dois subplots (2 linhas, 1 coluna). 'sharex' faz com que movam juntos no eixo X
            self.ax = self.fig.add_subplot(2, 1, 1)
            self.ax2 = self.fig.add_subplot(2, 1, 2, sharex=self.ax)

            # --- Eixo Superior: Sinal de Controle ---
            self.ax.set_title(data['label'])
            self.ax.set_ylabel('Sinal de Controle (%)', color='tab:blue')
            self.line1, = self.ax.plot(data['x'], data['y1'], color='tab:blue', marker='o', markersize=2, linestyle='-', label='Sinal de Controle (%)')
            self.ax.set_ylim(0, 100)
            self.ax.tick_params(axis='y', labelcolor='tab:blue')
            self.ax.legend(loc='upper left')

            # --- Eixo Inferior: Tensão ---
            self.ax2.set_xlabel("Tempo (s)")
            self.ax2.set_ylabel('Tensão (mV)', color='tab:red')
            self.line2, = self.ax2.plot(data['x'], data['y2'], color='tab:red', marker='x', markersize=2, linestyle='--', label='Tensão Real (mV)')
            
            self.line3, = self.ax2.plot(data['x'], data['y2_filtered'], color='orange', linewidth=2, linestyle='-', label='Tensão Filtrada (Méd)')
            self.line3.set_visible(self.show_filter)
            
            self.line4, = self.ax2.plot(data['x'], data['y_est'], color='tab:orange', linewidth=2, linestyle='-', label='Tensão Estimada')
            
            self.ax2.set_ylim(0, 3300)
            self.ax2.tick_params(axis='y', labelcolor='tab:red')
            self.ax2.xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
            self.ax2.legend(loc='upper left')

        elif graph_key == 'estados_sistema':
            self.ax = self.fig.add_subplot(1, 1, 1) # Gráfico único para os 3 estados
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Tempo (s)")
            self.ax.set_ylabel("Amplitude dos Estados")
            
            # Plota as 3 linhas simultaneamente com cores diferentes
            self.line_est1, = self.ax.plot(data['x'], data['y1'], color='tab:blue', marker='o', markersize=2, linestyle='-', label='Estado 1 (x1)')
            self.line_est2, = self.ax.plot(data['x'], data['y2'], color='tab:green', marker='x', markersize=2, linestyle='-', label='Estado 2 (x2)')
            self.line_est3, = self.ax.plot(data['x'], data['y3'], color='tab:orange', marker='^', markersize=2, linestyle='-', label='Estado 3 (x3)')
            
            self.ax.legend(loc='upper left')
            self.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))

        elif graph_key == 'erro_observador':
            # Volta para gráfico único
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.line1, = self.ax.plot(data['x'], data['y'], color='tab:purple', marker='o', markersize=2, linestyle='-')
            self.ax.set_title(data['label'])
            self.ax.set_ylabel(data['label'])
            self.ax.set_xlabel("Tempo (s)")
            self.ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
            self.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))

        else:
            # Volta para gráfico único
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.line1, = self.ax.plot(data['x'], data['y'], marker='o', markersize=2, linestyle='-')
            self.ax.set_title(data['label'])
            self.ax.set_ylabel(data['label'])

            is_time_based = (graph_key == 'valor_adc')
            self.ax.set_xlabel("Tempo (s)" if is_time_based else "Índice da Amostra")

            if graph_key == 'valor_adc':
                self.ax.set_ylim(0, 4095)
                self.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
            else:
                self.ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), 'd')))

        # Garante que os gráficos não se sobreponham visualmente
        self.fig.tight_layout()

    def append_plot_data(self, data: Dict[str, Any]) -> None:
        """
        Processa um novo pacote de dados e o adiciona aos buffers circulares.

        Calcula o tempo relativo (segundos) e deltas entre amostras.

        Args:
            data (dict): Dicionário contendo chaves como 'timestamp_amostra_ms',
                        'sinal_controle', 'tensao_mv', etc.
        """

        timestamp_amostra = data.get('timestamp_amostra_ms')
        if timestamp_amostra is None: return 

        self.sample_index += 1
        if self.start_time_ms is None:
            self.start_time_ms = timestamp_amostra

        current_time_sec = (timestamp_amostra - self.start_time_ms) / 1000.0

        sinal = data.get('sinal_controle', 0)
        tensao = data.get('tensao_mv', 0)
        adc = data.get('valor_adc', 0)
        est = data.get('tensao_estimada_mv')
        erro = data.get('erro_obs_mv')

        val_est = est if est is not None else np.nan
        val_erro = erro if erro is not None else np.nan

        est1 = data.get('estado_1', 0.0)
        est2 = data.get('estado_2', 0.0)
        est3 = data.get('estado_3', 0.0)

        # Adiciona aos buffers do gráfico combinado
        self.plot_data['controle_tensao']['x'].append(current_time_sec)
        self.plot_data['controle_tensao']['y1'].append(sinal)
        self.plot_data['controle_tensao']['y2'].append(tensao)
        self.plot_data['controle_tensao']['y_est'].append(val_est)

        # Adiciona ao gráfico de Erro
        self.plot_data['erro_observador']['x'].append(current_time_sec)
        self.plot_data['erro_observador']['y'].append(val_erro)

        # NOVO: Cálculo Média Móvel Tempo Real
        buffer_tensao = list(self.plot_data['controle_tensao']['y2'])
        window = 20
        if len(buffer_tensao) > 0:
            subset = buffer_tensao[-window:] 
            avg_val = sum(subset) / len(subset)
            self.plot_data['controle_tensao']['y2_filtered'].append(avg_val)
        else:
            self.plot_data['controle_tensao']['y2_filtered'].append(tensao)

        # Adiciona aos buffers do ADC
        self.plot_data['valor_adc']['x'].append(current_time_sec)
        self.plot_data['valor_adc']['y'].append(adc)

        self.plot_data['estados_sistema']['x'].append(current_time_sec)
        self.plot_data['estados_sistema']['y1'].append(est1)
        self.plot_data['estados_sistema']['y2'].append(est2)
        self.plot_data['estados_sistema']['y3'].append(est3)

        # Calcula e armazena o ciclo (delta t)
        if self.last_sample_time is not None:
            cycle_time = timestamp_amostra - self.last_sample_time
            self.plot_data['ciclo']['x'].append(self.sample_index)
            self.plot_data['ciclo']['y'].append(cycle_time)
        self.last_sample_time = timestamp_amostra

    def animation_update_callback(self, frame: int) -> Tuple:
        """
        Função chamada periodicamente pela animação para redesenhar as linhas.

        Args:
            frame (int): Número do quadro atual (fornecido pelo FuncAnimation).

        Returns:
            Tuple: Tupla contendo os objetos artísticos (linhas) atualizados.
        """

        if not self.current_graph:
            return self.line1,

        data = self.plot_data[self.current_graph]

        if self.current_graph == 'controle_tensao':
            self.line1.set_data(data['x'], data['y1'])
            self.line2.set_data(data['x'], data['y2'])
            self.line4.set_data(data['x'], data['y_est'])

            # Atualiza Linha Filtrada se visível
            if self.show_filter and self.line3:
                self.line3.set_data(data['x'], data['y2_filtered'])

            # Atualiza limites do eixo X dinamicamente
            if data['x']:
                self.ax.set_xlim(data['x'][0], data['x'][-1])
                self.ax2.set_xlim(data['x'][0], data['x'][-1])

            self.ax.set_ylim(0, 100)
            self.ax2.set_ylim(0, 3300)
            
            artists = [self.line1, self.line2, self.line4]
            if self.line3: artists.append(self.line3)
            return tuple(artists)

        elif self.current_graph == 'estados_sistema':
            self.line_est1.set_data(data['x'], data['y1'])
            self.line_est2.set_data(data['x'], data['y2'])
            self.line_est3.set_data(data['x'], data['y3'])
            
            # Redimensiona os eixos Y automaticamente de acordo com a variação dos estados
            self.ax.relim()
            self.ax.autoscale_view(True, True)
            
            return self.line_est1, self.line_est2, self.line_est3

        else:
            self.line1.set_data(data['x'], data['y'])
            self.ax.relim()
            self.ax.autoscale_view(True, True)
            if self.current_graph == 'valor_adc':
                self.ax.set_ylim(0, 4095)
            return self.line1,

    def get_current_stats(self) -> Dict[str, str]:
        """
        Calcula estatísticas rápidas dos dados atuais para exibição na barra de status.

        Returns:
            Dict[str, str]: Dicionário com chaves como 'last_x', 'last_y', 'avg_y'
                            formatados como strings.
        """

        if not self.current_graph:
            return {}

        data = self.plot_data[self.current_graph]

        if self.current_graph == 'controle_tensao':
            if not data['x']: return {'last_x': "--", 'last_y1': "--", 'last_y2': "--"}
            last_x = data['x'][-1]
            last_y1 = data['y1'][-1]
            last_y2 = data['y2'][-1]
            return {
                'last_x': f"{last_x:.2f}",
                'last_y1': f"{last_y1:.2f}",
                'last_y2': f"{last_y2:.0f}"
            }
        else:
            if not data['y']: return {'last_x': "--", 'last_y': "--", 'avg_y': "--"}
            last_y = data['y'][-1]
            last_x = data['x'][-1]
            formatted_x = f"{last_x:.2f}" if isinstance(last_x, float) else str(last_x)
            formatted_y = f"{last_y:.2f}"

            # Média móvel dos últimos 50 pontos para suavizar a leitura
            last_50_y = list(data['y'])[-50:]
            avg_y = sum(last_50_y) / len(last_50_y) if last_50_y else 0

            return {
                'last_x': formatted_x, 
                'last_y': formatted_y, 
                'avg_y': f"{avg_y:.2f}"
            }