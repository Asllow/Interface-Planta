# 🎛️ Interface de Controle de Planta (Tacogerador)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green)
![Status](https://img.shields.io/badge/Status-Active-success)

Interface gráfica desenvolvida em Python para a disciplina de **Sistemas de Controle I**. O software atua como uma estação de controle e monitoramento para uma planta didática (Motor DC com Tacogerador), comunicando-se via Wi-Fi (HTTP) com um microcontrolador ESP32.

O sistema permite a visualização de dados em tempo real, atuação via PWM, gravação seletiva de experimentos e análise histórica dos dados com recursos avançados de filtragem de sinal.

## 🚀 Funcionalidades

* **Monitoramento em Tempo Real:** Gráficos dinâmicos de Tensão, Valor ADC, Intervalo de Amostras e Sinal de Controle.
* **Filtro de Sinal (EMA):** Aplicação opcional de Média Móvel Exponencial (EMA) para suavização da curva de tensão em tempo real e na análise pós-experimento.
* **Controle Manual de Gravação:** O sistema inicia em modo "Standby". A gravação no banco de dados é acionada manualmente, garantindo que apenas os dados do experimento real sejam salvos.
* **Atuação (PWM):** Envio de setpoints de *Duty Cycle* (0-100%) para a planta.
* **Banco de Dados:** Armazenamento automático em SQLite (`motor_data.db`).
* **Visualizador de Histórico:**
    * Seleção e carregamento de experimentos anteriores.
    * **Exportação Inteligente:** Salva dados em `.csv`, `.txt` ou `.npy`. Se o filtro estiver ativo na visualização, o arquivo exportado incluirá automaticamente uma coluna extra com a tensão filtrada.
    * **Exclusão:** Permite remover experimentos de teste ou falhos.

## 📂 Estrutura do Projeto

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
    ├── plot_manager.py      # Gerenciamento de gráficos (Matplotlib) e Filtros
    └── frames/              # Telas da aplicação
        ├── home_screen_frame.py
        ├── live_dashboard_frame.py
        └── experiment_viewer_frame.py

## 🛠️ Instalação e Configuração

Siga estes passos para rodar o projeto em sua máquina local.

### Pré-requisitos
* **Python 3.10** ou superior instalado.
* Conexão de rede local (o computador e o ESP32 devem estar conectados à mesma rede Wi-Fi).

### Passo a Passo

1. **Clone o repositório:**
   Abra seu terminal ou CMD e execute:
   
   git clone https://github.com/seu-usuario/interface-planta.git
   cd interface-planta

2. **Crie um ambiente virtual (Recomendado):**
   Isso isola as dependências do projeto.

   *Windows:*
   python -m venv venv
   .\venv\Scripts\activate

   *Linux/Mac:*
   python3 -m venv venv
   source venv/bin/activate

3. **Instale as dependências:**
   O projeto utiliza bibliotecas como CustomTkinter, Matplotlib e Flask. Instale todas de uma vez:
   
   pip install -r requirements.txt
   
   *Se o arquivo requirements.txt não existir, instale manualmente:*
   pip install customtkinter matplotlib flask numpy packaging pillow

4. **Configuração (Opcional):**
   Você pode alterar o tema (Light/Dark) ou o esquema de cores editando o arquivo `config/settings.py`:
   
   # config/settings.py
   APPEARANCE_MODE = "dark" 
   COLOR_THEME = "blue"

5. **Execute a aplicação:**
   
   python main.py
   
   *O console exibirá o endereço IP e a porta onde o servidor está escutando (ex: http://0.0.0.0:5000).*

## 🖥️ Como Usar

### 1. Painel em Tempo Real (Live Dashboard)
* **Conexão:** Assim que o ESP32 estiver ligado e configurado para enviar dados para o IP do seu computador, os gráficos começarão a se mover automaticamente.
* **Filtro de Ruído:** Use o interruptor **"Filtro (EMA)"** na barra lateral esquerda. Isso plotará uma linha laranja suavizada sobre o sinal de tensão (vermelho), ajudando a visualizar a tendência em meio ao ruído.
* **Gravação:**
    * O status inicial é "EM ESPERA" (Botão Verde: "Iniciar Gravação").
    * Clique para começar a salvar os dados no banco. O status muda para "GRAVANDO" (Botão Vermelho).
    * Clique novamente para parar e fechar o experimento.
* **Controle (PWM):** Digite o valor do PWM (0 a 100) no campo inferior e pressione Enter ou clique em "Enviar".
* **Pausar:** O botão "Pausar" congela a visualização para análise imediata, mas o sistema continua recebendo e processando dados em segundo plano.

### 2. Visualizador (Experiments)
* Navegue até a aba "Experiments" pelo menu principal.
* A lista lateral exibe todos os experimentos concluídos, com data, hora e duração.
* **Visualizar:** Clique em um item da lista para carregar os gráficos de Tensão e Controle correspondentes.
* **Filtro Pós-Processado:** Marque a caixa de seleção **"Ativar Filtro (Média)"** na barra lateral. Isso aplicará o filtro exponencial aos dados históricos carregados.
* **Exportar:** Clique em "Exportar Experimento".
    * Uma janela de salvamento abrirá. Você pode escolher entre `.csv`, `.txt` ou `.npy`.
    * **Nota:** Se a caixa de filtro estiver marcada, o arquivo exportado conterá uma coluna adicional chamada `tensao_filtrada_mv` com os valores processados.
* **Excluir:** Use o botão "Excluir Experimento" para remover o registro permanentemente do banco de dados.

## 📡 Integração (API)

O microcontrolador deve enviar requisições **POST** para o endpoint `/data`. O servidor aceita lotes (batches) de dados para melhor performance.

**Exemplo de Payload JSON esperado:**

[
  {
    "timestamp_amostra_ms": 10500,
    "valor_adc": 2048,
    "tensao_mv": 1650,
    "sinal_controle": 50.5
  },
  {
    "timestamp_amostra_ms": 10550,
    "valor_adc": 2055,
    "tensao_mv": 1655,
    "sinal_controle": 50.5
  }
]

## 🤝 Contribuição

Contribuições são bem-vindas! Se você quiser melhorar o projeto:

1. Faça um Fork do projeto.
2. Crie uma Branch para sua Feature (`git checkout -b feature/MinhaFeature`).
3. Faça o Commit das suas mudanças (`git commit -m 'Adiciona funcionalidade X'`).
4. Faça o Push para a Branch (`git push origin feature/MinhaFeature`).
5. Abra um Pull Request.

## 📄 Licença

Este projeto é desenvolvido para fins acadêmicos. Sinta-se livre para usar e modificar.