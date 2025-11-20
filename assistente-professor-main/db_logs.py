import sqlite3
from datetime import datetime

DB_PATH = "logs.db"

def registrar_log(usuario, pergunta, resposta, contexto, tipo_prompt, modulo=None, aula=None, data=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            pergunta TEXT,
            resposta TEXT,
            contexto TEXT,
            tipo_prompt TEXT,
            modulo TEXT,
            aula TEXT,
            data TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if data is None:
        data = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO logs (usuario, pergunta, resposta, contexto, tipo_prompt, modulo, aula, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (usuario, pergunta, resposta, contexto, tipo_prompt, modulo, aula, data))

    conn.commit()
    conn.close()
