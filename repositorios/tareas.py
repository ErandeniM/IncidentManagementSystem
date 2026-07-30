"""
Repositorio de tareas de entrega.

A diferencia de las actividades personalizadas, las tareas tienen fecha
de entrega y la maestra lleva el registro de quién cumplió.

Tablas:
  · tareas_entrega  → la tarea en sí
  · entregas        → el estado de cada alumno frente a esa tarea
"""

from repositorios.base import conexion, a_dict, a_lista, ahora


# ═══════════ CATÁLOGOS ═══════════

ESTADOS = [
    ('pendiente',  'Pendiente',  '#afafaf', 'ti-clock'),
    ('cumplio',    'Cumplió',    '#58cc02', 'ti-check'),
    ('incompleta', 'Incompleta', '#ffc107', 'ti-alert-triangle'),
    ('no_cumplio', 'No cumplió', '#ff4b4b', 'ti-x'),
]

ESTADOS_MAP = {c: {'etiqueta': e, 'color': col, 'icono': i} for c, e, col, i in ESTADOS}

MATERIAS = [
    'Lenguajes',
    'Saberes y Pensamiento Científico',
    'Ética, Naturaleza y Sociedades',
    'De lo Humano y lo Comunitario',
    'General',
]


# ═══════════ LECTURA ═══════════

def todas():
    """
    Todas las tareas con su resumen de cumplimiento.
    Las más recientes primero.
    """
    with conexion() as conn:
        filas = conn.execute('''
            SELECT t.*,
                   (SELECT COUNT(*) FROM alumnos) AS total_alumnos,
                   SUM(CASE WHEN e.estado = 'cumplio'    THEN 1 ELSE 0 END) AS cumplieron,
                   SUM(CASE WHEN e.estado = 'incompleta' THEN 1 ELSE 0 END) AS incompletas,
                   SUM(CASE WHEN e.estado = 'no_cumplio' THEN 1 ELSE 0 END) AS no_cumplieron
            FROM tareas_entrega t
            LEFT JOIN entregas e ON e.id_tarea = t.id
            GROUP BY t.id
            ORDER BY t.fecha_entrega DESC, t.id DESC
        ''').fetchall()

    lista = []
    for t in a_lista(filas):
        total = t['total_alumnos'] or 0
        t['cumplieron']    = t['cumplieron'] or 0
        t['incompletas']   = t['incompletas'] or 0
        t['no_cumplieron'] = t['no_cumplieron'] or 0
        t['revisados']     = t['cumplieron'] + t['incompletas'] + t['no_cumplieron']
        t['porcentaje']    = round(t['cumplieron'] * 100 / total) if total else 0
        lista.append(t)
    return lista


