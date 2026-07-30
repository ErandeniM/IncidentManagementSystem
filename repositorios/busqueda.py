"""
Búsqueda global.

Busca el mismo texto en alumnos, incidencias, avisos, mensajes y tareas,
y devuelve los resultados agrupados por tipo.
"""

from repositorios.base import conexion, a_lista

LIMITE = 8   # resultados por categoría


def _patron(texto):
    """Prepara el texto para usarlo con LIKE."""
    return f'%{texto.strip()}%'


def buscar(texto):
    """
    Busca en todo el sistema.
    Devuelve un diccionario con una lista por cada categoría.
    """
    texto = (texto or '').strip()
    if len(texto) < 2:
        return {'alumnos': [], 'incidencias': [], 'avisos': [],
                'mensajes': [], 'tareas': [], 'total': 0}

    p = _patron(texto)

    with conexion() as conn:

        alumnos = conn.execute('''
            SELECT id, nombre, curp, nombre_tutor, correo_padre
            FROM alumnos
            WHERE nombre LIKE ? OR curp LIKE ?
               OR nombre_tutor LIKE ? OR correo_padre LIKE ?
            ORDER BY nombre
            LIMIT ?
        ''', (p, p, p, p, LIMITE)).fetchall()

        incidencias = conn.execute('''
            SELECT i.id, i.id_alumno, i.tipo, i.nivel, i.fecha,
                   i.descripcion, i.accion_docente,
                   a.nombre AS nombre_alumno
            FROM incidencias i
            JOIN alumnos a ON a.id = i.id_alumno
            WHERE i.descripcion LIKE ? OR i.accion_docente LIKE ?
               OR a.nombre LIKE ?
            ORDER BY i.fecha DESC
            LIMIT ?
        ''', (p, p, p, LIMITE)).fetchall()

        avisos = conn.execute('''
            SELECT id, titulo, contenido, fecha, fecha_actualizado
            FROM avisos
            WHERE titulo LIKE ? OR contenido LIKE ?
            ORDER BY fecha DESC
            LIMIT ?
        ''', (p, p, LIMITE)).fetchall()

        mensajes = conn.execute('''
            SELECT m.id, m.id_alumno, m.remitente, m.contenido,
                   m.fecha, m.ref_titulo,
                   a.nombre AS nombre_alumno
            FROM mensajes m
            JOIN alumnos a ON a.id = m.id_alumno
            WHERE m.contenido LIKE ? OR a.nombre LIKE ?
            ORDER BY m.fecha DESC
            LIMIT ?
        ''', (p, p, LIMITE)).fetchall()

        tareas = conn.execute('''
            SELECT id, titulo, descripcion, materia, fecha_entrega
            FROM tareas_entrega
            WHERE titulo LIKE ? OR descripcion LIKE ? OR materia LIKE ?
            ORDER BY fecha_entrega DESC
            LIMIT ?
        ''', (p, p, p, LIMITE)).fetchall()

    resultado = {
        'alumnos':     a_lista(alumnos),
        'incidencias': a_lista(incidencias),
        'avisos':      a_lista(avisos),
        'mensajes':    a_lista(mensajes),
        'tareas':      a_lista(tareas),
    }
    resultado['total'] = sum(len(v) for v in resultado.values())
    return resultado
