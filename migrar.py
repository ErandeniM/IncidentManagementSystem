"""
Migración de la base de datos.

Agrega tablas y columnas solo si no existen, así que se puede correr
varias veces sin causar problemas. No borra ni modifica datos.

Uso:
    python migrar.py
"""

import sqlite3

from database import ruta_db


# ── Tablas que se crean completas si faltan ──────────────────

TABLAS_NUEVAS = {
    'eventos': '''
        CREATE TABLE eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            fecha_fin DATE,
            titulo TEXT NOT NULL,
            detalle TEXT,
            tipo TEXT DEFAULT 'escuela',
            oficial INTEGER DEFAULT 0,
            hay_clases INTEGER DEFAULT 1,
            creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            id_docente INTEGER DEFAULT 1
        )
    ''',
}


# ── Columnas que se agregan a tablas existentes ──────────────
#    (tabla, columna, definición)

COLUMNAS = [
    ('alumnos',                  'id_grupo',           'INTEGER DEFAULT 1'),
    ('alumnos',                  'acepto_aviso',       'INTEGER DEFAULT 0'),
    ('alumnos',                  'fecha_acepto_aviso', 'TIMESTAMP'),
    ('alumnos',                  'acepto_aviso_por',   'TEXT'),

    ('incidencias',              'id_docente',         'INTEGER DEFAULT 1'),
    ('incidencias',              'accion_docente',     'TEXT'),
    ('incidencias',              'nivel',              "TEXT DEFAULT 'informativo'"),

    ('incidencia_seguimiento',   'acepto_declaracion', 'INTEGER DEFAULT 0'),
    ('incidencia_seguimiento',   'texto_declaracion',  'TEXT'),

    ('avisos',                   'id_docente',         'INTEGER DEFAULT 1'),
    ('avisos',                   'eliminado',          'INTEGER DEFAULT 0'),
    ('avisos',                   'fecha_eliminado',    'TIMESTAMP'),

    ('avisos_padre',             'acusado_por',        'TEXT'),

    ('mensajes',                 'id_docente',         'INTEGER DEFAULT 1'),
    ('mensajes',                 'ref_tipo',           'TEXT'),
    ('mensajes',                 'ref_id',             'INTEGER'),
    ('mensajes',                 'ref_titulo',         'TEXT'),

    ('calificaciones',           'id_docente',         'INTEGER DEFAULT 1'),
    ('actividades_recomendadas', 'id_docente',         'INTEGER DEFAULT 1'),
]


# ── Índices que conviene tener ───────────────────────────────

INDICES = [
    ('idx_incidencias_alumno',    'incidencias(id_alumno)'),
    ('idx_incidencias_fecha',     'incidencias(fecha)'),
    ('idx_calificaciones_alumno', 'calificaciones(id_alumno)'),
    ('idx_actividades_alumno',    'actividades_recomendadas(id_alumno)'),
    ('idx_entregas_tarea',        'entregas(id_tarea)'),
    ('idx_entregas_alumno',       'entregas(id_alumno)'),
    ('idx_confirmaciones_aviso',  'avisos_confirmaciones(id_aviso)'),
    ('idx_confirmaciones_alumno', 'avisos_confirmaciones(id_alumno)'),
    ('idx_avisos_padre_alumno',   'avisos_padre(id_alumno)'),
    ('idx_mensajes_alumno',       'mensajes(id_alumno, fecha)'),
    ('idx_accesos_alumno',        'registro_accesos(id_alumno, fecha)'),
    ('idx_eventos_fecha',         'eventos(fecha)'),
]


def columnas_de(conn, tabla):
    return [r[1] for r in conn.execute(f'PRAGMA table_info({tabla})')]


def tablas_de(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}


def migrar():
    conn = sqlite3.connect(ruta_db())

    tablas   = tablas_de(conn)
    creadas  = 0
    columnas = 0
    indices  = 0

    # ── Tablas nuevas ──
    for tabla, sql in TABLAS_NUEVAS.items():
        if tabla in tablas:
            print(f'  ya está  tabla {tabla}')
        else:
            conn.execute(sql)
            print(f'  CREADA   tabla {tabla}')
            creadas += 1
            tablas.add(tabla)

    # ── Columnas nuevas ──
    for tabla, columna, tipo in COLUMNAS:
        if tabla not in tablas:
            print(f'  falta    la tabla {tabla}, se omite {columna}')
            continue

        if columna in columnas_de(conn, tabla):
            print(f'  ya está  {tabla}.{columna}')
        else:
            conn.execute(f'ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}')
            print(f'  AGREGADA {tabla}.{columna}')
            columnas += 1

    # ── Índices ──
    for nombre, definicion in INDICES:
        try:
            conn.execute(f'CREATE INDEX IF NOT EXISTS {nombre} ON {definicion}')
            indices += 1
        except sqlite3.OperationalError as e:
            print(f'  omitido  índice {nombre}: {e}')

    conn.commit()
    conn.close()

    print()
    if creadas or columnas:
        print(f'Listo: {creadas} tabla(s) y {columnas} columna(s) agregadas.')
    else:
        print('La base ya estaba al día. No hubo cambios.')
    print(f'{indices} índice(s) verificados.')


if __name__ == '__main__':
    print('Migrando base de datos...\n')
    migrar()
