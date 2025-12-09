# database.py
import sqlite3
from datetime import datetime

DB_FILE = "motor_data.db"
current_run_id = None

# --- NOVA TRAVA GLOBAL ---
# Começa ligada, permitindo a gravação automática no início.
is_recording_enabled = True

def _create_new_experiment():
    """Função interna para criar um novo experimento."""
    global current_run_id
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        timestamp_inicio = datetime.now().isoformat()
        cursor.execute("INSERT INTO experimentos (timestamp_inicio, status) VALUES (?, 'running')", (timestamp_inicio,))
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        current_run_id = new_id
        print(f"--- NOVO EXPERIMENTO INICIADO --- ID: {current_run_id} ---")
        return new_id
        
    except Exception as e:
        print(f"ERRO ao criar novo experimento: {e}")
        return None

def startup_cleanup():
    """Fecha experimentos 'running' de sessões anteriores."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE experimentos
            SET status = 'completed',
                timestamp_fim = (
                    SELECT timestamp_recebimento FROM telemetria 
                    WHERE id_experimento = experimentos.id
                    ORDER BY timestamp_recebimento DESC LIMIT 1
                )
            WHERE status = 'running'
        """)
        cursor.execute("UPDATE experimentos SET status = 'completed' WHERE status = 'running' AND timestamp_fim IS NULL")
        conn.commit()
        conn.close()
        if cursor.rowcount > 0:
            print(f"DB: {cursor.rowcount} experimento(s) anterior(es) foi(ram) fechado(s).")
    except Exception as e:
        print(f"ERRO ao fechar experimentos antigos: {e}")

# --- FUNÇÃO ATUALIZADA ---
def close_current_experiment():
    """
    Fecha o experimento atual E DESLIGA A GRAVAÇÃO.
    """
    global current_run_id, is_recording_enabled
    
    # 1. Desliga a trava de gravação
    is_recording_enabled = False
    print("DB: Gravação DESLIGADA.")
    
    if current_run_id is None:
        print("DB: Nenhum experimento 'running' para fechar.")
        return
        
    print(f"Fechando experimento ID: {current_run_id}...")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        timestamp_fim = datetime.now().isoformat()
        cursor.execute("SELECT timestamp_recebimento FROM telemetria WHERE id_experimento = ? ORDER BY timestamp_recebimento DESC LIMIT 1", (current_run_id,))
        last_telemetry_time = cursor.fetchone()
        
        if last_telemetry_time:
            timestamp_fim = last_telemetry_time[0]

        cursor.execute("UPDATE experimentos SET timestamp_fim = ?, status = 'completed' WHERE id = ?", (timestamp_fim, current_run_id))
        
        conn.commit()
        conn.close()
        print(f"--- EXPERIMENTO FINALIZADO --- ID: {current_run_id} ---")
        current_run_id = None
        
    except Exception as e:
        print(f"ERRO ao fechar experimento {current_run_id}: {e}")

# --- FUNÇÃO ATUALIZADA ---
def start_new_experiment():
    """
    Fecha o experimento atual (se houver) E LIGA A GRAVAÇÃO,
    criando um novo experimento.
    """
    global is_recording_enabled
    print("DB: Solicitação para iniciar novo experimento...")
    
    # 1. Garante que o experimento anterior seja fechado
    #    (Nota: isso também desliga a gravação, mas vamos ligá-la de volta)
    close_current_experiment() 
    
    # 2. Liga a trava de gravação
    is_recording_enabled = True
    print("DB: Gravação LIGADA.")
    
    # 3. Força a criação do novo experimento agora
    _create_new_experiment()

def init_db():
    # ... (Esta função continua exatamente igual) ...
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_inicio TEXT NOT NULL,
            timestamp_fim TEXT,
            status TEXT NOT NULL DEFAULT 'running'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_experimento INTEGER,
            timestamp_recebimento TEXT NOT NULL,
            timestamp_amostra_ms INTEGER,
            valor_adc INTEGER,
            tensao_mv INTEGER,
            sinal_controle REAL,
            FOREIGN KEY (id_experimento) REFERENCES experimentos (id)
        )
    """)
    try:
        cursor.execute("ALTER TABLE experimentos ADD COLUMN timestamp_fim TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE experimentos ADD COLUMN status TEXT NOT NULL DEFAULT 'running'")
    except sqlite3.OperationalError: pass
    conn.commit()
    conn.close()

# --- FUNÇÃO ATUALIZADA ---
def insert_data(data: dict):
    """
    Insere dados, criando um novo experimento se necessário,
    MAS SOMENTE SE a gravação estiver ligada.
    """
    global current_run_id, is_recording_enabled
    
    # 1. NOVA VERIFICAÇÃO DA TRAVA GLOBAL
    if not is_recording_enabled:
        # print("DB: Gravação desligada, dados descartados.") # (Opcional: pode poluir o log)
        return

    try:
        # 2. Lógica antiga de criação automática (agora segura)
        if current_run_id is None:
            _create_new_experiment()
        
        if current_run_id is None:
            print("ERRO: ID do experimento é nulo. Dados não serão salvos.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO telemetria (
                id_experimento, timestamp_recebimento, timestamp_amostra_ms, 
                valor_adc, tensao_mv, sinal_controle
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            current_run_id, data.get("timestamp_recebimento"), data.get("timestamp_amostra_ms"),
            data.get("valor_adc"), data.get("tensao_mv"), data.get("sinal_controle")
        ))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"ERRO ao inserir dados no banco de dados: {e}")

# ... (as funções get_completed_experiments() e 
#      get_telemetry_for_experiment() continuam iguais) ...
def get_completed_experiments():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp_inicio, timestamp_fim 
            FROM experimentos 
            WHERE status = 'completed' 
              AND timestamp_inicio IS NOT NULL 
              AND timestamp_fim IS NOT NULL
            ORDER BY timestamp_inicio DESC
        """)
        experimentos = []
        for row in cursor.fetchall():
            try:
                inicio = datetime.fromisoformat(row[1])
                fim = datetime.fromisoformat(row[2])
                duracao_total = (fim - inicio)
                segundos_totais = int(duracao_total.total_seconds())
                minutos, segundos = divmod(segundos_totais, 60)
                duracao_str = f"{minutos}m {segundos}s"
                experimentos.append({
                    "id": row[0],
                    "inicio_str": inicio.strftime("%d/%m/%Y às %H:%M:%S"),
                    "fim_str": fim.strftime("%H:%M:%S"),
                    "duracao_str": duracao_str,
                    "nome": f"Experimento #{row[0]}"
                })
            except Exception: pass
        conn.close()
        return experimentos
    except Exception as e:
        print(f"ERRO ao buscar experimentos concluídos: {e}")
        return []

def get_telemetry_for_experiment(exp_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp_amostra_ms, valor_adc, tensao_mv, sinal_controle 
            FROM telemetria 
            WHERE id_experimento = ?
            ORDER BY timestamp_amostra_ms ASC
        """, (exp_id,))
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return data
    except Exception as e:
        print(f"ERRO ao buscar telemetria para o experimento {exp_id}: {e}")
        return []

if __name__ == '__main__':
    print("Inicializando o banco de dados...")
    init_db()
    print("Fechando experimentos 'running' antigos (se houver)...")
    startup_cleanup()
    print("Banco de dados 'motor_data.db' pronto.")