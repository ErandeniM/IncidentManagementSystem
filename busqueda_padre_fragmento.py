def buscar_del_padre(id_alumno, texto):
    """
    Busca solo dentro de lo que le corresponde a un alumno.

    A diferencia de la búsqueda de la maestra, aquí nunca se devuelven
    datos de otros alumnos: las incidencias, mensajes y actividades se
    filtran por `id_alumno`, y los avisos y tareas son del grupo entero.
    """
    texto = (texto or '').strip()
    if len(texto) < 2 or not id_alumno:
        return {'incidencias': [], 'avisos': [], 'mensajes': [],
                'tareas': [], 'actividades': [], 'total': 0}

    p = _patron(texto)

    with conexion() as conn:

        incidencias = conn.execute('''
            SELECT i.id, i.tipo, i.nivel, i.fecha, i.descripcion,
                   i.accion_docente, s.enterado
            FROM incidencias i
            LEFT JOIN incidencia_seguimiento s ON s.id_incidencia = i.id
            WHERE i.id_alumno = ?
              AND (i.descripcion LIKE ? OR i.accion_docente LIKE ?)
            ORDER BY i.fecha DESC
            LIMIT ?
        ''', (id_alumno, p, p, LIMITE)).fetchall()

        avisos = conn.execute('''
            SELECT a.id, a.titulo, a.contenido, a.fecha,
                   CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END AS confirmado
            FROM avisos a
            LEFT JOIN avisos_confirmaciones c
                ON c.id_aviso = a.id AND c.id_alumno = ?
            WHERE a.activo = 1 AND (a.titulo LIKE ? OR a.contenido LIKE ?)
            ORDER BY a.fecha DESC
            LIMIT ?
        ''', (id_alumno, p, p, LIMITE)).fetchall()

        mensajes = conn.execute('''
            SELECT id, remitente, contenido, fecha, ref_titulo
            FROM mensajes
            WHERE id_alumno = ? AND contenido LIKE ?
            ORDER BY fecha DESC
            LIMIT ?
        ''', (id_alumno, p, LIMITE)).fetchall()

        tareas = conn.execute('''
            SELECT t.id, t.titulo, t.descripcion, t.materia, t.fecha_entrega,
                   COALESCE(e.estado, 'pendiente') AS estado
            FROM tareas_entrega t
            LEFT JOIN entregas e
                ON e.id_tarea = t.id AND e.id_alumno = ?
            WHERE t.titulo LIKE ? OR t.descripcion LIKE ? OR t.materia LIKE ?
            ORDER BY t.fecha_entrega DESC
            LIMIT ?
        ''', (id_alumno, p, p, p, LIMITE)).fetchall()

        actividades = conn.execute('''
            SELECT id, actividad, categoria, fecha
            FROM actividades_recomendadas
            WHERE id_alumno = ? AND (actividad LIKE ? OR categoria LIKE ?)
            ORDER BY fecha DESC
            LIMIT ?
        ''', (id_alumno, p, p, LIMITE)).fetchall()

    resultado = {
        'incidencias': a_lista(incidencias),
        'avisos':      a_lista(avisos),
        'mensajes':    a_lista(mensajes),
        'tareas':      a_lista(tareas),
        'actividades': a_lista(actividades),
    }
    resultado['total'] = sum(len(v) for v in resultado.values())
    return resultado
