"""
Repositorio académico.

Reúne las tres tablas del seguimiento pedagógico:
  · calificaciones            → notas por trimestre
  · perfil_alumno             → nivel por área de habilidad
  · actividades_recomendadas  → sugerencias para trabajar en casa
"""

from repositorios.base import conexion, a_dict, a_lista, ahora


# ═══════════ CATÁLOGOS ═══════════

MATERIAS = [
    ('lenguajes',   'Lenguajes'),
    ('ciencias',    'Saberes y Pensamiento Científico'),
    ('etica',       'Ética, Naturaleza y Sociedades'),
    ('comunitario', 'De lo Humano y lo Comunitario'),
]

AREAS = [
    ('logico',    'Lógico-matemático'),
    ('fisico',    'Físico-deportivo'),
    ('artistico', 'Artístico'),
    ('social',    'Social'),
    ('lenguaje',  'Lenguaje'),
]

CATEGORIAS_ACTIVIDAD = ['Cognitiva', 'Física', 'Artística', 'Social', 'Lenguaje', 'General']


def _promedio(valores):
    """Promedio de los valores que no son None. Devuelve None si no hay ninguno."""
    llenos = [v for v in valores if v is not None]
    return round(sum(llenos) / len(llenos), 1) if llenos else None


# ═══════════ CALIFICACIONES ═══════════

def calificaciones_de(id_alumno):
    """Calificaciones de un alumno, ordenadas por trimestre."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT * FROM calificaciones
            WHERE id_alumno = ?
            ORDER BY trimestre
        ''', (id_alumno,)).fetchall()
    return a_lista(filas)


def promedio_general(id_alumno):
    """Promedio de todas las materias de todos los trimestres."""
    todas = []
    for cal in calificaciones_de(id_alumno):
        todas += [cal[campo] for campo, _ in MATERIAS]
    return _promedio(todas)


def tabla_trimestre(trimestre):
    """
    Todos los alumnos con sus calificaciones de un trimestre.
    Cada fila trae además `completo` y `promedio` ya calculados.
    """
    with conexion() as conn:
        filas = conn.execute('''
            SELECT a.id, a.nombre, a.curp,
                   c.lenguajes, c.ciencias, c.etica, c.comunitario,
                   c.inasistencias, c.observaciones, c.fecha_actualizacion
            FROM alumnos a
            LEFT JOIN calificaciones c
                ON c.id_alumno = a.id AND c.trimestre = ?
            ORDER BY a.nombre
        ''', (trimestre,)).fetchall()

    alumnos = []
    for fila in a_lista(filas):
        notas = [fila[campo] for campo, _ in MATERIAS]
        fila['completo'] = all(n is not None for n in notas)
        fila['promedio'] = _promedio(notas)
        alumnos.append(fila)
    return alumnos


def resumen_trimestre(alumnos):
    """
    A partir de la tabla de un trimestre, calcula el avance de captura,
    el promedio por materia y el promedio del grupo.
    """
    total     = len(alumnos)
    completos = sum(1 for a in alumnos if a['completo'])

    por_materia = {}
    todas = []
    for campo, _ in MATERIAS:
        valores = [a[campo] for a in alumnos if a[campo] is not None]
        por_materia[campo] = _promedio(valores)
        todas += valores

    return {
        'total':        total,
        'completos':    completos,
        'avance':       round(completos * 100 / total) if total else 0,
        'por_materia':  por_materia,
        'promedio':     _promedio(todas),
    }


def guardar_calificaciones(id_alumno, trimestre, notas,
                           inasistencias=0, observaciones=''):
    """
    Guarda o actualiza la fila de un alumno en un trimestre.
    `notas` es un diccionario con las claves de MATERIAS.
    """
    with conexion() as conn:
        conn.execute('''
            INSERT INTO calificaciones
                (id_alumno, trimestre, lenguajes, ciencias, etica, comunitario,
                 inasistencias, observaciones, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_alumno, trimestre) DO UPDATE SET
                lenguajes           = excluded.lenguajes,
                ciencias            = excluded.ciencias,
                etica               = excluded.etica,
                comunitario         = excluded.comunitario,
                inasistencias       = excluded.inasistencias,
                observaciones       = excluded.observaciones,
                fecha_actualizacion = excluded.fecha_actualizacion
        ''', (
            id_alumno, trimestre,
            notas.get('lenguajes'), notas.get('ciencias'),
            notas.get('etica'), notas.get('comunitario'),
            inasistencias, observaciones, ahora()
        ))


# ═══════════ PERFIL DE HABILIDADES ═══════════

def perfil_de(id_alumno):
    """Perfil de habilidades, o None si la maestra no lo ha registrado."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT * FROM perfil_alumno WHERE id_alumno = ?', (id_alumno,)
        ).fetchone()
    return a_dict(fila)


def guardar_perfil(id_alumno, valores, nota=''):
    """
    Guarda el perfil. `valores` es un diccionario con las claves de AREAS,
    cada una de 0 a 100.
    """
    with conexion() as conn:
        conn.execute('''
            INSERT INTO perfil_alumno
                (id_alumno, logico, fisico, artistico, social, lenguaje,
                 nota, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_alumno) DO UPDATE SET
                logico      = excluded.logico,
                fisico      = excluded.fisico,
                artistico   = excluded.artistico,
                social      = excluded.social,
                lenguaje    = excluded.lenguaje,
                nota        = excluded.nota,
                actualizado = excluded.actualizado
        ''', (
            id_alumno,
            int(valores.get('logico', 0)),
            int(valores.get('fisico', 0)),
            int(valores.get('artistico', 0)),
            int(valores.get('social', 0)),
            int(valores.get('lenguaje', 0)),
            nota, ahora()
        ))


# ═══════════ ACTIVIDADES ═══════════

def actividades_de(id_alumno, pendientes_primero=False):
    """Actividades sugeridas para un alumno."""
    orden = 'completada ASC, fecha DESC' if pendientes_primero else 'fecha DESC'
    with conexion() as conn:
        filas = conn.execute(f'''
            SELECT * FROM actividades_recomendadas
            WHERE id_alumno = ?
            ORDER BY {orden}
        ''', (id_alumno,)).fetchall()
    return a_lista(filas)


def crear_actividad(id_alumno, actividad, categoria='General'):
    """Agrega una actividad para un alumno."""
    with conexion() as conn:
        cur = conn.execute('''
            INSERT INTO actividades_recomendadas
                (id_alumno, actividad, categoria, fecha)
            VALUES (?, ?, ?, ?)
        ''', (id_alumno, actividad, categoria, ahora()))
        return cur.lastrowid


def crear_actividad_para_todos(actividad, categoria='General'):
    """
    Agrega la misma actividad a todo el grupo.
    Devuelve cuántos alumnos la recibieron.
    """
    momento = ahora()
    with conexion() as conn:
        ids = [f['id'] for f in conn.execute('SELECT id FROM alumnos').fetchall()]
        conn.executemany('''
            INSERT INTO actividades_recomendadas
                (id_alumno, actividad, categoria, fecha)
            VALUES (?, ?, ?, ?)
        ''', [(i, actividad, categoria, momento) for i in ids])
    return len(ids)


def eliminar_actividad(id_actividad):
    """Borra una actividad."""
    with conexion() as conn:
        conn.execute(
            'DELETE FROM actividades_recomendadas WHERE id = ?', (id_actividad,)
        )
