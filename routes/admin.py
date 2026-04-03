from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from flask import make_response
import io

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db, hash_password
from email_utils import enviar_correo
from config import ADMIN_PASSWORD

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Login / Logout ──

@admin_bp.route('', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin.admin_dashboard'))
        flash('Contraseña incorrecta')
    return render_template('admin_login.html')


@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin.admin_panel'))


# ── Dashboard ──

@admin_bp.route('/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    conn    = get_db()
    alumnos = conn.execute('SELECT id, nombre, curp FROM alumnos ORDER BY nombre').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', alumnos=alumnos)


@admin_bp.route('/nuevo_alumno', methods=['POST'])
def nuevo_alumno():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
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
    except Exception:
        flash('Error: ese CURP ya existe')
    finally:
        conn.close()
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/accesos')
def admin_accesos():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    conn    = get_db()
    accesos = conn.execute('''
        SELECT a.nombre, a.curp, r.fecha, r.ip
        FROM registro_accesos r
        JOIN alumnos a ON r.id_alumno = a.id
        ORDER BY r.fecha DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    return render_template('admin_accesos.html', accesos=accesos)


# ── Expediente del alumno ──

@admin_bp.route('/alumno/<int:id_alumno>')
def admin_expediente(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

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

@admin_bp.route('/nueva_incidencia/<int:id_alumno>', methods=['POST'])
def nueva_incidencia(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    tipo        = request.form['tipo']
    descripcion = request.form['descripcion'].strip()
    conn        = get_db()
    conn.execute(
        'INSERT INTO incidencias (id_alumno, tipo, descripcion) VALUES (?, ?, ?)',
        (id_alumno, tipo, descripcion)
    )
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
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


# ── Nueva calificación ──

@admin_bp.route('/nueva_calificacion/<int:id_alumno>', methods=['POST'])
def nueva_calificacion(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
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
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


# ── Guardar perfil de personalidad ──

@admin_bp.route('/guardar_perfil/<int:id_alumno>', methods=['POST'])
def guardar_perfil(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
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
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


# ── Nueva actividad recomendada ──

@admin_bp.route('/nueva_actividad/<int:id_alumno>', methods=['POST'])
def nueva_actividad(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
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
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


# ── Avisos ──

@admin_bp.route('/avisos')
def admin_avisos():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    conn   = get_db()
    avisos = conn.execute('SELECT * FROM avisos ORDER BY fecha DESC').fetchall()
    conn.close()
    return render_template('admin_avisos.html', avisos=avisos)


@admin_bp.route('/nuevo_aviso', methods=['POST'])
def nuevo_aviso():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    titulo    = request.form['titulo'].strip()
    contenido = request.form['contenido'].strip()
    conn      = get_db()
    conn.execute('INSERT INTO avisos (titulo, contenido) VALUES (?, ?)', (titulo, contenido))
    conn.commit()
    conn.close()
    flash('Aviso publicado ✓')
    return redirect(url_for('admin.admin_avisos'))


@admin_bp.route('/desactivar_aviso/<int:id_aviso>')
def desactivar_aviso(id_aviso):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    conn = get_db()
    conn.execute('UPDATE avisos SET activo = 0 WHERE id = ?', (id_aviso,))
    conn.commit()
    conn.close()
    flash('Aviso desactivado ✓')
    return redirect(url_for('admin.admin_avisos'))


# ── Generar PDF del expediente ──
@admin_bp.route('/alumno/<int:id_alumno>/pdf')
def expediente_pdf(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    conn   = get_db()
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (id_alumno,)).fetchone()

    incidencias_raw = conn.execute('''
        SELECT i.*, s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
               s.comentario_padre
        FROM incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE i.id_alumno = ?
        ORDER BY i.fecha ASC
    ''', (id_alumno,)).fetchall()

    incidencias = []
    for idx, inc in enumerate(incidencias_raw, start=1):
        inc = dict(inc)
        inc['numero'] = idx
        incidencias.append(inc)

    calificaciones = conn.execute('''
        SELECT * FROM calificaciones WHERE id_alumno = ?
        ORDER BY periodo, materia
    ''', (id_alumno,)).fetchall()

    conn.close()

    # Generar PDF
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=inch, leftMargin=inch,
                               topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story  = []

    # Título
    titulo_style = ParagraphStyle('titulo', fontSize=18, fontName='Helvetica-Bold',
                                  spaceAfter=6, textColor=colors.HexColor('#2c3e50'))
    sub_style    = ParagraphStyle('sub', fontSize=10, fontName='Helvetica',
                                  spaceAfter=20, textColor=colors.HexColor('#636e72'))
    h2_style     = ParagraphStyle('h2', fontSize=13, fontName='Helvetica-Bold',
                                  spaceBefore=16, spaceAfter=8,
                                  textColor=colors.HexColor('#2c3e50'))
    normal       = ParagraphStyle('normal', fontSize=9, fontName='Helvetica',
                                  spaceAfter=4, textColor=colors.HexColor('#2d3436'))

    story.append(Paragraph(f"Expediente — {alumno['nombre']}", titulo_style))
    story.append(Paragraph(f"CURP: {alumno['curp']}  |  Generado: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))

    # Incidencias
    story.append(Paragraph("Incidencias", h2_style))
    if incidencias:
        data = [['#', 'Tipo', 'Fecha', 'Visto', 'Enterado', 'Respuesta del padre']]
        for inc in incidencias:
            data.append([
                str(inc['numero']),
                inc['tipo'] or '—',
                inc['fecha'][:10] if inc['fecha'] else '—',
                inc['fecha_visto'][:16] if inc.get('fecha_visto') else '✗',
                inc['fecha_enterado'][:16] if inc.get('fecha_enterado') else '✗',
                (inc['comentario_padre'] or '—')[:60]
            ])
        tabla = Table(data, colWidths=[0.3*inch, 0.8*inch, 0.9*inch, 1.2*inch, 1.2*inch, 2.1*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#dee2e6')),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING',     (0,0), (-1,-1), 4),
        ]))
        story.append(tabla)
    else:
        story.append(Paragraph("Sin incidencias registradas.", normal))

    # Calificaciones
    story.append(Paragraph("Calificaciones", h2_style))
    if calificaciones:
        data2 = [['Materia', 'Periodo', 'Calificación', 'Observación']]
        for cal in calificaciones:
            data2.append([
                cal['materia'],
                cal['periodo'] or '—',
                str(cal['calificacion']),
                (cal['comentario'] or '—')[:50]
            ])
        tabla2 = Table(data2, colWidths=[1.5*inch, 1.2*inch, 1*inch, 2.8*inch])
        tabla2.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#dee2e6')),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING',     (0,0), (-1,-1), 4),
        ]))
        story.append(tabla2)
    else:
        story.append(Paragraph("Sin calificaciones registradas.", normal))

    doc.build(story)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=expediente_{alumno["curp"]}.pdf'
    return response


