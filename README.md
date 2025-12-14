# 🎛️ Interface de Controle de Planta (Tacogerador)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green) ![Status](https://img.shields.io/badge/Status-Active-success)

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
    * **Exportação Inteligente:** Salva dados em `.csv`, `.txt` ou `.npy` (inclui coluna filtrada se a opção estiver ativa).
    * **Exclusão:** Permite remover experimentos do banco.

## 📥 Como Baixar e Executar (Windows)

Não é necessário instalar Python para usar a versão compilada.

1. Baixe o arquivo **`InterfacePlanta.exe`** na seção de [Releases](https://github.com/Asllow/Interface-Planta/releases).
2. Coloque o arquivo em uma pasta de sua preferência.
3. Execute o arquivo.
    * *Nota:* Na primeira execução, o firewall pode pedir permissão. **Permita o acesso** para que o servidor local funcione.
4. O banco de dados e a pasta de imagens serão criados automaticamente ao lado do executável.

## 🖥️ Guia de Uso

### 1. Painel em Tempo Real (Live Dashboard)
* **Conexão:** Assim que o ESP32 estiver enviando dados, os gráficos iniciarão automaticamente.
* **Filtro:** Use o interruptor **"Filtro (EMA)"** na barra lateral para suavizar o ruído.
* **Gravação:**
    * Clique em "Iniciar Gravação" (Verde) para salvar os dados.
    * Clique novamente (Vermelho) para parar.
* **Controle:** Digite o valor do PWM (0-100) e pressione Enter.

### 2. Visualizador (Experiments)
* Acesse a aba "Experiments".
* Selecione um experimento na lista para ver os gráficos.
* **Exportar:** Clique em "Exportar Experimento" para salvar em Excel/CSV/TXT.

---

## ⚙️ Área do Desenvolvedor

Se você deseja editar o código ou compilar por conta própria.

### Estrutura do Projeto

```text
interface-planta/
├── main.py                  # Ponto de entrada
├── config/                  # Configurações globais
├── core/                    # Backend (Servidor Web, Database, Exportador)
└── ui/                      # Frontend (Interface Gráfica, Gráficos)
```

### Instalação (Dev)

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/Asllow/Interface-Planta.git](https://github.com/Asllow/Interface-Planta.git)
   cd Interface-Planta
   ```

2. **Crie o ambiente virtual:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute:**
   ```bash
   python main.py
   ```

### Como Compilar (.exe)

Para gerar um novo executável após alterações no código:

1. Instale o PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Execute o comando de build:
   ```bash
   pyinstaller --noconsole --onefile --name="InterfacePlanta" --collect-all customtkinter main.py
   ```

## 📡 Integração (API)

O sistema espera requisições **POST** no endpoint `/data`.

**Exemplo de JSON:**
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

## 📄 Licença

Este projeto é desenvolvido para fins acadêmicos.