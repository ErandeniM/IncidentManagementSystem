from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from flask import make_response
import io
import csv
import io
import random

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
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

    conn = get_db()

    alumnos = conn.execute(
        'SELECT id, nombre, curp FROM alumnos ORDER BY nombre'
    ).fetchall()

    # Mensajes de padres no vistos
    mensajes_pendientes = conn.execute('''
        SELECT COUNT(*) AS n FROM mensajes
        WHERE remitente = 'padre' AND visto = 0
    ''').fetchone()['n']

    # Avisos de padres no vistos
    avisos_pendientes = conn.execute('''
        SELECT COUNT(*) AS n FROM avisos_padre
        WHERE visto_maestra = 0
    ''').fetchone()['n']

    # Incidencias sin firmar
    incidencias_sin_firmar = conn.execute('''
        SELECT COUNT(*) AS n FROM incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE s.enterado IS NULL OR s.enterado = 0
    ''').fetchone()['n']

    conn.close()
    return render_template('admin_dashboard.html',
                           alumnos                = alumnos,
                           mensajes_pendientes    = mensajes_pendientes,
                           avisos_pendientes      = avisos_pendientes,
                           incidencias_sin_firmar = incidencias_sin_firmar)


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
        SELECT i.*, s.visto, s.enterado, s.comentario_padre, s.firmado_por
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
        ORDER BY trimestre
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
        return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno) + '#tab-incidencias')

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
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno) + '#tab-perfil')

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
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno) + '#tab-actividades')


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
    titulo    = request.form['titulo']
    contenido = request.form['contenido']
    conn      = get_db()
    conn.execute(
        'INSERT INTO avisos (titulo, contenido) VALUES (?, ?)',
        (titulo, contenido)
    )
    conn.commit()
    conn.close()
    flash('Aviso publicado ✓')
    return redirect(url_for('admin.admin_avisos'))

# ═══════════ EDITAR AVISO ═══════════
@admin_bp.route('/aviso/editar/<int:id_aviso>', methods=['POST'])
def editar_aviso(id_aviso):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    titulo    = request.form['titulo']
    contenido = request.form['contenido']
    conn      = get_db()
    conn.execute('''
        UPDATE avisos
        SET titulo = ?, contenido = ?, fecha_actualizado = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (titulo, contenido, id_aviso))
    # Reset de confirmaciones: los padres deben volver a confirmar
    conn.execute('DELETE FROM avisos_confirmaciones WHERE id_aviso = ?', (id_aviso,))
    conn.commit()
    conn.close()
    flash('Aviso actualizado. Los padres deberán confirmar nuevamente.')
    return redirect(url_for('admin.admin_avisos'))


# ═══════════ ELIMINAR AVISO ═══════════
@admin_bp.route('/aviso/eliminar/<int:id_aviso>', methods=['POST'])
def eliminar_aviso(id_aviso):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    conn = get_db()
    conn.execute('DELETE FROM avisos_confirmaciones WHERE id_aviso = ?', (id_aviso,))
    conn.execute('DELETE FROM avisos WHERE id = ?', (id_aviso,))
    conn.commit()
    conn.close()
    flash('Aviso eliminado')
    return redirect(url_for('admin.admin_avisos'))


# ═══════════ VER CONFIRMACIONES DE UN AVISO ═══════════
@admin_bp.route('/aviso/confirmaciones/<int:id_aviso>')
def ver_confirmaciones(id_aviso):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))
    conn = get_db()
    aviso = conn.execute('SELECT * FROM avisos WHERE id = ?', (id_aviso,)).fetchone()

    confirmados = conn.execute('''
        SELECT a.id, a.nombre, a.curp, c.fecha_confirmado
        FROM alumnos a
        JOIN avisos_confirmaciones c ON c.id_alumno = a.id
        WHERE c.id_aviso = ?
        ORDER BY c.fecha_confirmado DESC
    ''', (id_aviso,)).fetchall()

    pendientes = conn.execute('''
        SELECT a.id, a.nombre, a.curp
        FROM alumnos a
        WHERE a.id NOT IN (
            SELECT id_alumno FROM avisos_confirmaciones WHERE id_aviso = ?
        )
        ORDER BY a.nombre
    ''', (id_aviso,)).fetchall()

    conn.close()
    return render_template('admin_confirmaciones.html',
                           aviso       = aviso,
                           confirmados = confirmados,
                           pendientes  = pendientes)
# ── Generar PDF del expediente ──
@admin_bp.route('/alumno/<int:id_alumno>/pdf')
def expediente_pdf(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    conn   = get_db()
    alumno = conn.execute('SELECT * FROM alumnos WHERE id = ?', (id_alumno,)).fetchone()

    incidencias_raw = conn.execute('''
        SELECT i.*, s.visto, s.fecha_visto, s.enterado, s.fecha_enterado,
               s.comentario_padre, s.firmado_por
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
        ORDER BY trimestre
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
        data2 = [['Trim.', 'Lenguajes', 'Ciencias', 'Ética', 'Comunitario', 'Faltas', 'Prom.']]
        for cal in calificaciones:
            notas  = [cal['lenguajes'], cal['ciencias'], cal['etica'], cal['comunitario']]
            llenas = [n for n in notas if n is not None]
            prom   = round(sum(llenas) / len(llenas), 1) if llenas else '—'
            data2.append([
                str(cal['trimestre']),
                *[('—' if n is None else str(int(n))) for n in notas],
                str(cal['inasistencias'] or 0),
                str(prom)
            ])
        tabla2 = Table(data2, colWidths=[0.5*inch, 1*inch, 1*inch, 1*inch, 1.1*inch, 0.6*inch, 0.6*inch])
        tabla2.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 8),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
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

