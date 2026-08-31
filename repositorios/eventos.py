"""
Calendario escolar.

Combina dos fuentes: las fechas del calendario oficial de la SEC Sonora
para el ciclo 2026-2027, que se precargan una sola vez, y los eventos
internos que la docente agrega durante el año.

Las fechas oficiales no se pueden editar ni borrar desde el sistema: si
la autoridad publica un ajuste, se corrige aquí y se vuelve a cargar.
"""

from repositorios.base import conexion, a_dict, a_lista, ahora


# ── Tipos de evento ──────────────────────────────────────────
#    (clave, etiqueta, icono, color, hay_clases)

TIPOS = [
    ('inicio',      'Inicio de clases',      'ti-flag',            'var(--verde)',    1),
    ('fin',         'Fin de clases',         'ti-flag-check',      'var(--verde)',    1),
    ('suspension',  'Suspensión de labores', 'ti-calendar-off',    'var(--coral)',    0),
    ('receso',      'Receso de clases',      'ti-beach',           'var(--azul)',     0),
    ('vacaciones',  'Vacaciones',            'ti-sun',             'var(--amarillo)', 0),
    ('consejo',     'Consejo Técnico',       'ti-users-group',     'var(--morado)',   0),
    ('evaluacion',  'Evaluación',            'ti-clipboard-check', 'var(--azul)',     1),
    ('conmemora',   'Fecha conmemorativa',   'ti-star',            'var(--naranja)',  1),
    ('junta',       'Junta de padres',       'ti-users',           'var(--morado)',   1),
    ('escuela',     'Actividad de la escuela', 'ti-confetti',      'var(--rosa)',     1),
    ('jornada',     'Jornada de concientización', 'ti-shield-heart', 'var(--azul)',     1),
    ('escuela',     'Actividad de la escuela', 'ti-confetti',      'var(--rosa)',    1),
    ('festival',    'Festival',          'ti-confetti',   'var(--rosa)',   1),
    ('honores',     'Honores a la bandera', 'ti-flag-3',  'var(--azul)',   1)]

TIPOS_MAP = {
    clave: {'etiqueta': etiqueta, 'icono': icono,
            'color': color, 'hay_clases': hay_clases}
    for clave, etiqueta, icono, color, hay_clases in TIPOS
}

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def etiqueta_tipo(clave):
    return TIPOS_MAP.get(clave, {}).get('etiqueta', 'Evento')


# ── Calendario oficial SEC Sonora 2026-2027 ──────────────────
#    (fecha, fecha_fin, titulo, tipo)
#    fecha_fin en None significa un solo día.

