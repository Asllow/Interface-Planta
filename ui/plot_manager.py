"""
Gestor de Plotagem Vetorial em Tempo Real.

Módulo responsável pela orquestração do motor de renderização Matplotlib.
Implementa otimizações de memória (buffers circulares contíguos) e 
estruturação de dados para compatibilidade estrita com algoritmos de Blitting.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from collections import deque
import numpy as np
from typing import Dict, Optional, Any, Tuple

import config.settings as settings


def apply_style_from_settings() -> None:
    """
    Aplica o paradigma visual à instância global do Matplotlib.

    Configura parâmetros de alto rendimento no rcParams e assegura
    o contraste colorimétrico com o framework CustomTkinter.
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


class GraphManager:
    """
    Controlador de Estado e Geometria para gráficos de alta frequência.

    Abstrai a manipulação das coleções de dados (Deques) e a atualização
    das primitivas gráficas (Line2D) exigidas pelo motor de animação assíncrona.
    """

    def __init__(self, fig: Figure, ax: Axes, max_points: int = 100):
        """
        Instancia as estruturas de contenção de telemetria.

        Args:
            fig (Figure): Instância da figura base do Matplotlib.
            ax (Axes): Instância do eixo coordenado primário.
            max_points (int): Limite espacial dos buffers circulares.
        """
        self.fig = fig
        self.ax = ax
        self.ax2: Optional[Axes] = None
        self.max_points = max_points

        self.plot_data: Dict[str, Dict[str, Any]] = {
            'controle_tensao': {
                'x': deque(maxlen=self.max_points),
                'y1': deque(maxlen=self.max_points),
                'y2': deque(maxlen=self.max_points),
                'y_est': deque(maxlen=self.max_points),
                'label': 'Sinal de Controlo e Tensão'
            },
            'valor_adc': {
                'x': deque(maxlen=self.max_points),
                'y': deque(maxlen=self.max_points),
                'label': 'Valor Discreto ADC'
            },
            'ciclo': {
                'x': deque(maxlen=self.max_points),
                'y': deque(maxlen=self.max_points),
                'label': 'Período de Amostragem (ms)'
            },
            'erro_observador': {
                'x': deque(maxlen=self.max_points),
                'y': deque(maxlen=self.max_points),
                'label': 'Erro de Estimação (mV)'
            },
            'estados_sistema': {
                'x': deque(maxlen=self.max_points),
                'y1': deque(maxlen=self.max_points),
                'y2': deque(maxlen=self.max_points),
                'y3': deque(maxlen=self.max_points),
                'label': 'Matriz de Estados (LQR/Luenberger)'
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
        Reestrutura a matriz dimensional de subplots e reinstancia as primitivas gráficas.

        Args:
            graph_key (str): Chave identificadora do mapa de visualização.
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
            self.ax.set_ylabel('Comando (%)', color='tab:blue')
            self.line1, = self.ax.plot([], [], color='tab:blue', linestyle='-', animated=True, label='Sinal LQR (%)')
            self.ax.set_ylim(0, 100)
            self.ax.legend(loc='upper left')

            self.ax2.set_xlabel("Cronologia (s)")
            self.ax2.set_ylabel('Potencial (mV)', color='tab:red')
            self.line2, = self.ax2.plot([], [], color='tab:red', linestyle='-', animated=True, alpha=0.6, label='Medição Real')
            self.line_est, = self.ax2.plot([], [], color='tab:orange', linestyle='--', animated=True, label='Estimação Luenberger')
            
            self.ax2.set_ylim(0, 3300)
            self.ax2.legend(loc='upper left')

        elif graph_key == 'estados_sistema':
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Cronologia (s)")
            self.ax.set_ylabel("Amplitude Variável")
            
            self.line_est1, = self.ax.plot([], [], color='tab:blue', linestyle='-', animated=True, label='x1 (Velocidade)')
            self.line_est2, = self.ax.plot([], [], color='tab:green', linestyle='-', animated=True, label='x2 (Corrente)')
            self.line_est3, = self.ax.plot([], [], color='tab:orange', linestyle='-', animated=True, label='x3 (Erro Integrativo)')
            self.ax.legend(loc='upper left')

        elif graph_key == 'erro_observador':
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.line1, = self.ax.plot([], [], color='tab:purple', linestyle='-', animated=True)
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Cronologia (s)")
            self.ax.axhline(0, color='gray', linestyle='--', alpha=0.5)

        else:
            self.ax = self.fig.add_subplot(1, 1, 1)
            self.line1, = self.ax.plot([], [], linestyle='-', animated=True)
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Cronologia (s)" if graph_key == 'valor_adc' else "Índice Sequencial")
            if graph_key == 'valor_adc':
                self.ax.set_ylim(0, 4095)

        self.fig.tight_layout()

    def append_plot_data(self, data: Dict[str, Any]) -> None:
        """
        Incorpora e computa novos vetores de telemetria aos buffers de visualização.

        Args:
            data (Dict[str, Any]): Pacote de telemetria desserializado.
        """
        timestamp_amostra = data.get('timestamp_amostra_ms')
        if timestamp_amostra is None: return 

        self.sample_index += 1
        if self.start_time_ms is None:
            self.start_time_ms = timestamp_amostra

        current_time_sec = (timestamp_amostra - self.start_time_ms) / 1000.0

        sinal = data.get('sinal_controle', 0.0)
        tensao = data.get('tensao_mv', 0.0)
        adc = data.get('valor_adc', 0)
        val_est = data.get('tensao_estimada_mv', np.nan)
        val_erro = data.get('erro_obs_mv', np.nan)

        est1 = data.get('estado_1', 0.0)
        est2 = data.get('estado_2', 0.0)
        est3 = data.get('estado_3', 0.0)

        self.plot_data['controle_tensao']['x'].append(current_time_sec)
        self.plot_data['controle_tensao']['y1'].append(sinal)
        self.plot_data['controle_tensao']['y2'].append(tensao)
        self.plot_data['controle_tensao']['y_est'].append(val_est)

        self.plot_data['erro_observador']['x'].append(current_time_sec)
        self.plot_data['erro_observador']['y'].append(val_erro)

        self.plot_data['valor_adc']['x'].append(current_time_sec)
        self.plot_data['valor_adc']['y'].append(adc)

        self.plot_data['estados_sistema']['x'].append(current_time_sec)
        self.plot_data['estados_sistema']['y1'].append(est1)
        self.plot_data['estados_sistema']['y2'].append(est2)
        self.plot_data['estados_sistema']['y3'].append(est3)

        if self.last_sample_time is not None:
            cycle_time = timestamp_amostra - self.last_sample_time
            self.plot_data['ciclo']['x'].append(self.sample_index)
            self.plot_data['ciclo']['y'].append(cycle_time)
            
        self.last_sample_time = timestamp_amostra

    def animation_update_callback(self, frame: int) -> Tuple:
        """
        Rotina de injeção vetorial demandada pelo backend FuncAnimation.

        Args:
            frame (int): Iterador de chamada.

        Returns:
            Tuple: Coleção de instâncias Artist modificadas na iteração corrente.
        """
        if not self.current_graph:
            return (self.line1,)

        data = self.plot_data[self.current_graph]
        x_data = list(data['x'])

        if not x_data:
            return ()

        current_x_min = x_data[0]
        current_x_max = x_data[-1]

        if self.current_graph == 'controle_tensao':
            self.line1.set_data(x_data, data['y1'])
            self.line2.set_data(x_data, data['y2'])
            self.line_est.set_data(x_data, data['y_est'])
            
            artists = [self.line1, self.line2, self.line_est]

            self.ax.set_xlim(current_x_min, max(current_x_max, current_x_min + 0.1))
            self.ax2.set_xlim(current_x_min, max(current_x_max, current_x_min + 0.1))
            
            return tuple(artists)

        elif self.current_graph == 'estados_sistema':
            self.line_est1.set_data(x_data, data['y1'])
            self.line_est2.set_data(x_data, data['y2'])
            self.line_est3.set_data(x_data, data['y3'])
            
            self.ax.set_xlim(current_x_min, max(current_x_max, current_x_min + 0.1))
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)
            
            return self.line_est1, self.line_est2, self.line_est3

        else:
            self.line1.set_data(x_data, data['y'])
            self.ax.set_xlim(current_x_min, max(current_x_max, current_x_min + 0.1))
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)
            return (self.line1,)

    def get_current_stats(self) -> Dict[str, str]:
        """
        Agregação estatística instantânea para atualização dos componentes HMI.

        Returns:
            Dict[str, str]: Variáveis formatadas prontas para atribuição em interface textual.
        """
        if not self.current_graph:
            return {}

        data = self.plot_data[self.current_graph]

        if self.current_graph == 'controle_tensao':
            if not data['x']: return {'last_x': "--", 'last_y1': "--", 'last_y2': "--"}
            return {
                'last_x': f"{data['x'][-1]:.2f}",
                'last_y1': f"{data['y1'][-1]:.2f}",
                'last_y2': f"{data['y2'][-1]:.0f}"
            }
        else:
            if not data['y']: return {'last_x': "--", 'last_y': "--", 'avg_y': "--"}
            
            last_y = data['y'][-1]
            last_x = data['x'][-1]
            
            last_50_y = list(data['y'])[-50:]
            avg_y = sum(last_50_y) / len(last_50_y) if last_50_y else 0.0

            return {
                'last_x': f"{last_x:.2f}" if isinstance(last_x, float) else str(last_x), 
                'last_y': f"{last_y:.2f}", 
                'avg_y': f"{avg_y:.2f}"
            }