# ═══════════ MENSAJES DE PADRES ═══════════

@admin_bp.route('/mensajes')
def admin_mensajes():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    conn = get_db()

    # Listar alumnos con mensajes, con conteo de no leídos por la maestra
    conversaciones = conn.execute('''
        SELECT a.id, a.nombre, a.curp,
               MAX(m.fecha) AS ultima_fecha,
               (SELECT contenido FROM mensajes
                WHERE id_alumno = a.id
                ORDER BY fecha DESC LIMIT 1) AS ultimo_mensaje,
               (SELECT remitente FROM mensajes
                WHERE id_alumno = a.id
                ORDER BY fecha DESC LIMIT 1) AS ultimo_remitente,
               SUM(CASE WHEN m.remitente = 'padre' AND m.visto = 0 THEN 1 ELSE 0 END) AS no_leidos
        FROM alumnos a
        INNER JOIN mensajes m ON m.id_alumno = a.id
        GROUP BY a.id
        ORDER BY ultima_fecha DESC
    ''').fetchall()

    conn.close()
    return render_template('admin_mensajes.html', conversaciones=conversaciones)


@admin_bp.route('/mensajes/<int:id_alumno>', methods=['GET', 'POST'])
def admin_chat(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    conn = get_db()

    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()
        if contenido:
            conn.execute('''
                INSERT INTO mensajes (id_alumno, remitente, contenido)
                VALUES (?, 'maestra', ?)
            ''', (id_alumno, contenido))
            conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_chat', id_alumno=id_alumno))

    # Marcar mensajes del padre como vistos por la maestra
    conn.execute('''
        UPDATE mensajes SET visto = 1, fecha_visto = CURRENT_TIMESTAMP
        WHERE id_alumno = ? AND remitente = 'padre' AND visto = 0
    ''', (id_alumno,))
    conn.commit()

    alumno = conn.execute(
        'SELECT * FROM alumnos WHERE id = ?', (id_alumno,)
    ).fetchone()

    mensajes = conn.execute('''
        SELECT * FROM mensajes
        WHERE id_alumno = ?
        ORDER BY fecha ASC
    ''', (id_alumno,)).fetchall()

    conn.close()
    return render_template('admin_chat.html',
                           alumno   = alumno,
                           mensajes = mensajes)

# ═══════════ AVISOS DE PADRES ═══════════

@admin_bp.route('/avisos-padres')
def admin_avisos_padres():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    conn = get_db()

    # Marcar como vistos al entrar
    conn.execute('''
        UPDATE avisos_padre SET visto_maestra = 1, fecha_visto = CURRENT_TIMESTAMP
        WHERE visto_maestra = 0
    ''')
    conn.commit()

    avisos = conn.execute('''
        SELECT ap.*, a.nombre AS nombre_alumno
        FROM avisos_padre ap
        JOIN alumnos a ON ap.id_alumno = a.id
        ORDER BY ap.fecha_creado DESC
        LIMIT 100
    ''').fetchall()

    conn.close()
    return render_template('admin_avisos_padres.html', avisos=avisos)

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
               s.comentario_padre, s.firmado_por
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
# ═══════════ TABLA DE CALIFICACIONES ═══════════

MATERIAS = [
    ('lenguajes',   'Lenguajes'),
    ('ciencias',    'Saberes y Pensamiento Científico'),
    ('etica',       'Ética, Naturaleza y Sociedades'),
    ('comunitario', 'De lo Humano y lo Comunitario'),
]


@admin_bp.route('/calificaciones')
def admin_calificaciones():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    trimestre = request.args.get('trimestre', 1, type=int)
    if trimestre not in (1, 2, 3):
        trimestre = 1

    conn = get_db()
    filas = conn.execute('''
        SELECT a.id, a.nombre, a.curp,
               c.lenguajes, c.ciencias, c.etica, c.comunitario,
               c.inasistencias, c.observaciones, c.fecha_actualizacion
        FROM alumnos a
        LEFT JOIN calificaciones c
            ON c.id_alumno = a.id AND c.trimestre = ?
        ORDER BY a.nombre
    ''', (trimestre,)).fetchall()
    conn.close()

    alumnos   = []
    completos = 0
    sumas     = {k: [] for k, _ in MATERIAS}

    for f in filas:
        f = dict(f)
        notas  = [f[k] for k, _ in MATERIAS]
        llenas = [n for n in notas if n is not None]
        f['completo'] = len(llenas) == len(MATERIAS)
        f['promedio'] = round(sum(llenas) / len(llenas), 1) if llenas else None
        if f['completo']:
            completos += 1
        for k, _ in MATERIAS:
            if f[k] is not None:
                sumas[k].append(f[k])
        alumnos.append(f)

    total        = len(alumnos)
    avance       = round(completos * 100 / total) if total else 0
    prom_materia = {k: (round(sum(v) / len(v), 1) if v else None) for k, v in sumas.items()}
    todas        = [n for v in sumas.values() for n in v]
    prom_grupo   = round(sum(todas) / len(todas), 1) if todas else None

    return render_template('admin_calificaciones.html',
                           alumnos      = alumnos,
                           trimestre    = trimestre,
                           materias     = MATERIAS,
                           completos    = completos,
                           total        = total,
                           avance       = avance,
                           prom_materia = prom_materia,
                           prom_grupo   = prom_grupo)


@admin_bp.route('/calificaciones/guardar', methods=['POST'])
def guardar_calificaciones():
    if not session.get('admin'):
        return jsonify({'ok': False}), 403

    d = request.get_json()

    def num(v):
        if v is None or v == '':
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    conn = get_db()
    conn.execute('''
        INSERT INTO calificaciones
            (id_alumno, trimestre, lenguajes, ciencias, etica, comunitario,
             inasistencias, observaciones, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id_alumno, trimestre) DO UPDATE SET
            lenguajes           = excluded.lenguajes,
            ciencias            = excluded.ciencias,
            etica               = excluded.etica,
            comunitario         = excluded.comunitario,
            inasistencias       = excluded.inasistencias,
            observaciones       = excluded.observaciones,
            fecha_actualizacion = CURRENT_TIMESTAMP
    ''', (
        d.get('id_alumno'),
        d.get('trimestre'),
        num(d.get('lenguajes')),
        num(d.get('ciencias')),
        num(d.get('etica')),
        num(d.get('comunitario')),
        int(d.get('inasistencias') or 0),
        (d.get('observaciones') or '').strip(),
    ))
    conn.commit()
    conn.close()

    notas  = [num(d.get(k)) for k, _ in MATERIAS]
    llenas = [n for n in notas if n is not None]
    return jsonify({
        'ok':       True,
        'completo': len(llenas) == len(MATERIAS),
        'promedio': round(sum(llenas) / len(llenas), 1) if llenas else None
    })
    
# ═══════════ RESETEAR CONTRASEÑA DE UN PADRE ═══════════

PALABRAS = ['casa', 'sol', 'luna', 'flor', 'mar', 'nube', 'arbol', 'rio', 'cielo', 'campo']


def generar_password():
    """Contraseña simple de dictar por teléfono. Ej: luna-4821"""
    return f"{random.choice(PALABRAS)}-{random.randint(1000, 9999)}"


@admin_bp.route('/alumno/<int:id_alumno>/password', methods=['POST'])
def resetear_password(id_alumno):
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    nueva = request.form.get('password_nueva', '').strip()
    if len(nueva) < 6:
        flash('La contraseña debe tener al menos 6 caracteres')
        return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))

    conn = get_db()
    conn.execute(
        'UPDATE alumnos SET password_hash = ? WHERE id = ?',
        (hash_password(nueva), id_alumno)
    )
    conn.commit()
    alumno = conn.execute(
        'SELECT nombre FROM alumnos WHERE id = ?', (id_alumno,)
    ).fetchone()
    conn.close()

    flash(f'Contraseña de {alumno["nombre"]} restablecida. Nueva contraseña: {nueva} ✓')
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


