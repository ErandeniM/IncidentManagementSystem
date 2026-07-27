"""
Respaldo de la base de datos de Mi Salón.

Uso:
    python backup.py            → crea un respaldo nuevo
    python backup.py --listar   → muestra los respaldos existentes

Los respaldos se guardan en la carpeta 'respaldos/' con fecha y hora.
Se conservan los 30 más recientes; los más viejos se borran solos.
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATABASE      = os.path.join(BASE_DIR, 'incidencias.db')
CARPETA       = os.path.join(BASE_DIR, 'respaldos')
MAX_RESPALDOS = 30


def crear_respaldo():
    if not os.path.exists(DATABASE):
        print('ERROR: no se encontró incidencias.db')
        return False

    os.makedirs(CARPETA, exist_ok=True)

    sello   = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    destino = os.path.join(CARPETA, f'incidencias_{sello}.db')

    # Copia segura con la API de SQLite (funciona aunque Flask esté corriendo)
    origen_con  = sqlite3.connect(DATABASE)
    destino_con = sqlite3.connect(destino)
    with destino_con:
        origen_con.backup(destino_con)
    destino_con.close()
    origen_con.close()

    tam = os.path.getsize(destino) / 1024
    print(f'Respaldo creado: respaldos/incidencias_{sello}.db  ({tam:.0f} KB)')

    rotar()
    return True


def rotar():
    """Conserva solo los MAX_RESPALDOS más recientes."""
    archivos = sorted(
        f for f in os.listdir(CARPETA)
        if f.startswith('incidencias_') and f.endswith('.db')
    )
    sobran = len(archivos) - MAX_RESPALDOS
    for viejo in archivos[:max(0, sobran)]:
        os.remove(os.path.join(CARPETA, viejo))
        print(f'Respaldo antiguo eliminado: {viejo}')


def listar():
    if not os.path.exists(CARPETA):
        print('Todavía no hay respaldos.')
        return

    archivos = sorted(
        f for f in os.listdir(CARPETA)
        if f.startswith('incidencias_') and f.endswith('.db')
    )
    if not archivos:
        print('Todavía no hay respaldos.')
        return

    print(f'{len(archivos)} respaldo(s):\n')
    for f in archivos:
        ruta = os.path.join(CARPETA, f)
        tam  = os.path.getsize(ruta) / 1024
        print(f'  {f}   {tam:.0f} KB')


if __name__ == '__main__':
    if '--listar' in sys.argv:
        listar()
    else:
        crear_respaldo()
