# plot_manager.py
import matplotlib.pyplot as plt
from collections import deque

class GraphManager:
    def __init__(self, fig, ax, max_points=100):
        self.fig = fig
        self.ax = ax # Eixo Y principal (Sinal)
        self.ax2 = None # Eixo Y secundário (Tensão)
        self.max_points = max_points

        self.plot_data = {
            # --- MODIFICADO ---
            'controle_tensao': {
                'x': deque(maxlen=self.max_points), 
                'y1': deque(maxlen=self.max_points), # Para Sinal de Controle
                'y2': deque(maxlen=self.max_points), # Para Tensão
                'label': 'Sinal de Controle e Tensão'
            },
            # --- FIM DA MODIFICAÇÃO ---
            'valor_adc': {'x': deque(maxlen=self.max_points), 'y': deque(maxlen=self.max_points), 'label': 'Valor ADC'},
            'ciclo': {'x': deque(maxlen=self.max_points), 'y': deque(maxlen=self.max_points), 'label': 'Intervalo entre Amostras (ms)'},
            'batch_interval': {'x': deque(maxlen=self.max_points), 'y': deque(maxlen=self.max_points), 'label': 'Intervalo de Rede (ms)'}
        }
        self.current_graph = None
        self.last_sample_time = None
        self.sample_index = 0
        self.start_time_ms = None
        
        # Linhas do gráfico (agora duas)
        self.line1, = self.ax.plot([], [], marker='o', markersize=2, linestyle='-', label='Sinal de Controle')
        self.line2 = None

    def select_graph(self, graph_key):
        """Limpa e reconfigura os eixos para o gráfico selecionado."""
        if self.current_graph == graph_key:
            return

        self.current_graph = graph_key
        
        # --- Limpa o eixo secundário (se existir) ---
        if self.ax2:
            self.ax2.remove()
            self.ax2 = None
            self.line2 = None
        
        # Limpa o eixo principal
        self.ax.clear()

        data = self.plot_data[graph_key]
        
        # --- LÓGICA DO GRÁFICO COMBINADO ---
        if graph_key == 'controle_tensao':
            self.ax.set_title(data['label'])
            self.ax.set_xlabel("Tempo (s)")
            
            # Configura Eixo 1 (Sinal)
            self.line1, = self.ax.plot(data['x'], data['y1'], color='tab:blue', marker='o', markersize=2, linestyle='-', label='Sinal de Controle (%)')
            self.ax.set_ylabel('Sinal de Controle (%)', color='tab:blue')
            self.ax.set_ylim(0, 100)
            self.ax.tick_params(axis='y', labelcolor='tab:blue')
            
            # Cria Eixo 2 (Tensão)
            self.ax2 = self.ax.twinx()
            self.line2, = self.ax2.plot(data['x'], data['y2'], color='tab:red', marker='x', markersize=2, linestyle='--', label='Tensão (mV)')
            self.ax2.set_ylabel('Tensão (mV)', color='tab:red')
            self.ax2.set_ylim(0, 3300)
            self.ax2.tick_params(axis='y', labelcolor='tab:red')
            
            self.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
        
        # --- LÓGICA DOS OUTROS GRÁFICOS ---
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
        """Processa um novo 'data' e o adiciona aos deques."""
        timestamp_amostra = data.get('timestamp_amostra_ms')
        if timestamp_amostra is None: return 

        self.sample_index += 1
        if self.start_time_ms is None:
            self.start_time_ms = timestamp_amostra

        current_time_sec = (timestamp_amostra - self.start_time_ms) / 1000.0

        # Pega os valores
        sinal = data.get('sinal_controle', 0)
        tensao = data.get('tensao_mv', 0)
        adc = data.get('valor_adc', 0)

        # --- ADICIONA DADOS AO GRÁFICO COMBINADO ---
        self.plot_data['controle_tensao']['x'].append(current_time_sec)
        self.plot_data['controle_tensao']['y1'].append(sinal)
        self.plot_data['controle_tensao']['y2'].append(tensao)
        
        # --- Adiciona dados aos outros gráficos ---
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
        """Callback para o FuncAnimation."""
        if not self.current_graph:
            return self.line1,

        data = self.plot_data[self.current_graph]
        
        # --- ATUALIZA GRÁFICO COMBINADO ---
        if self.current_graph == 'controle_tensao':
            self.line1.set_data(data['x'], data['y1'])
            self.line2.set_data(data['x'], data['y2'])
            
            # Rola o eixo X
            if data['x']:
                self.ax.set_xlim(data['x'][0], data['x'][-1])
                self.ax2.set_xlim(data['x'][0], data['x'][-1])
            
            # Reaplica limites Y (pois o autoscale pode bagunçá-los)
            self.ax.set_ylim(0, 100)
            self.ax2.set_ylim(0, 3300)
            
            return self.line1, self.line2, # Retorna as duas linhas
        
        # --- ATUALIZA OUTROS GRÁFICOS ---
        else:
            self.line1.set_data(data['x'], data['y'])
            self.ax.relim()
            self.ax.autoscale_view(True, True)
            if self.current_graph == 'valor_adc':
                self.ax.set_ylim(0, 4095)
            
            return self.line1,

    def get_current_stats(self):
        """Retorna as estatísticas atuais para a barra de status."""
        if not self.current_graph:
            return {}
        
        data = self.plot_data[self.current_graph]
        
        # --- STATS GRÁFICO COMBINADO ---
        if self.current_graph == 'controle_tensao':
            if not data['x']: return {'last_x': "--", 'last_y1': "--", 'last_y2': "--"}
            last_x = data['x'][-1]
            last_y1 = data['y1'][-1]
            last_y2 = data['y2'][-1]
            return {
                'last_x': f"{last_x:.2f}",
                'last_y1': f"{last_y1:.2f}",
                'last_y2': f"{last_y2:.0f}" # Tensão (mV) não precisa de decimal
            }
        
        # --- STATS OUTROS GRÁFICOS ---
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