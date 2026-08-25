"""
Pruebas de autenticación y permisos.

Cubren tres cosas distintas:

  · Que el login funcione y deje rastro (registro de accesos).
  · Que las defensas funcionen: límite de intentos, mensaje uniforme
    para no revelar qué CURP existe, migración de contraseñas viejas.
  · Que nadie vea lo que no le toca: un tutor no puede leer la
    incidencia de otro alumno ni entrar al panel docente.
"""

import hashlib
import sqlite3

from database import ruta_db, hash_password
from repositorios import alumnos as repo_alumnos
from repositorios import accesos as repo_accesos
from repositorios import incidencias as repo_incidencias

from conftest import CLAVE_ADMIN_PRUEBAS


MENSAJE_CREDENCIALES = 'CURP o contraseña incorrectos'


def texto(respuesta):
    return respuesta.data.decode('utf-8')


# ═══════════════════════════════════════════════════════════
# Login del tutor
# ═══════════════════════════════════════════════════════════

def test_login_correcto_lleva_al_panel(cliente, nuevo_alumno):
    alumno = nuevo_alumno()

    respuesta = cliente.post('/', data={
        'curp':     alumno['curp'],
        'password': alumno['password'],
    })

    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/panel')

    with cliente.session_transaction() as sesion:
        assert sesion['alumno_id'] == alumno['id']
        assert sesion['nombre'] == alumno['nombre']


def test_login_con_password_incorrecta_no_crea_sesion(cliente, nuevo_alumno):
    alumno = nuevo_alumno()

    respuesta = cliente.post('/', data={
        'curp':     alumno['curp'],
        'password': 'no-es-la-buena',
    })

    assert respuesta.status_code == 200
    assert MENSAJE_CREDENCIALES in texto(respuesta)

    with cliente.session_transaction() as sesion:
        assert 'alumno_id' not in sesion


def test_la_curp_se_normaliza_a_mayusculas(cliente, nuevo_alumno):
    """El tutor puede escribirla en minúsculas y debe entrar igual."""
    alumno = nuevo_alumno(curp='MABC010101')

    respuesta = cliente.post('/', data={
        'curp':     'mabc010101',
        'password': alumno['password'],
    })

    assert respuesta.status_code == 302


def test_login_exitoso_deja_rastro_en_la_bitacora(cliente, nuevo_alumno):
    alumno = nuevo_alumno()

    cliente.post('/', data={'curp':     alumno['curp'],
                            'password': alumno['password']})

    accesos = repo_accesos.ultimos_de_alumno(alumno['id'])
    assert len(accesos) == 1
    assert accesos[0]['ip']    is not None
    assert accesos[0]['fecha'] is not None


def test_login_fallido_no_deja_rastro(cliente, nuevo_alumno):
    alumno = nuevo_alumno()

    cliente.post('/', data={'curp': alumno['curp'], 'password': 'mala'})

    assert repo_accesos.ultimos_de_alumno(alumno['id']) == []


def test_logout_limpia_la_sesion(familia):
    cliente = familia['cliente']

    cliente.get('/logout')

    with cliente.session_transaction() as sesion:
        assert 'alumno_id' not in sesion


# ═══════════════════════════════════════════════════════════
# No revelar qué CURP existe
# ═══════════════════════════════════════════════════════════

def test_el_mensaje_es_identico_exista_o_no_la_curp(cliente, nuevo_alumno):
    """
    Si el sistema respondiera distinto, alguien podría probar CURPs para
    averiguar cuáles están dados de alta. Con CURPs, que siguen un patrón
    adivinable, eso sería una fuga real.
    """
    alumno = nuevo_alumno(curp='MABC010101')

    existente = cliente.post('/', data={'curp': 'MABC010101',
                                        'password': 'incorrecta'})
    inexistente = cliente.post('/', data={'curp': 'ZZZZ999999',
                                          'password': 'incorrecta'})

    assert MENSAJE_CREDENCIALES in texto(existente)
    assert MENSAJE_CREDENCIALES in texto(inexistente)
    assert existente.status_code == inexistente.status_code


# ═══════════════════════════════════════════════════════════
# Migración perezosa de contraseñas
# ═══════════════════════════════════════════════════════════

def _hash_viejo(password):
    """El formato SHA-256 que usaba el sistema antes."""
    return hashlib.sha256(password.encode()).hexdigest()


def _hash_guardado(id_alumno):
    conn = sqlite3.connect(ruta_db())
    fila = conn.execute(
        'SELECT password_hash FROM alumnos WHERE id = ?', (id_alumno,)
    ).fetchone()
    conn.close()
    return fila[0]


