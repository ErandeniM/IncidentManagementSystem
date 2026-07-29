from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db, hash_password, verificar_password
from repositorios import alumnos as repo_alumnos
from repositorios import accesos as repo_accesos
from repositorios import incidencias as repo_incidencias


alumno_bp = Blueprint('alumno', __name__)


# ═══════════ PANEL DEL PADRE ═══════════

@alumno_bp.route('/panel')
def panel_alumno():
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    filtro    = request.args.get('filtro', 'todo')
    conn      = get_db()
    

    # ═══ INCIDENCIAS ═══
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

    # ═══ AVISOS Y TAREAS ═══
    avisos = conn.execute('''
        SELECT a.*,
            CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END AS confirmado_por_padre
        FROM avisos a
        LEFT JOIN avisos_confirmaciones c
            ON c.id_aviso = a.id AND c.id_alumno = ?
        WHERE a.activo = 1
        ORDER BY a.fecha DESC
    ''', (alumno_id,)).fetchall()

    actividades = conn.execute('''
        SELECT * FROM actividades_recomendadas
        WHERE  id_alumno = ?
        ORDER  BY fecha DESC
    ''', (alumno_id,)).fetchall()

    # ═══ FEED UNIFICADO ═══
    publicaciones = []

    for inc in incidencias:
        tipo_pub = 'logro' if inc['tipo'] in ('logro', 'Logro') else 'incidencia'
        publicaciones.append({
            'tipo_pub': tipo_pub,
            'fecha':    inc['fecha'],
            'datos':    inc
        })

    for av in avisos:
        publicaciones.append({
            'tipo_pub': 'aviso',
            'fecha':    av['fecha'],
            'datos':    dict(av)
        })

    for act in actividades:
        publicaciones.append({
            'tipo_pub': 'tarea',
            'fecha':    act['fecha'] if 'fecha' in act.keys() else '',
            'datos':    dict(act)
        })

    publicaciones.sort(key=lambda x: x['fecha'] or '', reverse=True)

    # ═══ FILTROS ═══
    if filtro == 'incidencias':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'incidencia']
    elif filtro == 'logros':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'logro']
    elif filtro == 'avisos':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'aviso']
    elif filtro == 'tareas':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'tarea']

    # ═══ OTROS DATOS ═══
    calificaciones = conn.execute('''
         SELECT * FROM calificaciones
        WHERE  id_alumno = ?
        ORDER  BY trimestre
    ''', (alumno_id,)).fetchall()

    perfil = conn.execute(
        'SELECT * FROM perfil_alumno WHERE id_alumno = ?', (alumno_id,)
    ).fetchone()
    sin_firmar = sum(1 for i in incidencias if not i['enterado'])
    conn.close()
    return render_template('alumno.html',
                           nombre         = session['nombre'],
                           incidencias    = incidencias,
                           publicaciones  = publicaciones,
                           calificaciones = calificaciones,
                           perfil         = perfil,
                           actividades    = actividades,
                           avisos         = avisos,
                           filtro         = filtro,
                           sin_firmar = sin_firmar,
                           tipos_map      = repo_incidencias.TIPOS_MAP,
                           niveles_map    = repo_incidencias.NIVELES_MAP,)
    


# ═══════════ DETALLE DE INCIDENCIA ═══════════

@alumno_bp.route('/incidencia/<int:id_incidencia>')
def ver_incidencia(id_incidencia):
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    inc = repo_incidencias.obtener(id_incidencia, session['alumno_id'])
    if not inc:
        return redirect(url_for('alumno.panel_alumno'))

    if not inc['visto']:
        repo_incidencias.marcar_visto(id_incidencia)

    return render_template('detalle_incidencia.html', inc=inc,tipos_map      = repo_incidencias.TIPOS_MAP,
                           niveles_map    = repo_incidencias.NIVELES_MAP,)


# ═══════════ COMENTAR / FIRMA DE ENTERADO ═══════════

@alumno_bp.route('/comentar/<int:id_incidencia>', methods=['POST'])
def comentar(id_incidencia):
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    comentario = request.form.get('comentario', '').strip()
    if not comentario:
        flash('La respuesta es obligatoria para marcar como enterado')
        return redirect(url_for('alumno.ver_incidencia', id_incidencia=id_incidencia))

    alumno_id = session['alumno_id']

    if repo_incidencias.pertenece_a(id_incidencia, alumno_id):
        tutor = repo_alumnos.nombre_del_tutor(alumno_id)
        repo_incidencias.firmar(
            id_incidencia = id_incidencia,
            comentario    = comentario,
            firmado_por   = tutor or f'Tutor de {session["nombre"]}'
        )
        flash('Respuesta registrada ✓')

    return redirect(url_for('alumno.panel_alumno'))

# ═══════════ CHAT: PREGUNTAR A LA MAESTRA ═══════════

@alumno_bp.route('/chat', methods=['GET', 'POST'])
def chat_maestra():
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    conn      = get_db()

    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()
        if contenido:
            conn.execute('''
                INSERT INTO mensajes (id_alumno, remitente, contenido)
                VALUES (?, 'padre', ?)
            ''', (alumno_id, contenido))
            conn.commit()
        conn.close()
        return redirect(url_for('alumno.chat_maestra'))

    conn.execute('''
        UPDATE mensajes SET visto = 1, fecha_visto = CURRENT_TIMESTAMP
        WHERE id_alumno = ? AND remitente = 'maestra' AND visto = 0
    ''', (alumno_id,))
    conn.commit()

    mensajes = conn.execute('''
        SELECT * FROM mensajes
        WHERE id_alumno = ?
        ORDER BY fecha ASC
    ''', (alumno_id,)).fetchall()

    mensajes_nuevos = 0

    conn.close()
    return render_template('chat_padre.html',
                           nombre          = session['nombre'],
                           mensajes        = mensajes,
                           mensajes_nuevos = mensajes_nuevos)
    
