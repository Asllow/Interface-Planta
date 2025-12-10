# plot_manager.py
import matplotlib.pyplot as plt
from collections import deque
import config.settings as settings

def apply_style_from_settings():
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
    def __init__(self, fig, ax, max_points=100):
        self.fig = fig
        self.ax = ax
        self.ax2 = None
        self.max_points = max_points

        self.plot_data = {
            'controle_tensao': {
                'x': deque(maxlen=self.max_points), 
                'y1': deque(maxlen=self.max_points),
                'y2': deque(maxlen=self.max_points),
                'label': 'Sinal de Controle e Tensão'
            },
            'valor_adc': {'x': deque(maxlen=self.max_points), 'y': deque(maxlen=self.max_points), 'label': 'Valor ADC'},
            'ciclo': {'x': deque(maxlen=self.max_points), 'y': deque(maxlen=self.max_points), 'label': 'Intervalo entre Amostras (ms)'},
            'batch_interval': {'x': deque(maxlen=self.max_points), 'y': deque(maxlen=self.max_points), 'label': 'Intervalo de Rede (ms)'}
        }
        self.current_graph = None
        self.last_sample_time = None
        self.sample_index = 0
        self.start_time_ms = None

        self.line1, = self.ax.plot([], [], marker='o', markersize=2, linestyle='-', label='Sinal de Controle')
        self.line2 = None

    def select_graph(self, graph_key):
        if self.current_graph == graph_key:
            return

        self.current_graph = graph_key

        if self.ax2:
            self.ax2.remove()
            self.ax2 = None
            self.line2 = None

        self.ax.clear()
        data = self.plot_data[graph_key]

        if graph_key == 'controle_tensao':
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Tempo (s)")

            self.line1, = self.ax.plot(data['x'], data['y1'], color='tab:blue', marker='o', markersize=2, linestyle='-', label='Sinal de Controle (%)')
            self.ax.set_ylabel('Sinal de Controle (%)', color='tab:blue')
            self.ax.set_ylim(0, 100)
            self.ax.tick_params(axis='y', labelcolor='tab:blue')

            self.ax2 = self.ax.twinx()
            self.line2, = self.ax2.plot(data['x'], data['y2'], color='tab:red', marker='x', markersize=2, linestyle='--', label='Tensão (mV)')
            self.ax2.set_ylabel('Tensão (mV)', color='tab:red')
            self.ax2.set_ylim(0, 3300)
            self.ax2.tick_params(axis='y', labelcolor='tab:red')
            
            self.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
        else:
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

        self.fig.tight_layout()

    def append_plot_data(self, data):
        timestamp_amostra = data.get('timestamp_amostra_ms')
        if timestamp_amostra is None: return 

        self.sample_index += 1
        if self.start_time_ms is None:
            self.start_time_ms = timestamp_amostra

        current_time_sec = (timestamp_amostra - self.start_time_ms) / 1000.0

        sinal = data.get('sinal_controle', 0)
        tensao = data.get('tensao_mv', 0)
        adc = data.get('valor_adc', 0)

        self.plot_data['controle_tensao']['x'].append(current_time_sec)
        self.plot_data['controle_tensao']['y1'].append(sinal)
        self.plot_data['controle_tensao']['y2'].append(tensao)

        self.plot_data['valor_adc']['x'].append(current_time_sec)
        self.plot_data['valor_adc']['y'].append(adc)

        if self.last_sample_time is not None:
            cycle_time = timestamp_amostra - self.last_sample_time
            self.plot_data['ciclo']['x'].append(self.sample_index)
            self.plot_data['ciclo']['y'].append(cycle_time)
        self.last_sample_time = timestamp_amostra

        batch_interval = data.get('batch_interval_ms', 0)
        self.plot_data['batch_interval']['x'].append(self.sample_index)
        self.plot_data['batch_interval']['y'].append(batch_interval)

    def animation_update_callback(self, frame):
        if not self.current_graph:
            return self.line1,

        data = self.plot_data[self.current_graph]

        if self.current_graph == 'controle_tensao':
            self.line1.set_data(data['x'], data['y1'])
            self.line2.set_data(data['x'], data['y2'])

            if data['x']:
                self.ax.set_xlim(data['x'][0], data['x'][-1])
                self.ax2.set_xlim(data['x'][0], data['x'][-1])

            self.ax.set_ylim(0, 100)
            self.ax2.set_ylim(0, 3300)
            
            return self.line1, self.line2,

        else:
            self.line1.set_data(data['x'], data['y'])
            self.ax.relim()
            self.ax.autoscale_view(True, True)
            if self.current_graph == 'valor_adc':
                self.ax.set_ylim(0, 4095)
            return self.line1,

    def get_current_stats(self):
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

            last_50_y = list(data['y'])[-50:]
            avg_y = sum(last_50_y) / len(last_50_y) if last_50_y else 0

            return {
                'last_x': formatted_x, 
                'last_y': formatted_y, 
                'avg_y': f"{avg_y:.2f}"
            }