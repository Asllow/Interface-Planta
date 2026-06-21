"""
Gestor de Plotagem Vetorial em Tempo Real (Aceleração NumPy).

Módulo responsável pela orquestração do motor de renderização Matplotlib.
Implementa matrizes RingBuffer (C-Array) para otimização de memória e 
reajuste dinâmico de janelas de observação vetorial (Auto-Scaling).
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import numpy as np
from typing import Dict, Optional, Any, Tuple

import config.settings as settings


def apply_style_from_settings() -> None:
    """
    Aplica o paradigma visual à instância global do Matplotlib.
    """
    mode = settings.APPEARANCE_MODE.lower()

    if mode == "dark":
        plt.style.use('dark_background')
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
            'grid.alpha': 0.8,
            'path.simplify': True,
            'path.simplify_threshold': 1.0,
            'agg.path.chunksize': 10000
        })
    else:
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams.update({
            'figure.facecolor': '#f0f0f0',
            'axes.facecolor': 'white',
            'text.color': 'black',
            'grid.alpha': 0.4,
            'path.simplify': True,
            'path.simplify_threshold': 1.0,
            'agg.path.chunksize': 10000
        })


class RingBuffer:
    """
    Vetor circular estático para contenção de telemetria em alta frequência.
    Mitiga o acionamento do Garbage Collector limitando a alocação de memória ao arranque.
    """
    def __init__(self, capacity: int, dtype=float):
        self.capacity = capacity
        self.data = np.empty(capacity, dtype=dtype)
        self.index = 0
        self.is_full = False

    def append(self, value: float) -> None:
        self.data[self.index] = value
        self.index += 1
        if self.index == self.capacity:
            self.index = 0
            self.is_full = True

    def get_data(self) -> np.ndarray:
        if not self.is_full:
            return self.data[:self.index]
        return np.concatenate((self.data[self.index:], self.data[:self.index]))

    def get_last(self) -> float:
        if self.index == 0 and not self.is_full:
            return 0.0
        return self.data[self.index - 1]

    def get_mean_recent(self, window: int = 50) -> float:
        if not self.is_full and self.index == 0:
            return 0.0
        arr = self.get_data()
        return np.mean(arr[-window:]) if len(arr) >= window else np.mean(arr)


class GraphManager:
    """
    Controlador de Estado e Geometria para gráficos acelerados.
    """

    def __init__(self, fig: Figure, ax: Axes, max_points: int = 2000):
        """
        Instancia buffers vetoriais estáticos e primitivas gráficas.
        """
        self.fig = fig
        self.ax = ax
        self.ax2: Optional[Axes] = None
        self.max_points = max_points

        self.plot_data = {
            'controle_tensao': {
                'x': RingBuffer(max_points),
                'y1': RingBuffer(max_points),
                'y2': RingBuffer(max_points),
                'y_est': RingBuffer(max_points),
                'label': 'Controle e Tensão'
            },
            'valor_adc': {
                'x': RingBuffer(max_points),
                'y': RingBuffer(max_points),
                'label': 'Valor Discreto ADC'
            },
            'ciclo': {
                'x': RingBuffer(max_points),
                'y': RingBuffer(max_points),
                'label': 'Tempo de Ciclo (ms)'
            },
            'erro_observador': {
                'x': RingBuffer(max_points),
                'y': RingBuffer(max_points),
                'label': 'Erro do Observador (mV)'
            },
            'estados_sistema': {
                'x': RingBuffer(max_points),
                'y1': RingBuffer(max_points),
                'y2': RingBuffer(max_points),
                'y3': RingBuffer(max_points),
                'label': 'Estados do Sistema'
            },
        }

        self.current_graph: Optional[str] = None
        self.last_sample_time: Optional[int] = None
        self.sample_index: int = 0
        self.start_time_ms: Optional[int] = None

        self.line1, = self.ax.plot([], [], marker='o', markersize=2, linestyle='-', animated=True)
        self.line2 = None
        self.line_est = None
        self.line_est1 = None
        self.line_est2 = None
        self.line_est3 = None

    def select_graph(self, graph_key: str) -> None:
        """
        Reestrutura a matriz dimensional e reinstancia as primitivas gráficas.
        """
        if self.current_graph == graph_key:
            return

        self.current_graph = graph_key
        self.fig.clear()
        self.ax2 = None

        data = self.plot_data[graph_key]

        if graph_key == 'controle_tensao':
            self.ax = self.fig.add_subplot(2, 1, 1)
            self.ax2 = self.fig.add_subplot(2, 1, 2, sharex=self.ax)

            self.ax.set_title(data['label'])
            self.ax.set_ylabel('Sinal (%)', color='tab:blue')
            self.line1, = self.ax.plot([], [], color='tab:blue', linestyle='-', animated=True, label='Sinal de Controle (%)')
            self.ax.set_ylim(0, 100)
            self.ax.legend(loc='upper left')

            self.ax2.set_xlabel("Tempo (s)")
            self.ax2.set_ylabel('Tensão (mV)', color='tab:red')
            self.line2, = self.ax2.plot([], [], color='tab:red', linestyle='-', animated=True, alpha=0.6, label='Tensão Real')
            self.line_est, = self.ax2.plot([], [], color='tab:orange', linestyle='--', animated=True, label='Tensão Estimada')
            
            self.ax2.set_ylim(0, 3300)
            self.ax2.legend(loc='upper left')

        elif graph_key == 'estados_sistema':
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Tempo (s)")
            self.ax.set_ylabel("Amplitude")
            
            self.line_est1, = self.ax.plot([], [], color='tab:blue', linestyle='-', animated=True, label='x1')
            self.line_est2, = self.ax.plot([], [], color='tab:green', linestyle='-', animated=True, label='x2')
            self.line_est3, = self.ax.plot([], [], color='tab:orange', linestyle='-', animated=True, label='x3')
            self.ax.legend(loc='upper left')

        elif graph_key == 'erro_observador':
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.line1, = self.ax.plot([], [], color='tab:purple', linestyle='-', animated=True)
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Tempo (s)")
            self.ax.axhline(0, color='gray', linestyle='--', alpha=0.5)

        else:
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.line1, = self.ax.plot([], [], linestyle='-', animated=True)
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Tempo (s)" if graph_key == 'valor_adc' else "Amostra N")
            
            if graph_key == 'valor_adc':
                self.ax.set_ylim(0, 4095)

        self.fig.tight_layout()

    def append_plot_data(self, data: Dict[str, Any]) -> None:
        """
        Incorpora pacote de telemetria aos buffers circulares.
        """
        timestamp_amostra = data.get('timestamp_amostra_ms')
        if timestamp_amostra is None: return 

        self.sample_index += 1
        if self.start_time_ms is None:
            self.start_time_ms = timestamp_amostra

        current_time_sec = (timestamp_amostra - self.start_time_ms) / 1000.0

        self.plot_data['controle_tensao']['x'].append(current_time_sec)
        self.plot_data['controle_tensao']['y1'].append(data.get('sinal_controle', 0.0))
        self.plot_data['controle_tensao']['y2'].append(data.get('tensao_mv', 0.0))
        self.plot_data['controle_tensao']['y_est'].append(data.get('tensao_estimada_mv', np.nan))

        self.plot_data['erro_observador']['x'].append(current_time_sec)
        self.plot_data['erro_observador']['y'].append(data.get('erro_obs_mv', np.nan))

        self.plot_data['valor_adc']['x'].append(current_time_sec)
        self.plot_data['valor_adc']['y'].append(data.get('valor_adc', 0))

        self.plot_data['estados_sistema']['x'].append(current_time_sec)
        self.plot_data['estados_sistema']['y1'].append(data.get('estado_1', 0.0))
        self.plot_data['estados_sistema']['y2'].append(data.get('estado_2', 0.0))
        self.plot_data['estados_sistema']['y3'].append(data.get('estado_3', 0.0))

        if self.last_sample_time is not None:
            cycle_time = timestamp_amostra - self.last_sample_time
            self.plot_data['ciclo']['x'].append(self.sample_index)
            self.plot_data['ciclo']['y'].append(cycle_time)
            
        self.last_sample_time = timestamp_amostra

    def animation_update_callback(self, frame: int) -> Tuple:
        """
        Rotina de injeção vetorial exigida pelo backend FuncAnimation.
        Gere os redimensionamentos dinâmicos de eixo (Auto-Scaling) assegurando
        a coerência da renderização através de chamadas draw_idle().
        """
        if not self.current_graph:
            return (self.line1,)

        data = self.plot_data[self.current_graph]
        x_data = data['x'].get_data()

        if len(x_data) == 0:
            return ()

        # --- 1. Ajuste Dinâmico do Eixo X (Janela Deslizante de Tempo) ---
        current_x_min = x_data[0]
        current_x_max = x_data[-1]

        if current_x_max == current_x_min:
            current_x_max = current_x_min + 0.1

        self.ax.set_xlim(current_x_min, current_x_max)
        if self.ax2:
            self.ax2.set_xlim(current_x_min, current_x_max)

        # --- 2. Injeção de Primitivas e Ajuste Condicional do Eixo Y ---
        if self.current_graph == 'controle_tensao':
            self.line1.set_data(x_data, data['y1'].get_data())
            self.line2.set_data(x_data, data['y2'].get_data())
            self.line_est.set_data(x_data, data['y_est'].get_data())
            
            artists = [self.line1, self.line2, self.line_est]
            
            # Repinta a grelha e marcadores para a janela deslizante
            self.fig.canvas.draw_idle()
            return tuple(artists)

        elif self.current_graph == 'estados_sistema':
            y1 = data['y1'].get_data()
            y2 = data['y2'].get_data()
            y3 = data['y3'].get_data()
            
            self.line_est1.set_data(x_data, y1)
            self.line_est2.set_data(x_data, y2)
            self.line_est3.set_data(x_data, y3)
            
            # Filtra pacotes perdidos ou inválidos para calcular Limites Verticais
            valid_y = np.concatenate([y1[~np.isnan(y1)], y2[~np.isnan(y2)], y3[~np.isnan(y3)]])
            if len(valid_y) > 0:
                y_min, y_max = np.min(valid_y), np.max(valid_y)
                margin = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
                self.ax.set_ylim(y_min - margin, y_max + margin)

            self.fig.canvas.draw_idle()
            return self.line_est1, self.line_est2, self.line_est3

        else:
            y = data['y'].get_data()
            self.line1.set_data(x_data, y)
            
            # O Valor ADC opera numa arquitetura fixa de 12-bits (0-4095).
            # Apenas Ciclo e Erro devem flutuar.
            if self.current_graph in ['erro_observador', 'ciclo']:
                valid_y = y[~np.isnan(y)]
                if len(valid_y) > 0:
                    y_min, y_max = np.min(valid_y), np.max(valid_y)
                    margin = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
                    self.ax.set_ylim(y_min - margin, y_max + margin)
            
            self.fig.canvas.draw_idle()
            return (self.line1,)

    def get_current_stats(self) -> Dict[str, str]:
        """
        Agregação estatística instantânea para interface textual.
        """
        if not self.current_graph:
            return {}

        data = self.plot_data[self.current_graph]
        
        last_x = data['x'].get_last()

        if self.current_graph == 'controle_tensao':
            if last_x == 0.0: return {'last_x': "--", 'last_y1': "--", 'last_y2': "--"}
            return {
                'last_x': f"{last_x:.2f}",
                'last_y1': f"{data['y1'].get_last():.2f}",
                'last_y2': f"{data['y2'].get_last():.0f}"
            }
        else:
            if last_x == 0.0: return {'last_x': "--", 'last_y': "--", 'avg_y': "--"}
            
            last_y = data['y'].get_last()
            avg_y = data['y'].get_mean_recent(50)

            return {
                'last_x': f"{last_x:.2f}" if isinstance(last_x, float) else str(last_x), 
                'last_y': f"{last_y:.2f}", 
                'avg_y': f"{avg_y:.2f}"
            }