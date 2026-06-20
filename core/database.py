"""
Módulo de Gerenciamento de Banco de Dados (SQLite).

Responsável por todas as operações de persistência de dados. Implementa 
configurações de alto desempenho (WAL) e resolução de caminho absoluto
para assegurar a integridade dos dados independente do diretório de chamada.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

# Resolução dinâmica do caminho absoluto base do projeto.
# Garante a convergência para o mesmo ficheiro físico 'motor_data.db' na raiz do projeto.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "motor_data.db")

current_run_id: Optional[int] = None
is_recording_enabled: bool = False


def _create_new_experiment() -> Optional[int]:
    """
    Cria um novo registo na tabela 'experimentos' e define o status como 'running'.
    
    Returns:
        Optional[int]: O ID do novo experimento alocado, ou None em caso de falha.
    """
    global current_run_id
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        timestamp_inicio = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO experimentos (timestamp_inicio, status) VALUES (?, 'running')", 
            (timestamp_inicio,)
        )

        new_id = cursor.lastrowid
        conn.commit()
        conn.close()

        current_run_id = new_id
        print(f"--- NOVO EXPERIMENTO INICIADO --- ID: {current_run_id} ---")
        return new_id
    except Exception as e:
        print(f"ERRO ao alocar novo experimento: {e}")
        return None


def is_experiment_running() -> bool:
    """Verifica se há um experimento ativo com permissão de persistência I/O."""
    global current_run_id, is_recording_enabled
    return (current_run_id is not None) and is_recording_enabled


def start_new_experiment() -> None:
    """Inicia um novo ciclo de gravação, encerrando o anterior de forma segura."""
    global is_recording_enabled
    print("DB: Solicitação de inicialização de persistência...")
    close_current_experiment() 
    is_recording_enabled = True
    print("DB: Gravação I/O ATIVADA.")
    _create_new_experiment()


def close_current_experiment() -> None:
    """Consolida os metadados do experimento corrente e cessa a gravação I/O."""
    global current_run_id, is_recording_enabled

    is_recording_enabled = False
    print("DB: Gravação I/O SUSPENSA.")

    if current_run_id is None:
        return

    print(f"Consolidando metadados do experimento ID: {current_run_id}...")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        timestamp_fim = datetime.now().isoformat()
        
        cursor.execute(
            "SELECT timestamp_recebimento FROM telemetria WHERE id_experimento = ? ORDER BY timestamp_recebimento DESC LIMIT 1", 
            (current_run_id,)
        )
        last_telemetry_time = cursor.fetchone()

        if last_telemetry_time:
            timestamp_fim = last_telemetry_time[0]

        cursor.execute(
            "UPDATE experimentos SET timestamp_fim = ?, status = 'completed' WHERE id = ?", 
            (timestamp_fim, current_run_id)
        )

        conn.commit()
        conn.close()
        print(f"--- EXPERIMENTO CONCLUÍDO E INDEXADO --- ID: {current_run_id} ---")
        current_run_id = None
    except Exception as e:
        print(f"ERRO ao consolidar experimento {current_run_id}: {e}")


def init_db() -> None:
    """
    Inicializa a estrutura DDL (Data Definition Language) do SQLite.
    Aplica Pragmáticas industriais para otimização do motor de base de dados.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA cache_size=-64000;")

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
            tensao_estimada_mv REAL,
            erro_obs_mv REAL,
            estado_1 REAL, 
            estado_2 REAL, 
            estado_3 REAL,
            FOREIGN KEY (id_experimento) REFERENCES experimentos (id)
        )
    """)

    for col, def_type in [
        ("timestamp_fim", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'running'"),
        ("tensao_estimada_mv", "REAL"),
        ("erro_obs_mv", "REAL"),
        ("estado_1", "REAL"),
        ("estado_2", "REAL"),
        ("estado_3", "REAL")
    ]:
        try:
            cursor.execute(f"ALTER TABLE experimentos ADD COLUMN {col} {def_type}")
        except sqlite3.OperationalError:
            try:
                cursor.execute(f"ALTER TABLE telemetria ADD COLUMN {col} {def_type}")
            except sqlite3.OperationalError:
                pass

    conn.commit()
    conn.close()


def insert_data_batch(batch_data: List[Dict[str, Any]]) -> None:
    """
    Executa a injeção em lote (Bulk Insert) de estruturas de telemetria.

    Args:
        batch_data (List[Dict[str, Any]]): Vetor de dicionários contendo métricas.
    """
    if not batch_data:
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        tuples_to_insert = []
        for data in batch_data:
            exp_id = data.get('id_experimento') or current_run_id
                
            if exp_id is not None:
                tuples_to_insert.append((
                    exp_id,
                    data.get("timestamp_recebimento"),
                    data.get("timestamp_amostra_ms"),
                    data.get("valor_adc"),
                    data.get("tensao_mv"),
                    data.get("sinal_controle"),
                    data.get("tensao_estimada_mv"),
                    data.get("erro_obs_mv"),
                    data.get("estado_1"),
                    data.get("estado_2"),
                    data.get("estado_3")
                ))

        if tuples_to_insert:
            cursor.executemany("""
                INSERT INTO telemetria (
                    id_experimento, timestamp_recebimento, timestamp_amostra_ms, 
                    valor_adc, tensao_mv, sinal_controle, tensao_estimada_mv, erro_obs_mv,
                    estado_1, estado_2, estado_3
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuples_to_insert)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERRO DE I/O: Falha na transação em lote: {e}")


def get_completed_experiments() -> List[Dict[str, Any]]:
    """Consulta os metadados privados das operações consolidadas."""
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
                experimentos.append({
                    "id": row[0],
                    "inicio_str": inicio.strftime("%d/%m/%Y às %H:%M:%S"),
                    "fim_str": fim.strftime("%H:%M:%S"),
                    "duracao_str": f"{minutos}m {segundos}s",
                    "nome": f"Experimento #{row[0]}"
                })
            except Exception: pass

        conn.close()
        return experimentos
    except Exception as e:
        return []


def get_telemetry_for_experiment(exp_id: int) -> List[Dict[str, Any]]:
    """Extração de matriz de telemetria estruturada para análise analítica."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp_amostra_ms, valor_adc, tensao_mv, sinal_controle, tensao_estimada_mv, erro_obs_mv, estado_1, estado_2, estado_3
            FROM telemetria 
            WHERE id_experimento = ?
            ORDER BY timestamp_amostra_ms ASC
        """, (exp_id,))
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return data
    except Exception:
        return []


def delete_experiment(exp_id: int) -> bool:
    """Expurga as referências e dependências I/O associadas a um ID de sessão."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM telemetria WHERE id_experimento = ?", (exp_id,))
        cursor.execute("DELETE FROM experimentos WHERE id = ?", (exp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def startup_cleanup() -> None:
    """Rotina de salvaguarda para corrupção transacional prévia."""
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
    except Exception:
        pass