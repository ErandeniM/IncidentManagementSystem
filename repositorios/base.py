"""
Base de la capa de repositorios.

Un repositorio es el único lugar donde vive el SQL de una tabla.
Las rutas piden datos aquí y nunca escriben consultas.

El administrador de contexto abre la conexión, confirma los cambios
y la cierra sola — aunque ocurra un error a la mitad.
"""

from contextlib import contextmanager
from database import get_db
from datetime import datetime



@contextmanager
def conexion():
    """
    Uso:
        with conexion() as conn:
            filas = conn.execute('SELECT ...').fetchall()
    """
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def a_dict(fila):
    """Convierte una fila de SQLite en diccionario. Devuelve None si no hay fila."""
    return dict(fila) if fila else None


def a_lista(filas):
    """Convierte varias filas en lista de diccionarios."""
    return [dict(f) for f in filas]

def ahora():
    """
    Fecha y hora local del equipo, en el formato que usa SQLite.
    Se usa en lugar de CURRENT_TIMESTAMP, que guarda en UTC.
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')