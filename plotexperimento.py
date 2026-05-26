import pandas as pd
import matplotlib.pyplot as plt

# 1. Carregar os dados do arquivo CSV
df = pd.read_csv('experimento_20.csv')

# 2. Normalizar o tempo para começar do zero e converter para segundos
tempo_inicial = df['timestamp_amostra_ms'].iloc[0]
df['tempo_s'] = (df['timestamp_amostra_ms'] - tempo_inicial) / 1000.0

# =====================================================================
# GRÁFICO 1: Sinal de Controle, Tensão Real e Tensão Estimada
# =====================================================================
fig, ax1 = plt.subplots(figsize=(12, 6))

# Plot das tensões (Eixo Y da esquerda)
ax1.set_xlabel('Tempo (segundos)', fontsize=11)
ax1.set_ylabel('Tensão (mV)', color='black', fontsize=11)
line1 = ax1.plot(df['tempo_s'], df['tensao_mv'], label='Tensão Real (mV)', color='tab:blue', alpha=0.8)
line2 = ax1.plot(df['tempo_s'], df['tensao_estimada_mv'], label='Tensão Estimada (mV)', color='tab:orange', linestyle='--', alpha=0.8)
ax1.tick_params(axis='y', labelcolor='black')
ax1.grid(True, linestyle=':', alpha=0.7)

# Plot do sinal de controle (Eixo Y da direita)
ax2 = ax1.twinx()
ax2.set_ylabel('Sinal de Controle', color='tab:green', fontsize=11)
line3 = ax2.plot(df['tempo_s'], df['sinal_controle'], label='Sinal de Controle', color='tab:green', linewidth=1.5)
ax2.tick_params(axis='y', labelcolor='tab:green')

# Adicionar legendas combinadas no mesmo quadro
lines = line1 + line2 + line3
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper left')

plt.title('Tensão Real, Tensão Estimada e Sinal de Controle no Tempo', fontsize=14)
fig.tight_layout()
plt.savefig('grafico1_analise.png') # Salva a primeira imagem
plt.show()

# =====================================================================
# GRÁFICO 2: Erro do Observador
# =====================================================================
plt.figure(figsize=(12, 4))

plt.plot(df['tempo_s'], df['erro_obs_mv'], label='Erro do Observador (mV)', color='tab:red', linewidth=1.5)

# Linha horizontal no Y=0 para referência
plt.axhline(0, color='black', linewidth=1, linestyle='--') 

plt.title('Erro do Observador ao Longo do Tempo', fontsize=14)
plt.xlabel('Tempo (segundos)', fontsize=11)
plt.ylabel('Erro (mV)', fontsize=11)
plt.legend(loc='upper right')
plt.grid(True, linestyle=':', alpha=0.7)

plt.tight_layout()
plt.savefig('grafico2_erro.png') # Salva a segunda imagem
plt.show()