# ═══════════ ALTA MASIVA POR CSV ═══════════

@admin_bp.route('/alumnos/importar', methods=['GET', 'POST'])
def importar_alumnos():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    resultados = None

    if request.method == 'POST':
        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename:
            flash('No seleccionaste ningún archivo')
            return redirect(url_for('admin.importar_alumnos'))

        try:
            contenido = archivo.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            archivo.seek(0)
            contenido = archivo.read().decode('latin-1')

        lector = csv.DictReader(io.StringIO(contenido))
        conn   = get_db()
        creados, errores = [], []

        for num, fila in enumerate(lector, start=2):
            curp   = (fila.get('curp')   or '').strip().upper()
            nombre = (fila.get('nombre') or '').strip()
            correo = (fila.get('correo') or '').strip()
            passwd = (fila.get('contrasena') or '').strip() or generar_password()

            if not curp or not nombre:
                errores.append(f'Fila {num}: falta CURP o nombre')
                continue
            if len(curp) != 10:
                errores.append(f'Fila {num}: el CURP debe tener 10 caracteres ({curp})')
                continue

            try:
                conn.execute('''
                    INSERT INTO alumnos (curp, nombre, password_hash, correo_padre)
                    VALUES (?, ?, ?, ?)
                ''', (curp, nombre, hash_password(passwd), correo))
                creados.append({'curp': curp, 'nombre': nombre, 'password': passwd})
            except Exception:
                errores.append(f'Fila {num}: el CURP {curp} ya existe')

        conn.commit()
        conn.close()
        resultados = {'creados': creados, 'errores': errores}

    return render_template('admin_importar.html', resultados=resultados)


@admin_bp.route('/alumnos/plantilla-csv')
def plantilla_csv():
    if not session.get('admin'):
        return redirect(url_for('admin.admin_panel'))

    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(['curp', 'nombre', 'correo', 'contrasena'])
    escritor.writerow(['MABC010101', 'María G.', 'mama.maria@gmail.com', ''])
    escritor.writerow(['LOPZ020202', 'Juan P.', 'papa.juan@gmail.com', ''])

    respuesta = make_response('\ufeff' + salida.getvalue())
    respuesta.headers['Content-Type'] = 'text/csv; charset=utf-8'
    respuesta.headers['Content-Disposition'] = 'attachment; filename=plantilla_alumnos.csv'
    return respuesta
