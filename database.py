import sqlite3
import hashlib
import os
from config import DATABASE


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    if not os.path.exists(DATABASE):
        print("Creando base de datos...")
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema = f.read()
        conn = get_db()
        conn.executescript(schema)
        conn.execute(
            'INSERT INTO alumnos (curp, nombre, password_hash) VALUES (?, ?, ?)',
            ('MABC010101', 'María G.', hash_password('maria2024'))
        )
        conn.commit()
        conn.close()
        print("Base de datos creada con alumno de ejemplo: CURP=MABC010101 / pass=maria2024")
