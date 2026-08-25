import os
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash
from config import DATABASE as DATABASE_CONFIG


BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RUTA_SCHEMA = os.path.join(BASE_DIR, 'schema.sql')


def ruta_db():
    """
    Ruta de la base en uso.

    Se resuelve en cada llamada, no al importar: así las pruebas pueden
    apuntar a una base temporal con la variable de entorno MI_SALON_DB
    sin tocar la base real.
    """
    return os.environ.get('MI_SALON_DB') or DATABASE_CONFIG


def get_db():
    conn = sqlite3.connect(ruta_db())
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    """Genera un hash seguro (scrypt con sal aleatoria)."""
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
    if os.path.exists(ruta_db()):
        return

    print("Creando base de datos...")
    with open(RUTA_SCHEMA, 'r', encoding='utf-8') as f:
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