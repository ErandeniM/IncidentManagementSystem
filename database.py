import sqlite3
import hashlib
import os
from config import DATABASE
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Genera un hash seguro (PBKDF2 con sal aleatoria)."""
    return generate_password_hash(password)


def verificar_password(password, hash_guardado):
    """
    Verifica la contraseña.
    Acepta hashes viejos (SHA-256) para no romper cuentas existentes.
    Devuelve (es_valida, necesita_actualizar).
    """
    if not hash_guardado:
        return False, False

    # Hash viejo: 64 caracteres hexadecimales
    if len(hash_guardado) == 64 and all(c in '0123456789abcdef' for c in hash_guardado.lower()):
        import hashlib
        valida = hashlib.sha256(password.encode()).hexdigest() == hash_guardado
        return valida, valida   # si es válida, hay que re-hashear

    return check_password_hash(hash_guardado, password), False

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
