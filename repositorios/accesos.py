"""
Repositorio del registro de accesos.
"""

from repositorios.base import conexion, a_lista


def registrar(id_alumno, ip):
    """Guarda un ingreso al portal."""
    with conexion() as conn:
        conn.execute(
            'INSERT INTO registro_accesos (id_alumno, ip) VALUES (?, ?)',
            (id_alumno, ip)
        )


def ultimos_de_alumno(id_alumno, limite=10):
    """Últimos accesos de un padre, para su pantalla de Configuración."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT fecha, ip FROM registro_accesos
            WHERE id_alumno = ?
            ORDER BY fecha DESC
            LIMIT ?
        ''', (id_alumno, limite)).fetchall()
    return a_lista(filas)


def todos(limite=100):
    """Historial completo para el panel de la maestra."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT a.nombre, a.curp, r.fecha, r.ip
            FROM registro_accesos r
            JOIN alumnos a ON r.id_alumno = a.id
            ORDER BY r.fecha DESC
            LIMIT ?
        ''', (limite,)).fetchall()
    return a_lista(filas)