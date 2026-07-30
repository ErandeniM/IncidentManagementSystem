"""
Pendientes del padre.

Reúne en una sola consulta todo lo que requiere su atención o que
cambió desde la última vez: incidencias sin firmar, avisos sin
confirmar, mensajes nuevos de la maestra y tareas por entregar.

Se usa para el menú que se despliega al tocar la campana.
"""

from repositorios.base import conexion, a_lista


def resumen(id_alumno):
    """
    Devuelve las novedades del padre, ya ordenadas por urgencia.

    Cada elemento trae: tipo, titulo, detalle, fecha, icono, color y url_filtro,
    para que el template solo tenga que pintarlas.
    """
    if not id_alumno:
        return {'items': [], 'total': 0}

    items = []

    with conexion() as conn:

        # ── Incidencias sin firmar ──
        filas = conn.execute('''
            SELECT i.id, i.tipo, i.nivel, i.fecha, i.descripcion
            FROM incidencias i
            LEFT JOIN incidencia_seguimiento s ON s.id_incidencia = i.id
            WHERE i.id_alumno = ?
              AND (s.enterado IS NULL OR s.enterado = 0)
            ORDER BY i.fecha DESC
        ''', (id_alumno,)).fetchall()

        for f in a_lista(filas):
            urgente = f['nivel'] == 'urgente'
            items.append({
                'tipo':    'incidencia',
                'id':      f['id'],
                'titulo':  'Incidencia por firmar',
                'detalle': (f['descripcion'] or '')[:60],
                'fecha':   f['fecha'],
                'icono':   'ti-alert-circle',
                'color':   '#ff4b4b' if urgente else '#ff9600',
                'orden':   0 if urgente else 1,
            })

        # ── Avisos sin confirmar ──
        filas = conn.execute('''
            SELECT a.id, a.titulo, a.contenido, a.fecha, a.fecha_actualizado
            FROM avisos a
            LEFT JOIN avisos_confirmaciones c
                ON c.id_aviso = a.id AND c.id_alumno = ?
            WHERE a.activo = 1 AND c.id IS NULL
            ORDER BY a.fecha DESC
        ''', (id_alumno,)).fetchall()

        for f in a_lista(filas):
            editado = bool(f['fecha_actualizado'])
            items.append({
                'tipo':    'aviso',
                'id':      f['id'],
                'titulo':  'Aviso actualizado' if editado else 'Aviso por confirmar',
                'detalle': f['titulo'],
                'fecha':   f['fecha_actualizado'] or f['fecha'],
                'icono':   'ti-speakerphone',
                'color':   '#1cb0f6',
                'orden':   2,
            })

        # ── Mensajes nuevos de la maestra ──
        fila = conn.execute('''
            SELECT COUNT(*) AS n, MAX(fecha) AS ultima
            FROM mensajes
            WHERE id_alumno = ? AND remitente = 'maestra' AND visto = 0
        ''', (id_alumno,)).fetchone()

        if fila and fila['n']:
            items.append({
                'tipo':    'mensaje',
                'id':      None,
                'titulo':  f'{fila["n"]} mensaje(s) de la maestra',
                'detalle': 'Toca para leerlos',
                'fecha':   fila['ultima'],
                'icono':   'ti-message-circle',
                'color':   '#58cc02',
                'orden':   3,
            })

        # ── Tareas con entrega próxima ──
        filas = conn.execute('''
            SELECT t.id, t.titulo, t.fecha_entrega, t.materia
            FROM tareas_entrega t
            LEFT JOIN entregas e
                ON e.id_tarea = t.id AND e.id_alumno = ?
            WHERE t.fecha_entrega >= date('now', 'localtime')
              AND (e.estado IS NULL OR e.estado = 'pendiente')
            ORDER BY t.fecha_entrega ASC
            LIMIT 5
        ''', (id_alumno,)).fetchall()

        for f in a_lista(filas):
            items.append({
                'tipo':    'tarea',
                'id':      f['id'],
                'titulo':  'Tarea por entregar',
                'detalle': f'{f["titulo"]} · entrega {f["fecha_entrega"]}',
                'fecha':   f['fecha_entrega'],
                'icono':   'ti-notebook',
                'color':   '#ffc107',
                'orden':   4,
            })

    # Primero lo urgente, luego lo más reciente
    items.sort(key=lambda x: (x['orden'], -(len(x['fecha'] or ''))))
    items.sort(key=lambda x: x['orden'])

    return {'lista': items, 'total': len(items)}
