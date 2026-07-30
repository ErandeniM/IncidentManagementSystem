from datetime import datetime, timedelta

from flask import Flask

from config import SECRET_KEY, DOCENTE_NOMBRE, GRUPO_NOMBRE, ESCUELA_NOMBRE
from database import init_db
from routes.auth import auth_bp
from routes.alumno import alumno_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Cookies de sesión más seguras
app.config.update(
    SESSION_COOKIE_HTTPONLY = True,   # el JavaScript no puede leer la cookie
    SESSION_COOKIE_SAMESITE = 'Lax',  # evita envíos desde otros sitios
)


# ── Filtros de fecha para los templates ──

@app.template_filter('hora_local')
def hora_local(fecha_str):
    """Muestra solo la hora de una fecha guardada."""
    if not fecha_str:
        return ''
    try:
        return datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
    except ValueError:
        return fecha_str[11:16] if len(fecha_str) > 11 else ''


@app.template_filter('fecha_local')
def fecha_local(fecha_str):
    """Muestra solo la fecha."""
    if not fecha_str:
        return ''
    try:
        return datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    except ValueError:
        return fecha_str[:10] if len(fecha_str) >= 10 else ''


# ── Variables disponibles en todos los templates ──

@app.context_processor
def inyectar_datos_escuela():
    return {
        'DOCENTE': DOCENTE_NOMBRE,
        'GRUPO':   GRUPO_NOMBRE,
        'ESCUELA': ESCUELA_NOMBRE,
    }
    
@app.template_filter('color_avatar')
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