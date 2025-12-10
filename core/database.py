"""
Módulo de Gerenciamento de Banco de Dados (SQLite).

Responsável por todas as operações de persistência de dados, incluindo:
- Criação e inicialização de tabelas.
- Controle de sessões de experimento (Início/Fim).
- Inserção de telemetria e recuperação de histórico.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_FILE = "motor_data.db"
current_run_id: Optional[int] = None
is_recording_enabled: bool = False

def _create_new_experiment() -> Optional[int]:
    """
    Cria um novo registro na tabela 'experimentos' e define o status como 'running'.
    
    Returns:
        Optional[int]: O ID do novo experimento criado, ou None em caso de erro.
    """

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

def is_experiment_running() -> bool:
    """
    Verifica se há um experimento ativo e se a gravação está habilitada.

    Returns:
        bool: True se estiver gravando, False caso contrário.
    """

    global current_run_id, is_recording_enabled
    return (current_run_id is not None) and is_recording_enabled

def start_new_experiment() -> None:
    """
    Habilita a flag de gravação e inicia um novo experimento no banco.
    Se houver um experimento anterior aberto, ele será fechado primeiro.
    """

    global is_recording_enabled
    print("DB: Solicitação para iniciar novo experimento...")
    close_current_experiment() 
    is_recording_enabled = True
    print("DB: Gravação LIGADA.")
    _create_new_experiment()

def close_current_experiment() -> None:
    """
    Finaliza o experimento atual, atualizando o timestamp de fim e status.
    Desabilita a flag global de gravação.
    """

    global current_run_id, is_recording_enabled

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
        # Busca a última amostra para usar como data de fim real
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

def init_db() -> None:
    """
    Inicializa a estrutura do banco de dados (DDL).
    Cria as tabelas 'experimentos' e 'telemetria' se não existirem.
    """

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
    # Migrações para compatibilidade com versões antigas do DB
    try:
        cursor.execute("ALTER TABLE experimentos ADD COLUMN timestamp_fim TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE experimentos ADD COLUMN status TEXT NOT NULL DEFAULT 'running'")
    except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()

def insert_data(data: Dict[str, Any]) -> None:
    """
    Insere um registro de telemetria no banco de dados.
    
    Esta função só executa a inserção se a gravação estiver habilitada
    e houver um ID de experimento válido.

    Args:
        data (dict): Dicionário contendo os dados (tensao_mv, valor_adc, etc).
    """

    global current_run_id, is_recording_enabled

    if not is_recording_enabled:
        return

    try:
        if current_run_id is None:
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

def get_completed_experiments() -> List[Dict[str, Any]]:
    """
    Recupera a lista de todos os experimentos concluídos.

    Returns:
        List[Dict]: Lista de dicionários com metadados dos experimentos.
    """

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

def get_telemetry_for_experiment(exp_id: int) -> List[Dict[str, Any]]:
    """
    Recupera todos os dados brutos de telemetria de um experimento específico.

    Args:
        exp_id (int): O ID do experimento.

    Returns:
        List[Dict]: Lista de dicionários contendo os dados de cada amostra.
    """

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

def delete_experiment(exp_id: int) -> bool:
    """
    Exclui permanentemente um experimento e seus dados associados.

    Args:
        exp_id (int): O ID do experimento a ser excluído.

    Returns:
        bool: True se bem-sucedido, False caso contrário.
    """

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM telemetria WHERE id_experimento = ?", (exp_id,))
        cursor.execute("DELETE FROM experimentos WHERE id = ?", (exp_id,))
        
        conn.commit()
        conn.close()
        print(f"DB: Experimento {exp_id} excluído com sucesso.")
        return True
    except Exception as e:
        print(f"ERRO ao excluir experimento {exp_id}: {e}")
        return False

def startup_cleanup() -> None:
    """
    Limpeza inicial: Marca como 'completed' experimentos que ficaram presos
    como 'running' devido a falhas ou fechamentos abruptos anteriores.
    """

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

if __name__ == '__main__':
    print("Inicializando o banco de dados...")
    init_db()
    print("Fechando experimentos 'running' antigos (se houver)...")
    startup_cleanup()
    print("Banco de dados 'motor_data.db' pronto.")