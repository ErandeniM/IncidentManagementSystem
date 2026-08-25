from datetime import datetime, timedelta

from config import SECRET_KEY, DOCENTE_NOMBRE, GRUPO_NOMBRE, ESCUELA_NOMBRE # del archivo config.py se importan las variables SECRET_KEY, DOCENTE_NOMBRE, GRUPO_NOMBRE y ESCUELA_NOMBRE que contienen información de configuración de la aplicación.
from database import init_db # del archivo database.py se importa la función init_db que inicializa la base de datos de la aplicación.
from routes.auth import auth_bp # del archivo routes/auth.py se importa el objeto auth_bp que contiene las rutas relacionadas con la autenticación de usuarios.
from routes.alumno import alumno_bp # del archivo routes/alumno.py se importa el objeto alumno_bp que contiene las rutas relacionadas con los alumnos.
from routes.admin import admin_bp # del archivo routes/admin.py se importa el objeto admin_bp que contiene las rutas relacionadas con la administración de la aplicación.
from flask import Flask, session #  del módulo flask se importa la clase Flask y el objeto session que permite manejar sesiones de usuario.
from repositorios import pendientes as repo_pendientes # del archivo repositorios/pendientes.py se importa el módulo pendientes y se le asigna el alias repo_pendientes, que contiene funciones para manejar los pendientes de los alumnos.

app = Flask(__name__) # Se crea una instancia de la clase Flask, que representa la aplicación web y se le asigna a la variable app.
app.secret_key = SECRET_KEY # Se establece la clave secreta de la aplicación, que se utiliza para firmar las cookies de sesión y proteger contra ataques de falsificación de solicitudes entre sitios (CSRF).

# Cookies de sesión más seguras 
app.config.update( # Se actualiza la configuración de la aplicación con opciones de seguridad para las cookies de sesión.
    SESSION_COOKIE_HTTPONLY = True,   # el JavaScript no puede leer la cookie
    SESSION_COOKIE_SAMESITE = 'Lax',  # evita envíos desde otros sitios
)


# ── Filtros de fecha para los templates ──

@app.template_filter('hora_local') # Se define un filtro de plantilla llamado 'hora_local' que se puede usar en los templates de Jinja2 para mostrar solo la hora de una fecha guardada.
def hora_local(fecha_str): # se define la función hora_local que toma como argumento una cadena de fecha y hora en formato 'YYYY-MM-DD HH:MM:SS' y devuelve solo la hora en formato 'HH:MM'.
    """Muestra solo la hora de una fecha guardada.""" 
    if not fecha_str: # si la cadena de fecha es vacía o None, se devuelve una cadena vacía.
        return ''
    try: # se intenta convertir la cadena de fecha en un objeto datetime usando el formato '%Y-%m-%d %H:%M:%S' y luego se formatea para mostrar solo la hora en formato 'HH:MM'.
        return datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
    except ValueError:
        return fecha_str[11:16] if len(fecha_str) > 11 else ''


@app.template_filter('fecha_local') # Se define un filtro de plantilla llamado 'fecha_local' que se puede usar en los templates de Jinja2 para mostrar solo la fecha de una fecha guardada.
def fecha_local(fecha_str): # se define la función fecha_local que toma como argumento una cadena de fecha y hora en formato 'YYYY-MM-DD HH:MM:SS' y devuelve solo la fecha en formato 'YYYY-MM-DD'.
    """Muestra solo la fecha."""
    if not fecha_str:
        return ''
    try:
        return datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    except ValueError:
        return fecha_str[:10] if len(fecha_str) >= 10 else ''


# ── Variables disponibles en todos los templates ──

@app.context_processor # Se define un procesador de contexto que inyecta variables en todos los templates de Jinja2.
def inyectar_datos_escuela(): # Se define la función inyectar_datos_escuela que devuelve un diccionario con información de la escuela, el docente y el grupo, que se puede usar en todos los templates de Jinja2.
    return {
        'DOCENTE': DOCENTE_NOMBRE,
        'GRUPO':   GRUPO_NOMBRE,
        'ESCUELA': ESCUELA_NOMBRE,
    }
    
@app.context_processor # Se define un procesador de contexto que inyecta variables en todos los templates de Jinja2.
def inyectar_pendientes(): # Se define la función inyectar_pendientes que devuelve un diccionario con la cantidad de pendientes para el alumno actual, que se puede usar en todos los templates de Jinja2.
    """Novedades del padre, para el menú de la campana."""
    if 'alumno_id' not in session:
        return {}
    return {'pendientes': repo_pendientes.resumen(session['alumno_id'])}
    
@app.template_filter('color_avatar') # Se define un filtro de plantilla llamado 'color_avatar' que se puede usar en los templates de Jinja2 para generar un color único y estable para cada alumno, derivado de su id.
def color_avatar(valor):
    """
    Color estable y único por alumno, derivado de su id.

    Usa el ángulo áureo para saltar por el círculo cromático, así dos ids
    consecutivos caen en tonos bien separados y no se repiten hasta pasar
    de 100 alumnos. Si el valor no sirve, devuelve un azul neutro.
    """
    try:
        tono = (int(valor) * 137) % 360
    except (TypeError, ValueError):
        tono = 210
    return (f'linear-gradient(135deg, hsl({tono},72%,58%), '
            f'hsl({(tono + 18) % 360},70%,45%))')

app.register_blueprint(auth_bp)
app.register_blueprint(alumno_bp)
app.register_blueprint(admin_bp)

init_db()


if __name__ == '__main__':
    print("=" * 55)
    print("  MI SALÓN — Sistema de seguimiento escolar")
    print("=" * 55)
    print("  Padres  →  http://127.0.0.1:5000")
    print("  Maestra →  http://127.0.0.1:5000/admin")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0')