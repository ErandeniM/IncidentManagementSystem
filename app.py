from flask import Flask
from config import SECRET_KEY
from database import init_db
from routes.auth import auth_bp
from routes.alumno import alumno_bp
from routes.admin import admin_bp

app = Flask(__name__)
from datetime import datetime, timedelta

@app.template_filter('hora_local')
def hora_local(fecha_str):
    """Convierte UTC a hora Sonora (UTC-7)"""
    if not fecha_str:
        return ''
    try:
        dt = datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S')
        dt_local = dt - timedelta(hours=7)
        return dt_local.strftime('%H:%M')
    except:
        return fecha_str[11:16] if len(fecha_str) > 11 else ''

@app.template_filter('fecha_local')
def fecha_local(fecha_str):
    """Convierte UTC a fecha Sonora"""
    if not fecha_str:
        return ''
    try:
        dt = datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S')
        dt_local = dt - timedelta(hours=7)
        return dt_local.strftime('%Y-%m-%d')
    except:
        return fecha_str[:10] if len(fecha_str) >= 10 else ''
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'

app.register_blueprint(auth_bp)
app.register_blueprint(alumno_bp)
app.register_blueprint(admin_bp)

init_db()

if __name__ == '__main__':
    print("=" * 55)
    print("  APP DE INCIDENCIAS ESCOLARES")
    print("=" * 55)
    print("  Padres  →  http://127.0.0.1:5000")
    print("  Maestra →  http://127.0.0.1:5000/admin")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0')

# ═══════════ TODAS LAS INCIDENCIAS DEL GRUPO ═══════════

@admin_bp.route('/incidencias')
def admin_todas_incidencias():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    filtro = request.args.get('filtro', 'todo')
    conn   = get_db()

    incidencias = conn.execute('''
        SELECT i.*, a.nombre AS nombre_alumno, a.curp,
               s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
               s.comentario_padre
        FROM incidencias i
        JOIN alumnos a ON i.id_alumno = a.id
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        ORDER BY i.fecha DESC
    ''').fetchall()

    if filtro == 'pendientes':
        incidencias = [i for i in incidencias if not i['enterado']]
    elif filtro == 'firmadas':
        incidencias = [i for i in incidencias if i['enterado']]

    conn.close()
    return render_template('admin_todas_incidencias.html',
                           incidencias = incidencias,
                           filtro      = filtro)
