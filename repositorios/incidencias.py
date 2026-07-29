"""
Repositorio de incidencias.

Incluye la tabla `incidencias` y su tabla de seguimiento
`incidencia_seguimiento`, porque siempre se consultan juntas.
"""

from repositorios.base import conexion, a_dict, a_lista, ahora

# ═══════════ LECTURA ═══════════

def de_alumno(id_alumno, mas_recientes_primero=True):
    """
    Incidencias de un alumno con su estado de seguimiento.
    Cada una lleva un número consecutivo por alumno.
    """
    with conexion() as conn:
        filas = conn.execute('''
            SELECT i.*, s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
                   s.comentario_padre, s.fecha_comentario, s.firmado_por
            FROM   incidencias i
            LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
            WHERE  i.id_alumno = ?
            ORDER  BY i.fecha ASC
        ''', (id_alumno,)).fetchall()

    lista = []
    for numero, fila in enumerate(a_lista(filas), start=1):
        fila['numero'] = numero
        lista.append(fila)

    if mas_recientes_primero:
        lista.reverse()
    return lista


def obtener(id_incidencia, id_alumno=None):
    """
    Una incidencia con su seguimiento.
    Si se pasa id_alumno, verifica que le pertenezca (evita que un padre
    vea incidencias de otro alumno cambiando el número en la dirección).
    """
    sql = '''
        SELECT i.*, s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
               s.comentario_padre, s.fecha_comentario, s.firmado_por
        FROM incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE i.id = ?
    '''
    parametros = [id_incidencia]

    if id_alumno is not None:
        sql += ' AND i.id_alumno = ?'
        parametros.append(id_alumno)

    with conexion() as conn:
        fila = conn.execute(sql, parametros).fetchone()
    return a_dict(fila)


def todas(filtro='todo'):
    """
    Todas las incidencias del grupo, con el nombre del alumno.
    filtro: 'todo', 'pendientes' o 'firmadas'.
    """
    with conexion() as conn:
        filas = conn.execute('''
            SELECT i.*, a.nombre AS nombre_alumno, a.curp,
                   s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
                   s.comentario_padre, s.firmado_por
            FROM incidencias i
            JOIN alumnos a ON i.id_alumno = a.id
            LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
            ORDER BY i.fecha DESC
        ''').fetchall()

    lista = a_lista(filas)

    if filtro == 'pendientes':
        return [i for i in lista if not i['enterado']]
    if filtro == 'firmadas':
        return [i for i in lista if i['enterado']]
    return lista


# ═══════════ CONTADORES ═══════════

def contar_sin_firmar():
    """Incidencias de todo el grupo que ningún padre ha firmado."""
    with conexion() as conn:
        return conn.execute('''
            SELECT COUNT(*) AS n FROM incidencias i
            LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
            WHERE s.enterado IS NULL OR s.enterado = 0
        ''').fetchone()['n']


def contar_logros(id_alumno):
    """Cuántos logros tiene registrados un alumno."""
    with conexion() as conn:
        return conn.execute('''
            SELECT COUNT(*) AS n FROM incidencias
            WHERE id_alumno = ? AND tipo = 'Logro'
        ''', (id_alumno,)).fetchone()['n']


def contar_firmadas(id_alumno):
    """Cuántas incidencias de un alumno ya firmó su tutor."""
    with conexion() as conn:
        return conn.execute('''
            SELECT COUNT(*) AS n FROM incidencias i
            JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
            WHERE i.id_alumno = ? AND s.enterado = 1
        ''', (id_alumno,)).fetchone()['n']


# ═══════════ ESCRITURA ═══════════
def crear(id_alumno, tipo, descripcion, accion_docente='', nivel='informativo'):
    """
    Registra una incidencia nueva.
    `tipo` clasifica el hecho; `nivel` indica qué tanta atención requiere.
    """
    with conexion() as conn:
        cur = conn.execute('''
            INSERT INTO incidencias
                (id_alumno, tipo, descripcion, accion_docente, nivel, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id_alumno, tipo, descripcion, accion_docente, nivel, ahora()))
        return cur.lastrowid


def marcar_visto(id_incidencia):
    """Registra que el padre abrió la incidencia."""
    with conexion() as conn:
        conn.execute('''
            INSERT INTO incidencia_seguimiento (id_incidencia, visto, fecha_visto)
            VALUES (?, 1, ?)
            ON CONFLICT(id_incidencia) DO UPDATE SET
                visto = 1, fecha_visto = excluded.fecha_visto
        ''', (id_incidencia, ahora()))


def firmar(id_incidencia, comentario, firmado_por):
    """Registra la firma de enterado con la respuesta del tutor."""
    momento = ahora()
    with conexion() as conn:
        conn.execute('''
            INSERT INTO incidencia_seguimiento
                (id_incidencia, enterado, fecha_enterado,
                 comentario_padre, fecha_comentario, firmado_por)
            VALUES (?, 1, ?, ?, ?, ?)
            ON CONFLICT(id_incidencia) DO UPDATE SET
                enterado         = 1,
                fecha_enterado   = excluded.fecha_enterado,
                comentario_padre = excluded.comentario_padre,
                fecha_comentario = excluded.fecha_comentario,
                firmado_por      = excluded.firmado_por
        ''', (id_incidencia, momento, comentario, momento, firmado_por))

def pertenece_a(id_incidencia, id_alumno):
    """Verifica que una incidencia sea de ese alumno."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT 1 FROM incidencias WHERE id = ? AND id_alumno = ?',
            (id_incidencia, id_alumno)
        ).fetchone()
    return fila is not None
# ═══════════ CATÁLOGOS ═══════════

TIPOS = [
    ('accidente',   'Accidente o lesión',        'ti-first-aid-kit',   '#ff4b4b'),
    ('salud',       'Malestar de salud',         'ti-thermometer',     '#ff9600'),
    ('conflicto',   'Conflicto entre compañeros','ti-users-group',     '#a855f7'),
    ('conducta',    'Conducta en clase',         'ti-alert-triangle',  '#e0a800'),
    ('emocional',   'Estado emocional',          'ti-mood-sad',        '#1cb0f6'),
    ('academico',   'Desempeño académico',       'ti-book',            '#7c3aed'),
    ('logro',       'Logro o reconocimiento',    'ti-star',            '#58cc02'),
    ('comunicacion','Comunicación general',      'ti-message',         '#777777'),
]

NIVELES = [
    ('informativo', 'Informativo',          '#7dd3fc'),
    ('seguimiento', 'Requiere seguimiento', '#ffc107'),
    ('urgente',     'Urgente',              '#ff4b4b'),
]


def etiqueta_tipo(clave):
    """Nombre legible de un tipo. Acepta los tipos viejos."""
    for c, etiqueta, _, _ in TIPOS:
        if c == clave:
            return etiqueta
    return clave or 'General'


def color_tipo(clave):
    for c, _, _, color in TIPOS:
        if c == clave:
            return color
    return '#777777'


def etiqueta_nivel(clave):
    for c, etiqueta, _ in NIVELES:
        if c == clave:
            return etiqueta
    return 'Informativo'

TIPOS_MAP = {c: {'etiqueta': e, 'icono': i, 'color': col} for c, e, i, col in TIPOS}
NIVELES_MAP = {c: {'etiqueta': e, 'color': col} for c, e, col in NIVELES}