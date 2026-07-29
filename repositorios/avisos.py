"""
Repositorio de avisos.

Cubre tres tablas relacionadas:
  · avisos                 → comunicados que publica la maestra
  · avisos_confirmaciones  → qué padre confirmó qué aviso
  · avisos_padre           → avisos logísticos que manda el padre
"""

from repositorios.base import conexion, a_dict, a_lista, ahora


# ═══════════ AVISOS GENERALES ═══════════

def todos():
    """Todos los avisos publicados, del más reciente al más viejo."""
    with conexion() as conn:
        filas = conn.execute(
            'SELECT * FROM avisos ORDER BY fecha DESC'
        ).fetchall()
    return a_lista(filas)


def obtener(id_aviso):
    """Un aviso, o None si no existe."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT * FROM avisos WHERE id = ?', (id_aviso,)
        ).fetchone()
    return a_dict(fila)


def activos_para(id_alumno):
    """
    Avisos activos, marcando cuáles ya confirmó ese padre.
    Agrega el campo `confirmado_por_padre`.
    """
    with conexion() as conn:
        filas = conn.execute('''
            SELECT a.*,
                   CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END AS confirmado_por_padre
            FROM avisos a
            LEFT JOIN avisos_confirmaciones c
                ON c.id_aviso = a.id AND c.id_alumno = ?
            WHERE a.activo = 1
            ORDER BY a.fecha DESC
        ''', (id_alumno,)).fetchall()
    return a_lista(filas)


def crear(titulo, contenido):
    """Publica un aviso nuevo."""
    with conexion() as conn:
        cur = conn.execute(
            'INSERT INTO avisos (titulo, contenido, fecha) VALUES (?, ?, ?)',
            (titulo, contenido, ahora())
        )
        return cur.lastrowid


def editar(id_aviso, titulo, contenido):
    """
    Actualiza un aviso y borra sus confirmaciones,
    porque los padres deben volver a confirmarlo.
    """
    with conexion() as conn:
        conn.execute('''
            UPDATE avisos
            SET titulo = ?, contenido = ?, fecha_actualizado = ?
            WHERE id = ?
        ''', (titulo, contenido, ahora(), id_aviso))
        conn.execute(
            'DELETE FROM avisos_confirmaciones WHERE id_aviso = ?', (id_aviso,)
        )


def eliminar(id_aviso):
    """Borra un aviso junto con sus confirmaciones."""
    with conexion() as conn:
        conn.execute('DELETE FROM avisos_confirmaciones WHERE id_aviso = ?', (id_aviso,))
        conn.execute('DELETE FROM avisos WHERE id = ?', (id_aviso,))


# ═══════════ CONFIRMACIONES ═══════════

def confirmar(id_aviso, id_alumno):
    """Registra que un padre confirmó haber leído el aviso."""
    with conexion() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO avisos_confirmaciones
                (id_aviso, id_alumno, fecha_confirmado)
            VALUES (?, ?, ?)
        ''', (id_aviso, id_alumno, ahora()))


def quien_confirmo(id_aviso):
    """Padres que ya confirmaron, con la fecha en que lo hicieron."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT a.id, a.nombre, a.curp, c.fecha_confirmado
            FROM alumnos a
            JOIN avisos_confirmaciones c ON c.id_alumno = a.id
            WHERE c.id_aviso = ?
            ORDER BY c.fecha_confirmado DESC
        ''', (id_aviso,)).fetchall()
    return a_lista(filas)


def quien_falta(id_aviso):
    """Padres que todavía no confirman."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT a.id, a.nombre, a.curp
            FROM alumnos a
            WHERE a.id NOT IN (
                SELECT id_alumno FROM avisos_confirmaciones WHERE id_aviso = ?
            )
            ORDER BY a.nombre
        ''', (id_aviso,)).fetchall()
    return a_lista(filas)


# ═══════════ AVISOS DEL PADRE ═══════════

TIPOS_PADRE = [
    ('temprano', 'Paso temprano'),
    ('noasiste', 'No asistirá'),
    ('tarde',    'Llegará tarde'),
    ('tutor',    'Cambio de tutor'),
    ('salud',    'Estado de salud'),
    ('otro',     'Otro aviso'),
]


def crear_de_padre(id_alumno, tipo, detalle='', fecha_aplica=None, hora_aplica=None):
    """Guarda un aviso logístico enviado por el padre."""
    with conexion() as conn:
        cur = conn.execute('''
            INSERT INTO avisos_padre
                (id_alumno, tipo, detalle, fecha_aplica, hora_aplica, fecha_creado)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id_alumno, tipo, detalle, fecha_aplica, hora_aplica, ahora()))
        return cur.lastrowid


def de_padre(id_alumno):
    """Historial de avisos que ha enviado un padre."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT * FROM avisos_padre
            WHERE id_alumno = ?
            ORDER BY fecha_creado DESC
        ''', (id_alumno,)).fetchall()
    return a_lista(filas)


def todos_de_padres(limite=100):
    """Avisos de todos los padres, para el panel de la maestra."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT ap.*, a.nombre AS nombre_alumno
            FROM avisos_padre ap
            JOIN alumnos a ON ap.id_alumno = a.id
            ORDER BY ap.fecha_creado DESC
            LIMIT ?
        ''', (limite,)).fetchall()
    return a_lista(filas)


def marcar_vistos_por_maestra():
    """Marca como leídos todos los avisos pendientes de los padres."""
    with conexion() as conn:
        conn.execute('''
            UPDATE avisos_padre
            SET visto_maestra = 1, fecha_visto = ?
            WHERE visto_maestra = 0
        ''', (ahora(),))


def contar_pendientes_de_padres():
    """Cuántos avisos de padres no ha leído la maestra."""
    with conexion() as conn:
        return conn.execute(
            'SELECT COUNT(*) AS n FROM avisos_padre WHERE visto_maestra = 0'
        ).fetchone()['n']
