"""
Migración: prepara la base para múltiples docentes y grupos.

Agrega las columnas solo si no existen, así que se puede correr varias veces
sin causar problemas. No borra ni modifica datos existentes.

Uso:
    python migrar.py
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'incidencias.db')

# (tabla, columna, definición)
COLUMNAS = [
    ('alumnos',                  'id_grupo',   'INTEGER DEFAULT 1'),
    ('incidencias',              'id_docente', 'INTEGER DEFAULT 1'),
    ('avisos',                   'id_docente', 'INTEGER DEFAULT 1'),
    ('mensajes',                 'id_docente', 'INTEGER DEFAULT 1'),
    ('calificaciones',           'id_docente', 'INTEGER DEFAULT 1'),
    ('actividades_recomendadas', 'id_docente', 'INTEGER DEFAULT 1'),
]


def columnas_de(conn, tabla):
    return [r[1] for r in conn.execute(f'PRAGMA table_info({tabla})')]


def tabla_existe(conn, tabla):
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
    ).fetchone()
    return r is not None


def migrar():
    if not os.path.exists(DATABASE):
        print('ERROR: no se encontró incidencias.db')
        return

    conn = sqlite3.connect(DATABASE)
    agregadas = 0

    for tabla, columna, definicion in COLUMNAS:
        if not tabla_existe(conn, tabla):
            print(f'  omitida  {tabla}.{columna}  (la tabla no existe)')
            continue

        if columna in columnas_de(conn, tabla):
            print(f'  ya está  {tabla}.{columna}')
            continue

        conn.execute(f'ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}')
        print(f'  AGREGADA {tabla}.{columna}')
        agregadas += 1

    conn.commit()
    conn.close()

    print()
    if agregadas:
        print(f'Listo: {agregadas} columna(s) agregada(s).')
    else:
        print('La base ya estaba al día. No hubo cambios.')


if __name__ == '__main__':
    print('Migrando base de datos...\n')
    migrar()
