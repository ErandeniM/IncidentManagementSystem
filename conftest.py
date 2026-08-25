"""
Configuración de pruebas para Mi Salón.

Notas sobre esta estructura en particular:

  · La app es global (`app = Flask(__name__)`), no hay factory. Se importa
    una sola vez, después de apuntar MI_SALON_DB a un archivo temporal.

  · Cada repositorio abre y cierra su propia conexión, así que no se puede
    aislar con transacciones. En su lugar, cada prueba arranca con las
    tablas vacías.

  · `seguridad.py` guarda el contador de intentos en un diccionario de
    módulo. Sin limpiarlo entre pruebas, una que agote los intentos deja
    bloqueada a la siguiente.

  · `notificaciones.py` lanza hilos que hablan con SMTP. Se neutraliza.
"""

import os
import sys
import sqlite3
import tempfile

import pytest


# ─────────────────────────────────────────────────────────────
# El proyecto debe estar en el path antes de importar nada suyo
# ─────────────────────────────────────────────────────────────

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# ─────────────────────────────────────────────────────────────
# Base temporal — se define ANTES de importar la aplicación
# ─────────────────────────────────────────────────────────────

_descriptor, RUTA_PRUEBAS = tempfile.mkstemp(suffix='.db', prefix='misalon_test_')
os.close(_descriptor)
os.remove(RUTA_PRUEBAS)          # init_db() la crea desde schema.sql
os.environ['MI_SALON_DB'] = RUTA_PRUEBAS

# A partir de aquí ya es seguro importar: get_db() leerá la ruta temporal
import app as modulo_app                                    # noqa: E402
import seguridad                                            # noqa: E402
import notificaciones                                       # noqa: E402
from database import init_db, hash_password, ruta_db        # noqa: E402
from repositorios import alumnos as repo_alumnos            # noqa: E402


TABLAS = [
    'alumnos', 'incidencias', 'incidencia_seguimiento', 'calificaciones',
    'perfil_alumno', 'actividades_recomendadas', 'tareas_entrega', 'entregas',
    'avisos', 'avisos_confirmaciones', 'avisos_padre', 'mensajes',
    'registro_accesos', 'sqlite_sequence',
]

CLAVE_ADMIN_PRUEBAS = 'clave-de-pruebas-2026'


def _vaciar_tablas():
    """
    Deja todas las tablas sin filas.

    init_db() crea un alumno de ejemplo; si no se borra, cada prueba
    arrancaría con datos que no pidió.
    """
    conn = sqlite3.connect(ruta_db())
    for tabla in TABLAS:
        try:
            conn.execute(f'DELETE FROM {tabla}')
        except sqlite3.OperationalError:
            pass          # la tabla no existe en esta versión del esquema
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# Fixtures de sesión
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def aplicacion():
    """La app de Flask configurada para pruebas."""
    modulo_app.app.config.update(
        TESTING    = True,
        SECRET_KEY = 'llave-de-pruebas',
    )
    yield modulo_app.app

    if os.path.exists(RUTA_PRUEBAS):
        os.remove(RUTA_PRUEBAS)


# ─────────────────────────────────────────────────────────────
# Fixtures por prueba
# ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def base_limpia(aplicacion):
    """Cada prueba arranca con el esquema creado y sin datos."""
    if not os.path.exists(ruta_db()):
        init_db()
    _vaciar_tablas()
    yield


@pytest.fixture(autouse=True)
def sin_bloqueos():
    """
    Limpia el contador de intentos fallidos.

    Vive en un diccionario de módulo, así que sin esto una prueba que
    agota los intentos bloquearía a las siguientes.
    """
    seguridad._registro.clear()
    yield
    seguridad._registro.clear()


@pytest.fixture(autouse=True)
def sin_correos(monkeypatch):
    """
    Anula el envío de correo.

    notificaciones.py lanza un hilo que se conecta a Gmail; en pruebas
    eso sería lento y fallaría sin red.
    """
    enviados = []

    def registrar(*args, **kwargs):
        enviados.append({'args': args, 'kwargs': kwargs})

    monkeypatch.setattr(notificaciones, 'avisar_a_padre',   registrar)
    monkeypatch.setattr(notificaciones, 'avisar_a_todos',   registrar)
    monkeypatch.setattr(notificaciones, 'avisar_a_docente', registrar)
    return enviados


@pytest.fixture(autouse=True)
def clave_admin_conocida(monkeypatch):
    """
    Sustituye la contraseña de la docente por una conocida.

    Así las pruebas no dependen de la contraseña real de config.py, que
    ni siquiera está en el repositorio.
    """
    import routes.admin as rutas_admin
    monkeypatch.setattr(
        rutas_admin, 'ADMIN_PASSWORD_HASH', hash_password(CLAVE_ADMIN_PRUEBAS)
    )


# ─────────────────────────────────────────────────────────────
# Clientes
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def cliente(aplicacion):
    """Navegador sin sesión iniciada."""
    return aplicacion.test_client()


@pytest.fixture
def nuevo_alumno():
    """
    Fábrica de alumnos.

        alumno = nuevo_alumno('MABC010101', 'María G.')
    """
    def crear(curp='MABC010101', nombre='María G.',
              password='clave-de-prueba', correo='mama@ejemplo.com'):
        id_alumno = repo_alumnos.crear(
            curp          = curp,
            nombre        = nombre,
            password_hash = hash_password(password),
            correo_padre  = correo,
        )
        return {'id': id_alumno, 'curp': curp, 'nombre': nombre,
                'password': password}
    return crear


@pytest.fixture
def familia(cliente, nuevo_alumno):
    """Cliente con sesión de tutor ya iniciada."""
    alumno = nuevo_alumno()
    cliente.post('/', data={'curp':     alumno['curp'],
                            'password': alumno['password']})
    return {'cliente': cliente, 'alumno': alumno}


@pytest.fixture
def docente(cliente):
    """Cliente con sesión de docente ya iniciada."""
    cliente.post('/admin', data={'password': CLAVE_ADMIN_PRUEBAS})
    return cliente