# ═══════════ AVISAR A LA MAESTRA ═══════════

@alumno_bp.route('/avisar', methods=['GET', 'POST'])
def avisar_maestra():
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    conn      = get_db()

    if request.method == 'POST':
        tipo         = request.form.get('tipo')
        detalle      = request.form.get('detalle', '').strip()
        fecha_aplica = request.form.get('fecha_aplica', '') or None
        hora_aplica  = request.form.get('hora_aplica', '') or None

        if tipo:
            conn.execute('''
                INSERT INTO avisos_padre (id_alumno, tipo, detalle, fecha_aplica, hora_aplica)
                VALUES (?, ?, ?, ?, ?)
            ''', (alumno_id, tipo, detalle, fecha_aplica, hora_aplica))
            conn.commit()
            flash('Aviso enviado a la maestra ✓')
        conn.close()
        return redirect(url_for('alumno.avisar_maestra'))

    # Historial de avisos enviados por este padre
    avisos_enviados = conn.execute('''
        SELECT * FROM avisos_padre
        WHERE id_alumno = ?
        ORDER BY fecha_creado DESC
    ''', (alumno_id,)).fetchall()

    conn.close()
    return render_template('avisar_maestra.html',
                           nombre          = session['nombre'],
                           avisos_enviados = avisos_enviados)
    
# ═══════════ CONFIRMAR AVISO GENERAL ═══════════

@alumno_bp.route('/aviso/confirmar/<int:id_aviso>', methods=['POST'])
def confirmar_aviso(id_aviso):
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    conn.execute('''
        INSERT OR IGNORE INTO avisos_confirmaciones (id_aviso, id_alumno)
        VALUES (?, ?)
    ''', (id_aviso, session['alumno_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('alumno.panel_alumno'))
# ═══════════ MI PERFIL (VISTA DEL PADRE) ═══════════

@alumno_bp.route('/perfil')
def mi_perfil():
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    conn      = get_db()

    alumno = conn.execute(
        'SELECT * FROM alumnos WHERE id = ?', (alumno_id,)
    ).fetchone()

    calificaciones = conn.execute('''
          SELECT * FROM calificaciones
        WHERE  id_alumno = ?
        ORDER  BY trimestre
    ''', (alumno_id,)).fetchall()

    perfil = conn.execute(
        'SELECT * FROM perfil_alumno WHERE id_alumno = ?', (alumno_id,)
    ).fetchone()

    actividades = conn.execute('''
        SELECT * FROM actividades_recomendadas
        WHERE  id_alumno = ?
        ORDER  BY fecha DESC
    ''', (alumno_id,)).fetchall()

    # Promedio general (calculado en Python)
    todas = []
    
    for c in calificaciones:
        for campo in ('lenguajes', 'ciencias', 'etica', 'comunitario'):
            if c[campo] is not None:
                todas.append(c[campo])
    promedio = round(sum(todas) / len(todas), 1) if todas else None

    # Contadores
    total_logros = repo_incidencias.contar_logros(alumno_id)
    total_firmadas = repo_incidencias.contar_firmadas(alumno_id)

    conn.close()
    return render_template('mi_perfil.html',
                           nombre         = session['nombre'],
                           alumno         = alumno,
                           calificaciones = calificaciones,
                           perfil         = perfil,
                           actividades    = actividades,
                           promedio       = promedio,
                           total_logros   = total_logros,
                           total_firmadas = total_firmadas)
    
# ═══════════ CONFIGURACIÓN DEL PADRE ═══════════

@alumno_bp.route('/configuracion', methods=['GET', 'POST'])
def configuracion():
    if 'alumno_id' not in session:
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'datos':
            repo_alumnos.actualizar_datos_tutor(
                id_alumno    = alumno_id,
                nombre_tutor = request.form.get('nombre_tutor', '').strip(),
                correo_padre = request.form.get('correo_padre', '').strip(),
                notif_correo = request.form.get('notif_correo')
            )
            flash('Datos actualizados ✓')

        elif accion == 'password':
            actual  = request.form.get('password_actual', '')
            nueva   = request.form.get('password_nueva', '')
            repetir = request.form.get('password_repetir', '')

            alumno = repo_alumnos.obtener_por_id(alumno_id)
            valida, _ = verificar_password(actual, alumno['password_hash'])

            if not valida:
                flash('La contraseña actual no es correcta')
            elif len(nueva) < 6:
                flash('La nueva contraseña debe tener al menos 6 caracteres')
            elif nueva != repetir:
                flash('Las contraseñas nuevas no coinciden')
            else:
                repo_alumnos.actualizar_password(alumno_id, hash_password(nueva))
                flash('Contraseña actualizada ✓')

        return redirect(url_for('alumno.configuracion'))

    return render_template('configuracion.html',
                           nombre  = session['nombre'],
                           alumno  = repo_alumnos.obtener_por_id(alumno_id),
                           accesos = repo_accesos.ultimos_de_alumno(alumno_id))