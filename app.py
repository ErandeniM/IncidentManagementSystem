from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)
app.secret_key = 'mi_clave_secreta_2024'
app.config['SESSION_TYPE'] = 'filesystem'

DATABASE = 'incidencias.db'
ADMIN_PASSWORD = "1234"
CORREO_REMITENTE = "maestra.erandeni@gmail.com"
CORREO_CLAVE     = "herr kgjl yoqp epqm"

def enviar_correo(destinatario, asunto, cuerpo_html):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = CORREO_REMITENTE
        msg['To']      = destinatario
        msg.attach(MIMEText(cuerpo_html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(CORREO_REMITENTE, CORREO_CLAVE)
            smtp.sendmail(CORREO_REMITENTE, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
# ════════════════════════════════════════════════
#  UTILIDADES DE BASE DE DATOS
# ════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    if not os.path.exists(DATABASE):
        print("Creando base de datos...")
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema = f.read()
        conn = get_db()
        conn.executescript(schema)
        conn.execute(
            'INSERT INTO alumnos (curp, nombre, password_hash) VALUES (?, ?, ?)',
            ('MABC010101', 'María G.', hash_password('maria2024'))
        )
        conn.commit()
        conn.close()
        print("Base de datos creada con alumno de ejemplo: CURP=MABC010101 / pass=maria2024")

init_db()


# ════════════════════════════════════════════════
#  LOGIN PADRES
# ════════════════════════════════════════════════

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        curp     = request.form['curp'].strip().upper()
        password = request.form['password']
        conn     = get_db()
        alumno   = conn.execute(
            'SELECT * FROM alumnos WHERE curp = ?', (curp,)
        ).fetchone()
        conn.close()
        if alumno and alumno['password_hash'] == hash_password(password):
            session['alumno_id'] = alumno['id']
            session['nombre']    = alumno['nombre']
            conn2 = get_db()
            conn2.execute(
                'INSERT INTO registro_accesos (id_alumno, ip) VALUES (?, ?)',
                (alumno['id'], request.remote_addr)
            )
            conn2.commit()
            conn2.close()
            return redirect(url_for('panel_alumno'))
        flash('CURP o contraseña incorrectos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ════════════════════════════════════════════════
#  PANEL DEL PADRE
# ════════════════════════════════════════════════

@app.route('/panel')
def panel_alumno():
    if 'alumno_id' not in session:
        return redirect(url_for('login'))

    alumno_id = session['alumno_id']
    conn      = get_db()

    incidencias_raw = conn.execute('''
        SELECT i.*, s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
               s.comentario_padre, s.fecha_comentario
        FROM   incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE  i.id_alumno = ?
        ORDER  BY i.fecha ASC
    ''', (alumno_id,)).fetchall()

    incidencias = []
    for idx, inc in enumerate(incidencias_raw, start=1):
        inc = dict(inc)
        inc['numero'] = idx
        incidencias.append(inc)
    incidencias.reverse()

    calificaciones = conn.execute('''
        SELECT * FROM calificaciones
        WHERE  id_alumno = ?
        ORDER  BY periodo, materia
    ''', (alumno_id,)).fetchall()

    perfil = conn.execute(
        'SELECT * FROM perfil_alumno WHERE id_alumno = ?', (alumno_id,)
    ).fetchone()

    actividades = conn.execute('''
        SELECT * FROM actividades_recomendadas
        WHERE  id_alumno = ?
        ORDER  BY completada ASC, fecha DESC
    ''', (alumno_id,)).fetchall()
    
    avisos = conn.execute(
        'SELECT * FROM avisos WHERE activo = 1 ORDER BY fecha DESC'
    ).fetchall()
    

    conn.close()
    return render_template('alumno.html',
                           nombre         = session['nombre'],
                           incidencias    = incidencias,
                           calificaciones = calificaciones,
                           perfil         = perfil,
                           actividades    = actividades,
                           avisos         = avisos)


# ── Ver detalle de incidencia (visto automático) ──
@app.route('/incidencia/<int:id_incidencia>')
def ver_incidencia(id_incidencia):
    if 'alumno_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    inc = conn.execute('''
        SELECT i.*, s.visto, s.fecha_visto, s.enterado,
               s.fecha_enterado, s.comentario_padre, s.fecha_comentario
        FROM incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE i.id = ? AND i.id_alumno = ?
    ''', (id_incidencia, session['alumno_id'])).fetchone()

    if not inc:
        return redirect(url_for('panel_alumno'))

    if not inc['visto']:
        conn.execute('''
            INSERT INTO incidencia_seguimiento
                (id_incidencia, visto, fecha_visto)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(id_incidencia) DO UPDATE SET
                visto = 1, fecha_visto = CURRENT_TIMESTAMP
        ''', (id_incidencia,))
        conn.commit()

    conn.close()
    return render_template('detalle_incidencia.html', inc=inc)


# ── Comentar / Firma de enterado ──
@app.route('/comentar/<int:id_incidencia>', methods=['POST'])
def comentar(id_incidencia):
    if 'alumno_id' not in session:
        return redirect(url_for('login'))

    comentario = request.form.get('comentario', '').strip()
    if not comentario:
        flash('La respuesta es obligatoria para marcar como enterado')
        return redirect(url_for('ver_incidencia', id_incidencia=id_incidencia))

    conn = get_db()
    inc  = conn.execute(
        'SELECT id_alumno FROM incidencias WHERE id = ?', (id_incidencia,)
    ).fetchone()

    if inc and inc['id_alumno'] == session['alumno_id']:
        conn.execute('''
            INSERT INTO incidencia_seguimiento
                (id_incidencia, enterado, fecha_enterado,
                 comentario_padre, fecha_comentario)
            VALUES (?, 1, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id_incidencia) DO UPDATE SET
                enterado         = 1,
                fecha_enterado   = CURRENT_TIMESTAMP,
                comentario_padre = ?,
                fecha_comentario = CURRENT_TIMESTAMP
        ''', (id_incidencia, comentario, comentario))
        conn.commit()
        flash('Respuesta registrada ✓')

    conn.close()
    return redirect(url_for('panel_alumno'))


# ════════════════════════════════════════════════
#  ADMIN — LOGIN
# ════════════════════════════════════════════════

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Contraseña incorrecta')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_panel'))


# ════════════════════════════════════════════════
#  ADMIN — DASHBOARD
# ════════════════════════════════════════════════

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn    = get_db()
    alumnos = conn.execute('SELECT id, nombre, curp FROM alumnos ORDER BY nombre').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', alumnos=alumnos)

@app.route('/admin/nuevo_alumno', methods=['POST'])
def nuevo_alumno():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    curp          = request.form['curp'].strip().upper()
    nombre        = request.form['nombre'].strip()
    password_hash = hash_password(request.form['password'])
    correo_padre  = request.form.get('correo_padre', '').strip()
    conn          = get_db()
    try:
        conn.execute(
            'INSERT INTO alumnos (curp, nombre, password_hash, correo_padre) VALUES (?, ?, ?, ?)',
            (curp, nombre, password_hash, correo_padre)
        )
        conn.commit()
        flash(f'Alumno {nombre} registrado correctamente ✓')
    except sqlite3.IntegrityError:
        flash('Error: ese CURP ya existe')
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/accesos')
def admin_accesos():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn = get_db()
    accesos = conn.execute('''
        SELECT a.nombre, a.curp, r.fecha, r.ip
        FROM registro_accesos r
        JOIN alumnos a ON r.id_alumno = a.id
        ORDER BY r.fecha DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    return render_template('admin_accesos.html', accesos=accesos)


# ════════════════════════════════════════════════
#  ADMIN — EXPEDIENTE DEL ALUMNO
# ════════════════════════════════════════════════

@app.route('/admin/alumno/<int:id_alumno>')
def admin_expediente(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))

    conn   = get_db()
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (id_alumno,)).fetchone()

    incidencias_raw = conn.execute('''
        SELECT i.*, s.visto, s.enterado, s.comentario_padre
        FROM   incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE  i.id_alumno = ?
        ORDER  BY i.fecha ASC
    ''', (id_alumno,)).fetchall()

    incidencias = []
    for idx, inc in enumerate(incidencias_raw, start=1):
        inc = dict(inc)
        inc['numero'] = idx
        incidencias.append(inc)
    incidencias.reverse()

    calificaciones = conn.execute('''
        SELECT * FROM calificaciones WHERE id_alumno = ?
        ORDER BY periodo, materia
    ''', (id_alumno,)).fetchall()

    perfil = conn.execute(
        'SELECT * FROM perfil_alumno WHERE id_alumno = ?', (id_alumno,)
    ).fetchone()

    actividades = conn.execute('''
        SELECT * FROM actividades_recomendadas WHERE id_alumno = ?
        ORDER BY completada ASC, fecha DESC
    ''', (id_alumno,)).fetchall()

    conn.close()
    return render_template('admin_expediente.html',
                           alumno         = alumno,
                           incidencias    = incidencias,
                           calificaciones = calificaciones,
                           perfil         = perfil,
                           actividades    = actividades,
                           id_alumno      = id_alumno)


# ── Nueva incidencia ──
@app.route('/admin/nueva_incidencia/<int:id_alumno>', methods=['POST'])
def nueva_incidencia(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    tipo        = request.form['tipo']
    descripcion = request.form['descripcion'].strip()
    conn        = get_db()
    conn.execute('INSERT INTO incidencias (id_alumno, tipo, descripcion) VALUES (?, ?, ?)',
                 (id_alumno, tipo, descripcion))
    conn.commit()
    alumno = conn.execute(
        'SELECT nombre, correo_padre FROM alumnos WHERE id = ?', (id_alumno,)
    ).fetchone()
    conn.close()

    if alumno and alumno['correo_padre']:
        asunto = f"Nueva notificación — {alumno['nombre']}"
        cuerpo = f"""
        <div style="font-family:sans-serif; max-width:500px; margin:0 auto;">
            <div style="background:linear-gradient(135deg,#ff8c42,#ff6b6b); padding:1.5rem; border-radius:12px 12px 0 0;">
                <h2 style="color:#fff; margin:0;">📋 Nueva notificación escolar</h2>
            </div>
            <div style="background:#fff; padding:1.5rem; border:1px solid #f0f0f0; border-radius:0 0 12px 12px;">
                <p style="color:#636e72;">Se ha registrado una nueva notificación para <strong>{alumno['nombre']}</strong>.</p>
                <div style="background:#fff8f0; border-left:4px solid #ff8c42; padding:1rem; border-radius:0 8px 8px 0; margin:1rem 0;">
                    <strong style="color:#2d3436;">Tipo:</strong> {tipo}<br>
                </div>
                <p style="color:#636e72;">Ingresa al portal para ver el detalle completo y registrar tu firma de enterado.</p>
                <p style="color:#b2bec3; font-size:.8rem; margin-top:2rem;">
                    Este es un mensaje automático del sistema escolar.
                </p>
            </div>
        </div>
        """
        enviar_correo(alumno['correo_padre'], asunto, cuerpo)
    
    flash('Incidencia registrada ✓')
    return redirect(url_for('admin_expediente', id_alumno=id_alumno))

# ── Nueva calificación ──
@app.route('/admin/nueva_calificacion/<int:id_alumno>', methods=['POST'])
def nueva_calificacion(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn = get_db()
    conn.execute('''
        INSERT INTO calificaciones (id_alumno, materia, periodo, calificacion, comentario)
        VALUES (?, ?, ?, ?, ?)
    ''', (id_alumno,
          request.form['materia'].strip(),
          request.form['periodo'].strip(),
          float(request.form['calificacion']),
          request.form.get('comentario', '').strip()))
    conn.commit()
    conn.close()
    flash('Calificación guardada ✓')
    return redirect(url_for('admin_expediente', id_alumno=id_alumno))


# ── Guardar perfil de personalidad ──
@app.route('/admin/guardar_perfil/<int:id_alumno>', methods=['POST'])
def guardar_perfil(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn = get_db()
    conn.execute('''
        INSERT INTO perfil_alumno
            (id_alumno, logico, fisico, artistico, social, lenguaje, nota, actualizado)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id_alumno) DO UPDATE SET
            logico      = excluded.logico,
            fisico      = excluded.fisico,
            artistico   = excluded.artistico,
            social      = excluded.social,
            lenguaje    = excluded.lenguaje,
            nota        = excluded.nota,
            actualizado = CURRENT_TIMESTAMP
    ''', (id_alumno,
          int(request.form.get('logico',    0)),
          int(request.form.get('fisico',    0)),
          int(request.form.get('artistico', 0)),
          int(request.form.get('social',    0)),
          int(request.form.get('lenguaje',  0)),
          request.form.get('nota', '').strip()))
    conn.commit()
    conn.close()
    flash('Perfil actualizado ✓')
    return redirect(url_for('admin_expediente', id_alumno=id_alumno))


# ── Nueva actividad recomendada ──
@app.route('/admin/nueva_actividad/<int:id_alumno>', methods=['POST'])
def nueva_actividad(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn = get_db()
    conn.execute('''
        INSERT INTO actividades_recomendadas (id_alumno, actividad, categoria)
        VALUES (?, ?, ?)
    ''', (id_alumno,
          request.form['actividad'].strip(),
          request.form.get('categoria', 'General')))
    conn.commit()
    conn.close()
    flash('Actividad agregada ✓')
    return redirect(url_for('admin_expediente', id_alumno=id_alumno))


# ════════════════════════════════════════════════
#  AVISOS
# ════════════════════════════════════════════════

@app.route('/admin/avisos')
def admin_avisos():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn = get_db()
    avisos = conn.execute(
        'SELECT * FROM avisos ORDER BY fecha DESC'
    ).fetchall()
    conn.close()
    return render_template('admin_avisos.html', avisos=avisos)

@app.route('/admin/nuevo_aviso', methods=['POST'])
def nuevo_aviso():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    titulo    = request.form['titulo'].strip()
    contenido = request.form['contenido'].strip()
    conn = get_db()
    conn.execute(
        'INSERT INTO avisos (titulo, contenido) VALUES (?, ?)',
        (titulo, contenido)
    )
    conn.commit()
    conn.close()
    flash('Aviso publicado ✓')
    return redirect(url_for('admin_avisos'))

@app.route('/admin/desactivar_aviso/<int:id_aviso>')
def desactivar_aviso(id_aviso):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    conn = get_db()
    conn.execute('UPDATE avisos SET activo = 0 WHERE id = ?', (id_aviso,))
    conn.commit()
    conn.close()
    flash('Aviso desactivado ✓')
    return redirect(url_for('admin_avisos'))

if __name__ == '__main__':
    print("=" * 55)
    print("  APP DE INCIDENCIAS ESCOLARES")
    print("=" * 55)
    print("  Padres  →  http://127.0.0.1:5000")
    print("  Maestra →  http://127.0.0.1:5000/admin")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0')l'))
    conn = get_db()
    conn.execute('UPDATE avisos SET activo = 0 WHERE id = ?', (id_aviso,))
    conn.commit()
    conn.close()
    flash('Aviso desactivado ✓')
    return redirect(url_for('admin_avisos'))

if __name__ == '__main__':
    print("=" * 55)
    print("  APP DE INCIDENCIAS ESCOLARES")
    print("=" * 55)
    print("  Padres  →  http://127.0.0.1:5000")
    print("  Maestra →  http://127.0.0.1:5000/admin")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0')