CALENDARIO_OFICIAL = [
    # Agosto 2026
    ('2026-08-01', '2026-08-28', 'Receso de clases',                    'receso'),
    ('2026-08-24', '2026-08-28', 'Consejo Técnico — fase intensiva',    'consejo'),
    ('2026-08-31', None,         'Inicio de clases del ciclo 2026-2027', 'inicio'),

    # Septiembre 2026
    ('2026-09-07', None, 'Jornada sobre prevención del abuso infantil', 'jornada'),
    ('2026-09-15', None, 'Reflexión — Independencia de México',         'conmemora'),
    ('2026-09-16', None, 'Aniversario de la Independencia de México',   'conmemora'),
    ('2026-09-25', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Octubre 2026
    ('2026-10-30', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Noviembre 2026
    ('2026-11-02', None, 'Conmemoración tradicional',                   'suspension'),
    ('2026-11-13', None, 'Registro de calificaciones',                  'evaluacion'),
    ('2026-11-16', None, 'Conmemoración de la Revolución Mexicana',     'suspension'),
    ('2026-11-20', None, 'Reflexión — Revolución Mexicana',             'conmemora'),
    ('2026-11-23', '2026-11-26', 'Resultados de la evaluación',         'evaluacion'),
    ('2026-11-27', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Diciembre 2026
    ('2026-12-21', '2027-01-06', 'Vacaciones de invierno',              'vacaciones'),
    ('2026-12-25', None, 'Conmemoración tradicional',                   'suspension'),

    # Enero 2027
    ('2027-01-01', None, 'Conmemoración tradicional',                   'suspension'),
    ('2027-01-06', None, 'Conmemoración tradicional',                   'suspension'),
    ('2027-01-29', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Febrero 2027
    ('2027-02-01', None, 'Aniversario de la Constitución',              'suspension'),
    ('2027-02-05', None, 'Reflexión — Constitución Mexicana',           'conmemora'),
    ('2027-02-08', '2027-02-12', 'Preinscripciones ciclo 2027-2028',    'escuela'),
    ('2027-02-24', None, 'Día de la Bandera',                           'conmemora'),
    ('2027-02-26', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Marzo 2027
    ('2027-03-05', None, 'Registro de calificaciones',                  'evaluacion'),
    ('2027-03-15', None, 'Natalicio de Benito Juárez',                  'suspension'),
    ('2027-03-16', '2027-03-19', 'Resultados de la evaluación',         'evaluacion'),
    ('2027-03-22', '2027-04-02', 'Vacaciones de primavera',             'vacaciones'),

    # Mayo 2027
    ('2027-05-01', None, 'Día del Trabajo',                             'conmemora'),
    ('2027-05-04', None, 'Reflexión — Batalla de Puebla',               'conmemora'),
    ('2027-05-05', None, 'Día de la Batalla de Puebla',                 'suspension'),
    ('2027-05-15', None, 'Día del Maestro',                             'conmemora'),
    ('2027-05-28', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Junio 2027
    ('2027-06-25', None, 'Consejo Técnico Escolar',                     'consejo'),

    # Julio 2027
    ('2027-07-02', None, 'Registro de calificaciones',                  'evaluacion'),
    ('2027-07-08', None, 'Fin de clases del ciclo 2026-2027',           'fin'),
    ('2027-07-09', '2027-07-31', 'Receso de clases',                    'receso'),
]


def cargar_calendario_oficial():
    """
    Precarga las fechas de la SEC. Se puede correr varias veces:
    borra las oficiales anteriores y las vuelve a insertar, así que
    si se corrige una fecha aquí, basta con volver a ejecutarla.

    Los eventos que agregó la docente no se tocan.
    """
    with conexion() as conn:
        conn.execute('DELETE FROM eventos WHERE oficial = 1')

        for fecha, fin, titulo, tipo in CALENDARIO_OFICIAL:
            conn.execute('''
                INSERT INTO eventos (fecha, fecha_fin, titulo, tipo, oficial, hay_clases)
                VALUES (?, ?, ?, ?, 1, ?)
            ''', (fecha, fin, titulo, tipo,
                  TIPOS_MAP.get(tipo, {}).get('hay_clases', 1)))

    return len(CALENDARIO_OFICIAL)


# ── Consultas ────────────────────────────────────────────────

def del_mes(anio, mes):
    """
    Eventos que caen en un mes, incluidos los periodos que lo cruzan.

    Un periodo como las vacaciones de invierno arranca en diciembre y
    termina en enero, así que aparece en los dos meses.
    """
    primero = f'{anio}-{mes:02d}-01'
    ultimo  = f'{anio}-{mes:02d}-31'

    with conexion() as conn:
        filas = conn.execute('''
            SELECT * FROM eventos
            WHERE (fecha BETWEEN ? AND ?)
               OR (fecha_fin IS NOT NULL AND fecha <= ? AND fecha_fin >= ?)
            ORDER BY fecha ASC
        ''', (primero, ultimo, ultimo, primero)).fetchall()
    return a_lista(filas)


def proximos(limite=6):
    """Lo que viene de hoy en adelante."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT * FROM eventos
            WHERE fecha >= date('now', 'localtime')
               OR (fecha_fin IS NOT NULL AND fecha_fin >= date('now', 'localtime'))
            ORDER BY fecha ASC
            LIMIT ?
        ''', (limite,)).fetchall()
    return a_lista(filas)


def obtener(id_evento):
    with conexion() as conn:
        fila = conn.execute('SELECT * FROM eventos WHERE id = ?',
                            (id_evento,)).fetchone()
    return a_dict(fila)


def todos():
    with conexion() as conn:
        filas = conn.execute(
            'SELECT * FROM eventos ORDER BY fecha ASC'
        ).fetchall()
    return a_lista(filas)


# ── Eventos de la escuela ────────────────────────────────────

def crear(fecha, titulo, detalle='', tipo='escuela', fecha_fin=None):
    """Agrega un evento interno. Nunca marca oficial."""
    with conexion() as conn:
        cur = conn.execute('''
            INSERT INTO eventos (fecha, fecha_fin, titulo, detalle, tipo,
                                 oficial, hay_clases, creado)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        ''', (fecha, fecha_fin or None, titulo, detalle, tipo,
              TIPOS_MAP.get(tipo, {}).get('hay_clases', 1), ahora()))
        return cur.lastrowid


def editar(id_evento, fecha, titulo, detalle='', tipo='escuela', fecha_fin=None):
    """Solo se editan los eventos de la escuela, no los oficiales."""
    with conexion() as conn:
        conn.execute('''
            UPDATE eventos
            SET fecha = ?, fecha_fin = ?, titulo = ?, detalle = ?,
                tipo = ?, hay_clases = ?
            WHERE id = ? AND oficial = 0
        ''', (fecha, fecha_fin or None, titulo, detalle, tipo,
              TIPOS_MAP.get(tipo, {}).get('hay_clases', 1), id_evento))


def eliminar(id_evento):
    """Solo se eliminan los eventos de la escuela."""
    with conexion() as conn:
        conn.execute('DELETE FROM eventos WHERE id = ? AND oficial = 0',
                     (id_evento,))
