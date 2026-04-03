from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db

alumno_bp = Blueprint('alumno', __name__)


@alumno_bp.route('/panel')
def panel_alumno():
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

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


@alumno_bp.route('/incidencia/<int:id_incidencia>')
def ver_incidencia(id_incidencia):
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    inc  = conn.execute('''
        SELECT i.*, s.visto, s.fecha_visto, s.enterado,
               s.fecha_enterado, s.comentario_padre, s.fecha_comentario
        FROM incidencias i
        LEFT JOIN incidencia_seguimiento s ON i.id = s.id_incidencia
        WHERE i.id = ? AND i.id_alumno = ?
    ''', (id_incidencia, session['alumno_id'])).fetchone()

    if not inc:
        return redirect(url_for('alumno.panel_alumno'))

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


@alumno_bp.route('/comentar/<int:id_incidencia>', methods=['POST'])
def comentar(id_incidencia):
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    comentario = request.form.get('comentario', '').strip()
    if not comentario:
        flash('La respuesta es obligatoria para marcar como enterado')
        return redirect(url_for('alumno.ver_incidencia', id_incidencia=id_incidencia))

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
    return redirect(url_for('alumno.panel_alumno'))