def obtener(id_tarea):
    """Una tarea, o None si no existe."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT * FROM tareas_entrega WHERE id = ?', (id_tarea,)
        ).fetchone()
    return a_dict(fila)


def lista_revision(id_tarea):
    """
    Todos los alumnos con su estado frente a una tarea.
    Los que no tienen registro salen como 'pendiente'.
    """
    with conexion() as conn:
        filas = conn.execute('''
            SELECT a.id, a.nombre, a.curp,
                   COALESCE(e.estado, 'pendiente') AS estado,
                   e.nota, e.fecha_registro
            FROM alumnos a
            LEFT JOIN entregas e
                ON e.id_alumno = a.id AND e.id_tarea = ?
            ORDER BY a.nombre
        ''', (id_tarea,)).fetchall()
    return a_lista(filas)


def de_alumno(id_alumno):
    """Historial de tareas de un alumno con su estado en cada una."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT t.*, COALESCE(e.estado, 'pendiente') AS estado, e.nota
            FROM tareas_entrega t
            LEFT JOIN entregas e
                ON e.id_tarea = t.id AND e.id_alumno = ?
            ORDER BY t.fecha_entrega DESC, t.id DESC
        ''', (id_alumno,)).fetchall()
    return a_lista(filas)


def resumen_alumno(id_alumno):
    """Cuántas tareas cumplió, entregó incompletas o no cumplió."""
    with conexion() as conn:
        fila = conn.execute('''
            SELECT
                (SELECT COUNT(*) FROM tareas_entrega) AS total,
                SUM(CASE WHEN e.estado = 'cumplio'    THEN 1 ELSE 0 END) AS cumplio,
                SUM(CASE WHEN e.estado = 'incompleta' THEN 1 ELSE 0 END) AS incompleta,
                SUM(CASE WHEN e.estado = 'no_cumplio' THEN 1 ELSE 0 END) AS no_cumplio
            FROM entregas e
            WHERE e.id_alumno = ?
        ''', (id_alumno,)).fetchone()

    d = a_dict(fila) or {}
    total = d.get('total') or 0
    d['cumplio']    = d.get('cumplio') or 0
    d['incompleta'] = d.get('incompleta') or 0
    d['no_cumplio'] = d.get('no_cumplio') or 0
    d['total']      = total
    d['porcentaje'] = round(d['cumplio'] * 100 / total) if total else 0
    return d


def proximas(limite=5):
    """Tareas cuya fecha de entrega aún no pasa."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT * FROM tareas_entrega
            WHERE fecha_entrega >= date('now', 'localtime')
            ORDER BY fecha_entrega ASC
            LIMIT ?
        ''', (limite,)).fetchall()
    return a_lista(filas)


# ═══════════ ESCRITURA ═══════════

def crear(titulo, descripcion='', materia='General', fecha_entrega=None):
    """Publica una tarea para todo el grupo."""
    with conexion() as conn:
        cur = conn.execute('''
            INSERT INTO tareas_entrega
                (titulo, descripcion, materia, fecha_asignada, fecha_entrega)
            VALUES (?, ?, ?, ?, ?)
        ''', (titulo, descripcion, materia, ahora(), fecha_entrega))
        return cur.lastrowid


def editar(id_tarea, titulo, descripcion, materia, fecha_entrega):
    """Actualiza los datos de una tarea sin tocar las entregas."""
    with conexion() as conn:
        conn.execute('''
            UPDATE tareas_entrega
            SET titulo = ?, descripcion = ?, materia = ?, fecha_entrega = ?
            WHERE id = ?
        ''', (titulo, descripcion, materia, fecha_entrega, id_tarea))


def eliminar(id_tarea):
    """Borra una tarea junto con sus entregas."""
    with conexion() as conn:
        conn.execute('DELETE FROM entregas WHERE id_tarea = ?', (id_tarea,))
        conn.execute('DELETE FROM tareas_entrega WHERE id = ?', (id_tarea,))


def marcar(id_tarea, id_alumno, estado, nota=''):
    """Registra el estado de un alumno frente a una tarea."""
    with conexion() as conn:
        conn.execute('''
            INSERT INTO entregas
                (id_tarea, id_alumno, estado, nota, fecha_registro)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id_tarea, id_alumno) DO UPDATE SET
                estado         = excluded.estado,
                nota           = excluded.nota,
                fecha_registro = excluded.fecha_registro
        ''', (id_tarea, id_alumno, estado, nota, ahora()))


def marcar_todos(id_tarea, estado):
    """
    Aplica el mismo estado a todo el grupo.
    Útil para marcar 'cumplió' a todos y luego corregir las excepciones.
    """
    momento = ahora()
    with conexion() as conn:
        ids = [f['id'] for f in conn.execute('SELECT id FROM alumnos').fetchall()]
        conn.executemany('''
            INSERT INTO entregas
                (id_tarea, id_alumno, estado, fecha_registro)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id_tarea, id_alumno) DO UPDATE SET
                estado         = excluded.estado,
                fecha_registro = excluded.fecha_registro
        ''', [(id_tarea, i, estado, momento) for i in ids])
    return len(ids)