def test_una_password_vieja_sigue_funcionando(cliente, nuevo_alumno):
    alumno = nuevo_alumno(password='da-igual')
    repo_alumnos.actualizar_password(alumno['id'], _hash_viejo('clave-antigua'))

    respuesta = cliente.post('/', data={'curp':     alumno['curp'],
                                        'password': 'clave-antigua'})

    assert respuesta.status_code == 302


def test_al_entrar_el_hash_viejo_se_actualiza_solo(cliente, nuevo_alumno):
    """
    El hash es irreversible, así que no se pueden convertir en bloque.
    Se actualizan uno por uno, en el momento en que cada tutor entra.
    """
    alumno = nuevo_alumno(password='da-igual')
    repo_alumnos.actualizar_password(alumno['id'], _hash_viejo('clave-antigua'))
    assert len(_hash_guardado(alumno['id'])) == 64          # formato viejo

    cliente.post('/', data={'curp':     alumno['curp'],
                            'password': 'clave-antigua'})

    nuevo = _hash_guardado(alumno['id'])
    assert nuevo.startswith(('scrypt:', 'pbkdf2:'))
    assert nuevo != _hash_viejo('clave-antigua')


def test_el_hash_viejo_no_acepta_password_equivocada(cliente, nuevo_alumno):
    alumno = nuevo_alumno(password='da-igual')
    repo_alumnos.actualizar_password(alumno['id'], _hash_viejo('clave-antigua'))

    respuesta = cliente.post('/', data={'curp':     alumno['curp'],
                                        'password': 'otra-cosa'})

    assert respuesta.status_code == 200
    assert len(_hash_guardado(alumno['id'])) == 64          # no se tocó


# ═══════════════════════════════════════════════════════════
# Límite de intentos
# ═══════════════════════════════════════════════════════════

def test_bloquea_tras_cinco_intentos_con_curp_existente(cliente, nuevo_alumno):
    alumno = nuevo_alumno()

    for _ in range(5):
        cliente.post('/', data={'curp': alumno['curp'], 'password': 'mala'})

    respuesta = cliente.post('/', data={'curp':     alumno['curp'],
                                        'password': alumno['password']})

    assert 'Demasiados intentos' in texto(respuesta)
    with cliente.session_transaction() as sesion:
        assert 'alumno_id' not in sesion, 'el bloqueo debe ganarle a la password correcta'


def test_una_curp_inexistente_tolera_mas_intentos(cliente):
    """
    Teclear mal la CURP es un error común del tutor, no un ataque.
    Por eso ahí se permiten diez intentos y no cinco.
    """
    for _ in range(5):
        cliente.post('/', data={'curp': 'ZZZZ999999', 'password': 'x'})

    respuesta = cliente.post('/', data={'curp': 'ZZZZ999999', 'password': 'x'})

    assert 'Demasiados intentos' not in texto(respuesta)


def test_un_login_exitoso_borra_el_contador(cliente, nuevo_alumno):
    alumno = nuevo_alumno()

    for _ in range(4):
        cliente.post('/', data={'curp': alumno['curp'], 'password': 'mala'})

    cliente.post('/', data={'curp':     alumno['curp'],
                            'password': alumno['password']})
    cliente.get('/logout')

    for _ in range(4):
        cliente.post('/', data={'curp': alumno['curp'], 'password': 'mala'})

    respuesta = cliente.post('/', data={'curp':     alumno['curp'],
                                        'password': alumno['password']})
    assert respuesta.status_code == 302


# ═══════════════════════════════════════════════════════════
# Rutas protegidas
# ═══════════════════════════════════════════════════════════

def test_el_panel_exige_sesion(cliente):
    respuesta = cliente.get('/panel')
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/')


def test_las_rutas_del_tutor_exigen_sesion(cliente):
    for ruta in ['/panel', '/chat', '/avisar', '/perfil',
                 '/configuracion', '/buscar', '/incidencia/1']:
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 302, f'{ruta} quedó sin proteger'


def test_las_rutas_de_la_docente_exigen_sesion(cliente):
    for ruta in ['/admin/dashboard', '/admin/alumnos', '/admin/calificaciones',
                 '/admin/incidencias', '/admin/avisos', '/admin/mensajes',
                 '/admin/tareas', '/admin/accesos', '/admin/alumno/1']:
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 302, f'{ruta} quedó sin proteger'
        assert respuesta.headers['Location'].endswith('/admin')


