# 🎛️ Interface de Controle de Planta (Tacogerador)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Build](https://img.shields.io/badge/Build-Windows_Exe-blue)

Interface gráfica desenvolvida para a disciplina de **Sistemas de Controle I**. O software atua como uma estação de controle e monitoramento para uma planta didática (Motor DC com Tacogerador), comunicando-se via Wi-Fi (HTTP) com um microcontrolador ESP32.

O sistema permite a visualização de dados em tempo real, atuação via PWM, gravação seletiva de experimentos e análise histórica dos dados.

## 🚀 Funcionalidades

* **Monitoramento em Tempo Real:** Gráficos dinâmicos de Tensão, Valor ADC, Intervalo de Amostras e Sinal de Controle.
* **Filtro de Sinal (EMA):** Aplicação opcional de Média Móvel Exponencial (EMA) para suavização da curva de tensão.
* **Controle Manual de Gravação:** O sistema inicia em "Standby". A gravação no banco de dados é acionada manualmente.
* **Atuação (PWM):** Envio de setpoints de *Duty Cycle* (0-100%) para a planta.
* **Banco de Dados:** Armazenamento automático em SQLite (`motor_data.db`).
* **Visualizador de Histórico:**
    * Seleção e carregamento de experimentos anteriores.
    * **Exportação Inteligente:** Salva dados em `.csv`, `.txt` ou `.npy`. (Inclui coluna filtrada se a opção estiver ativa).
    * **Exclusão:** Permite remover experimentos do banco.

## 📥 Como Baixar e Executar (Windows)

Não é necessário instalar Python para usar a versão compilada.

1. Baixe o arquivo **`InterfacePlanta.exe`** na seção de [Releases](#) (ou solicite o arquivo ao desenvolvedor).
2. Coloque o arquivo em uma pasta de sua preferência (ex: `Meus Documentos/Controle`).
3. Execute o arquivo com dois cliques.
    * *Nota:* Na primeira execução, o firewall do Windows pode pedir permissão pois o programa abre um servidor local para receber dados do ESP32. **Permita o acesso**.
4. O arquivo de banco de dados `motor_data.db` e a pasta `images/` serão criados automaticamente na mesma pasta do executável.

## 🖥️ Guia de Uso

### 1. Painel em Tempo Real (Live Dashboard)
* **Conexão:** Assim que o ESP32 estiver ligado e enviando dados para o IP do computador, os gráficos iniciarão automaticamente.
* **Filtro:** Use o interruptor **"Filtro (EMA)"** na barra lateral para suavizar o ruído da leitura de tensão.
* **Gravação:**
    * Clique em "Iniciar Gravação" (Botão Verde) para começar a salvar os dados.
    * Clique novamente (Botão Vermelho) para finalizar o experimento.
* **Controle:** Digite o valor do PWM (0-100) e pressione Enter ou "Enviar".

### 2. Visualizador (Experiments)
* Acesse a aba "Experiments".
* Selecione um experimento na lista para visualizar os gráficos.
* **Exportar:** Clique em "Exportar Experimento" para salvar em Excel/CSV/TXT.
    * *Dica:* Marque "Ativar Filtro (Média)" antes de exportar se desejar os dados suavizados no arquivo.

---

## ⚙️ Área do Desenvolvedor (Código Fonte)

Se você deseja editar o código ou compilar por conta própria, siga estes passos.

### Estrutura do Projeto

interface-planta/
├── main.py                  # Ponto de entrada
├── config/                  # Configurações globais
├── core/                    # Backend (Servidor Web, Database, Exportador)
└── ui/                      # Frontend (Interface Gráfica, Gráficos)

### Pré-requisitos
* Python 3.10+
* Git

### Instalação (Dev)

1. **Clone o repositório:**
   git clone https://github.com/seu-usuario/interface-planta.git
   cd interface-planta

2. **Crie o ambiente virtual:**
   python -m venv venv
   .\venv\Scripts\activate

3. **Instale as dependências:**
   pip install -r requirements.txt

4. **Execute:**
   python main.py

### Como Compilar (.exe)

Para gerar um novo executável após alterações no código:

1. Instale o PyInstaller:
   pip install pyinstaller

2. Execute o comando de build (incluindo os assets do CustomTkinter):
   pyinstaller --noconsole --onefile --name="InterfacePlanta" --collect-all customtkinter main.py

3. O executável estará na pasta `dist/`.

## 📡 Integração (API)

O sistema espera requisições **POST** no endpoint `/data`.

**Exemplo de JSON:**
[
  {
    "timestamp_amostra_ms": 10500,
    "valor_adc": 2048,
    "tensao_mv": 1650,
    "sinal_controle": 50.5
  }
]

## 📄 Licença

Este projeto é desenvolvido para fins acadêmicos.