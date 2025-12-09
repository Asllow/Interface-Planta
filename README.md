# 🎛️ Interface de Controle de Planta (Tacogerador)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green)
![Status](https://img.shields.io/badge/Status-Active-success)

Interface gráfica desenvolvida em Python para a disciplina de **Sistemas de Controle I**. O software atua como uma estação de controle e monitoramento para uma planta didática (Motor DC com Tacogerador), comunicando-se via Wi-Fi (HTTP) com um microcontrolador ESP32.

O sistema permite a visualização de dados em tempo real, atuação via PWM, gravação seletiva de experimentos e análise histórica dos dados.

## 🚀 Funcionalidades

* **Monitoramento em Tempo Real:** Gráficos dinâmicos de Tensão, Valor ADC, Ciclo de Rede e Sinal de Controle.
* **Controle Manual de Gravação:** O sistema inicia em modo "Standby". A gravação no banco de dados é acionada manualmente, garantindo que apenas os dados do experimento real sejam salvos.
* **Atuação (PWM):** Envio de setpoints de *Duty Cycle* (0-100%) para a planta.
* **Banco de Dados:** Armazenamento automático em SQLite (`motor_data.db`).
* **Visualizador de Histórico:**
    * Seleção e carregamento de experimentos anteriores.
    * **Exportação:** Salva dados em `.csv`, `.txt` ou `.npy` (NumPy) para análise externa (MATLAB/Excel).
    * **Exclusão:** Permite remover experimentos de teste ou falhos.

## 📂 Estrutura do Projeto

```text
interface-planta/
├── main.py                  # Ponto de entrada (Inicia DB, Servidor e GUI)
├── config/                  # Configurações globais
│   └── settings.py          # Temas, constantes e parâmetros visuais
├── core/                    # Backend (Lógica de Negócio)
│   ├── web_server.py        # Servidor Flask (Recebe dados do ESP32)
│   ├── database.py          # Gerenciamento do SQLite
│   ├── db_writer.py         # Thread de escrita assíncrona
│   ├── shared_state.py      # Variáveis compartilhadas e Filas (Queues)
│   └── data_exporter.py     # Lógica de exportação de arquivos
└── ui/                      # Frontend (Interface Gráfica)
    ├── main_app.py          # Janela Principal
    ├── plot_manager.py      # Gerenciamento de gráficos (Matplotlib)
    └── frames/              # Telas da aplicação
        ├── home_screen_frame.py
        ├── live_dashboard_frame.py
        └── experiment_viewer_frame.py
```

## 🛠️ Instalação e Configuração

### Pré-requisitos
* Python 3.10 ou superior.
* Conexão de rede local (o computador e o ESP32 devem estar na mesma rede).

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/interface-planta.git](https://github.com/seu-usuario/interface-planta.git)
   cd interface-planta
   ```

2. **Crie e ative um ambiente virtual (Recomendado):**

   *Windows:*
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

   *Linux/Mac:*
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install customtkinter matplotlib flask numpy packaging pillow
   ```

4. **Configuração (Opcional):**
   Você pode alterar o tema (Light/Dark) ou o esquema de cores editando o arquivo `config/settings.py`:
   ```python
   # config/settings.py
   APPEARANCE_MODE = "dark" 
   COLOR_THEME = "blue"
   ```

5. **Execute a aplicação:**
   ```bash
   python main.py
   ```
   *O console exibirá o endereço IP e a porta onde o servidor está escutando (ex: http://0.0.0.0:5000).*

## 🖥️ Como Usar

### 1. Painel em Tempo Real (Live Dashboard)
* **Conexão:** Assim que o ESP32 começar a enviar dados, os gráficos começarão a se mover automaticamente.
* **Gravação:**
    * O status inicial é "EM ESPERA" (Botão Verde: "Iniciar Gravação").
    * Clique para começar a salvar os dados no banco. O status muda para "GRAVANDO" (Botão Vermelho).
    * Clique novamente para parar e fechar o experimento.
* **Controle:** Digite o valor do PWM no campo inferior e pressione Enter ou clique em "Enviar".
* **Pausar:** O botão "Pausar" congela a visualização para análise visual imediata, mas o sistema continua recebendo e processando dados em segundo plano.

### 2. Visualizador (Experiments)
* Navegue até a aba "Experiments".
* A lista lateral exibe todos os experimentos concluídos, com data e duração.
* **Visualizar:** Clique em um item para carregar os gráficos de Tensão e Controle.
* **Exportar:** Clique em "Exportar Experimento" para gerar um arquivo CSV/TXT para usar no MATLAB ou Excel.
* **Excluir:** Use o botão "Excluir Experimento" para remover o registro permanentemente do banco de dados.

## 📡 Integração (API)

O microcontrolador deve enviar requisições **POST** para o endpoint `/data`. O servidor aceita lotes (batches) de dados para melhor performance.

**Exemplo de Payload JSON:**

```json
[
  {
    "timestamp_amostra_ms": 10500,
    "valor_adc": 2048,
    "tensao_mv": 1650,
    "sinal_controle": 50.5
  }
]
```

## 🤝 Contribuição

Contribuições são bem-vindas! Se você quiser melhorar o projeto:

1. Faça um Fork do projeto.
2. Crie uma Branch para sua Feature (`git checkout -b feature/MinhaFeature`).
3. Faça o Commit das suas mudanças (`git commit -m 'Adiciona funcionalidade X'`).
4. Faça o Push para a Branch (`git push origin feature/MinhaFeature`).
5. Abra um Pull Request.

## 📄 Licença

Este projeto é desenvolvido para fins acadêmicos. Sinta-se livre para usar e modificar.