def test_un_tutor_no_entra_al_panel_docente(familia):
    """Tener sesión de tutor no da acceso al panel de la maestra."""
    respuesta = familia['cliente'].get('/admin/dashboard')

    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/admin')


# ═══════════════════════════════════════════════════════════
# Aislamiento entre familias
# ═══════════════════════════════════════════════════════════

def test_un_tutor_no_puede_ver_la_incidencia_de_otro_alumno(cliente, nuevo_alumno):
    """
    La prueba más importante del archivo.

    El filtro por alumno está en el SQL, no en la plantilla: aunque el
    tutor cambie el número en la dirección, la consulta no devuelve nada.
    """
    mia   = nuevo_alumno(curp='MABC010101', nombre='María G.')
    ajena = nuevo_alumno(curp='LOPZ020202', nombre='Juan P.')

    id_incidencia = repo_incidencias.crear(
        id_alumno   = ajena['id'],
        tipo        = 'accidente',
        descripcion = 'Dato reservado de otra familia',
    )

    cliente.post('/', data={'curp': mia['curp'], 'password': mia['password']})
    respuesta = cliente.get(f'/incidencia/{id_incidencia}')

    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/panel')


def test_un_tutor_no_puede_firmar_la_incidencia_de_otro(cliente, nuevo_alumno):
    mia   = nuevo_alumno(curp='MABC010101')
    ajena = nuevo_alumno(curp='LOPZ020202')

    id_incidencia = repo_incidencias.crear(
        id_alumno   = ajena['id'],
        tipo        = 'accidente',
        descripcion = 'Dato reservado de otra familia',
    )

    cliente.post('/', data={'curp': mia['curp'], 'password': mia['password']})
    cliente.post(f'/comentar/{id_incidencia}', data={
        'acepto_declaracion': 'on',
        'comentario':         'Intento de firma indebida',
    })

    inc = repo_incidencias.obtener(id_incidencia)
    assert not inc['enterado'], 'se firmó una incidencia ajena'


def test_el_feed_solo_trae_publicaciones_del_propio_hijo(cliente, nuevo_alumno):
    mia   = nuevo_alumno(curp='MABC010101', nombre='María G.')
    ajena = nuevo_alumno(curp='LOPZ020202', nombre='Juan P.')

    repo_incidencias.crear(mia['id'],   'logro',     'Terminó primera el ejercicio')
    repo_incidencias.crear(ajena['id'], 'accidente', 'Dato reservado de otra familia')

    cliente.post('/', data={'curp': mia['curp'], 'password': mia['password']})
    respuesta = cliente.get('/panel')

    contenido = texto(respuesta)
    assert 'Dato reservado de otra familia' not in contenido


# ═══════════════════════════════════════════════════════════
# Acceso de la docente
# ═══════════════════════════════════════════════════════════

def test_la_docente_entra_con_la_clave_correcta(cliente):
    respuesta = cliente.post('/admin', data={'password': CLAVE_ADMIN_PRUEBAS})

    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/admin/dashboard')

    with cliente.session_transaction() as sesion:
        assert sesion['admin'] is True


def test_la_clave_incorrecta_no_abre_el_panel(cliente):
    respuesta = cliente.post('/admin', data={'password': 'no-es-la-buena'})

    assert respuesta.status_code == 200
    assert 'Contraseña incorrecta' in texto(respuesta)

    with cliente.session_transaction() as sesion:
        assert 'admin' not in sesion


def test_el_panel_docente_tambien_limita_intentos(cliente):
    for _ in range(5):
        cliente.post('/admin', data={'password': 'mala'})

    respuesta = cliente.post('/admin', data={'password': CLAVE_ADMIN_PRUEBAS})

    assert 'Demasiados intentos' in texto(respuesta)
    with cliente.session_transaction() as sesion:
        assert 'admin' not in sesion


def test_el_logout_docente_cierra_la_sesion(docente):
    docente.get('/admin/logout')

    with docente.session_transaction() as sesion:
        assert 'admin' not in sesion


def test_los_contadores_de_tutor_y_docente_son_independientes(cliente, nuevo_alumno):
    """
    Que un tutor agote sus intentos no debe dejar fuera a la maestra
    desde el mismo equipo.
    """
    alumno = nuevo_alumno()
    for _ in range(5):
        cliente.post('/', data={'curp': alumno['curp'], 'password': 'mala'})

    respuesta = cliente.post('/admin', data={'password': CLAVE_ADMIN_PRUEBAS})
    assert respuesta.status_code == 302
