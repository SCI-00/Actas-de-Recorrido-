import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "nom019.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS hallazgos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_sesion TEXT,
            fecha_hallazgo DATE,
            cedis TEXT,
            estado_geo TEXT, 
            hallazgo TEXT,
            tipo_hallazgo TEXT, 
            riesgo TEXT, 
            acciones_inmediatas TEXT,
            fecha_compromiso DATE,
            responsable TEXT,
            estatus TEXT,
            evidencia_path TEXT,
            fecha_registro TIMESTAMP
        )
    ''')
    try:
        c.execute("ALTER TABLE hallazgos ADD COLUMN riesgo TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE hallazgos ADD COLUMN estado_geo TEXT")
    except: pass
    
    conn.commit()
    conn.close()

def add_finding(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Check duplicates based on Description + Date + CEDIS to avoid re-insertion
        c.execute("SELECT id FROM hallazgos WHERE hallazgo=? AND fecha_hallazgo=? AND cedis=?", 
                  (data.get('hallazgo'), data.get('fecha_hallazgo'), data.get('cedis')))
        if c.fetchone():
            return False # Skip duplicate

        c.execute('''
            INSERT INTO hallazgos (
                numero_sesion, fecha_hallazgo, cedis, estado_geo, hallazgo, tipo_hallazgo,
                riesgo, acciones_inmediatas, fecha_compromiso, responsable, estatus, 
                evidencia_path, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('numero_sesion'),
            data.get('fecha_hallazgo'),
            data.get('cedis'),
            data.get('estado_geo', ''),
            data.get('hallazgo'),
            data.get('tipo_hallazgo'),
            data.get('riesgo', 'Bajo'),
            data.get('acciones_inmediatas'),
            data.get('fecha_compromiso'),
            data.get('responsable'),
            data.get('estatus', 'Abierto'),
            data.get('evidencia_path', None),
            datetime.now()
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error DB Add: {e}")
        return False
    finally:
        conn.close()

def get_findings(filters=None):
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM hallazgos"
    params = []
    
    if filters:
        conditions = []
        for key, value in filters.items():
            if value:
                if isinstance(value, list):
                    placeholders = ','.join(['?'] * len(value))
                    conditions.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_finding(id_hallazgo, data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Dynamic update
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(id_hallazgo)
        query = f"UPDATE hallazgos SET {', '.join(fields)} WHERE id = ?"
        c.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error Update: {e}")
        return False
    finally:
        conn.close()

def delete_finding(id_hallazgo):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM hallazgos WHERE id = ?", (id_hallazgo,))
    conn.commit()
    conn.close()
