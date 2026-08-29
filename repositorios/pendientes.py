"""
Pendientes del padre.

Cuenta lo que requiere una acción suya y todavía no la ha hecho.

Regla importante: **abrir no reduce el contador**. Una incidencia baja
cuando se firma, un aviso cuando se confirma. Si bajara al abrir, el
número diría "ya se enteró" sin que exista constancia de nada, y esa
constancia es el propósito del sistema.

La única excepción son los mensajes: ahí no hay nada que firmar, así
que se descuentan al leerlos.
"""

from repositorios.base import conexion


def contadores(id_alumno):
    """
    Números para el menú lateral.

    Devuelve un diccionario con una llave por sección:
        avisos    → incidencias sin firmar + avisos sin confirmar
        tareas    → tareas cuya entrega no ha pasado por revisión
        mensajes  → mensajes de la maestra sin leer
        total     → la suma, por si se quiere un solo número
    """
    vacio = {'avisos': 0, 'tareas': 0, 'mensajes': 0, 'total': 0}
    if not id_alumno:
        return vacio

    with conexion() as conn:

        # Incidencias sin firma del tutor.
        # Se excluyen los logros: son para celebrar, no requieren acción.
        sin_firmar = conn.execute('''
            SELECT COUNT(*) AS n
            FROM incidencias i
            LEFT JOIN incidencia_seguimiento s ON s.id_incidencia = i.id
            WHERE i.id_alumno = ?
              AND i.tipo NOT IN ('logro', 'Logro')
              AND (s.enterado IS NULL OR s.enterado = 0)
        ''', (id_alumno,)).fetchone()['n']

        # Avisos generales que el tutor no ha confirmado
        sin_confirmar = conn.execute('''
            SELECT COUNT(*) AS n
            FROM avisos a
            LEFT JOIN avisos_confirmaciones c
                ON c.id_aviso = a.id AND c.id_alumno = ?
            WHERE a.activo = 1 AND c.id IS NULL
        ''', (id_alumno,)).fetchone()['n']

        # Tareas que la maestra todavía no revisa
        tareas = conn.execute('''
            SELECT COUNT(*) AS n
            FROM tareas_entrega t
            LEFT JOIN entregas e
                ON e.id_tarea = t.id AND e.id_alumno = ?
            WHERE e.estado IS NULL OR e.estado = 'pendiente'
        ''', (id_alumno,)).fetchone()['n']

        # Mensajes de la maestra sin leer
        mensajes = conn.execute('''
            SELECT COUNT(*) AS n
            FROM mensajes
            WHERE id_alumno = ? AND remitente = 'maestra' AND visto = 0
        ''', (id_alumno,)).fetchone()['n']

    avisos = sin_firmar + sin_confirmar

    return {
        'avisos':        avisos,
        'sin_firmar':    sin_firmar,
        'sin_confirmar': sin_confirmar,
        'tareas':        tareas,
        'mensajes':      mensajes,
        'total':         avisos + tareas + mensajes,
    }
