"""
Rutas del portal de padres.

Ninguna función de este archivo escribe SQL: todo el acceso a datos
pasa por la capa de repositorios.
"""

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash)

from database import hash_password, verificar_password
import notificaciones

from repositorios import alumnos as repo_alumnos
from repositorios import accesos as repo_accesos
from repositorios import incidencias as repo_incidencias
from repositorios import avisos as repo_avisos
from repositorios import mensajes as repo_mensajes
from repositorios import academico as repo_academico
from repositorios import tareas as repo_tareas

alumno_bp = Blueprint('alumno', __name__)


def _sesion_activa():
    return 'alumno_id' in session


# ═══════════ PANEL DEL PADRE ═══════════

@alumno_bp.route('/panel')
def panel_alumno():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    filtro    = request.args.get('filtro', 'todo')

    # ── Datos ──
    incidencias    = repo_incidencias.de_alumno(alumno_id)
    avisos         = repo_avisos.activos_para(alumno_id)
    actividades    = repo_academico.actividades_de(alumno_id)
    tareas         = repo_tareas.de_alumno(alumno_id)
    calificaciones = repo_academico.calificaciones_de(alumno_id)
    perfil         = repo_academico.perfil_de(alumno_id)

    # ── Feed unificado ──
    publicaciones = []

    for inc in incidencias:
        publicaciones.append({
            'tipo_pub': 'logro' if inc['tipo'] in ('logro', 'Logro') else 'incidencia',
            'fecha':    inc['fecha'],
            'datos':    inc
        })

    for av in avisos:
        publicaciones.append({
            'tipo_pub': 'aviso',
            'fecha':    av['fecha'],
            'datos':    av
        })

    for act in actividades:
        publicaciones.append({
            'tipo_pub': 'tarea',
            'fecha':    act.get('fecha') or '',
            'datos':    act
        })

    for tar in tareas:
        publicaciones.append({
            'tipo_pub': 'tarea_entrega',
            'fecha':    tar.get('fecha_asignada') or '',
            'datos':    tar
        })

    publicaciones.sort(key=lambda x: x['fecha'] or '', reverse=True)

    # ── Filtros ──
    if filtro == 'incidencias':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'incidencia']
    elif filtro == 'logros':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'logro']
    elif filtro == 'avisos':
        publicaciones = [p for p in publicaciones if p['tipo_pub'] == 'aviso']
    elif filtro == 'tareas':
        publicaciones = [p for p in publicaciones
                         if p['tipo_pub'] in ('tarea', 'tarea_entrega')]

    return render_template('alumno.html',
        nombre          = session['nombre'],
        incidencias     = incidencias,
        publicaciones   = publicaciones,
        calificaciones  = calificaciones,
        perfil          = perfil,
        actividades     = actividades,
        avisos          = avisos,
        filtro          = filtro,
        sin_firmar      = sum(1 for i in incidencias if not i['enterado']),
        mensajes_nuevos = repo_mensajes.contar_no_leidos_padre(alumno_id),
        tipos_map       = repo_incidencias.TIPOS_MAP,
        niveles_map     = repo_incidencias.NIVELES_MAP,
        estados_map     = repo_tareas.ESTADOS_MAP)


# ═══════════ DETALLE DE INCIDENCIA ═══════════

@alumno_bp.route('/incidencia/<int:id_incidencia>')
def ver_incidencia(id_incidencia):
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    inc = repo_incidencias.obtener(id_incidencia, session['alumno_id'])
    if not inc:
        return redirect(url_for('alumno.panel_alumno'))

    if not inc['visto']:
        repo_incidencias.marcar_visto(id_incidencia)

    return render_template('detalle_incidencia.html',
                           inc         = inc,
                           tipos_map   = repo_incidencias.TIPOS_MAP,
                           niveles_map = repo_incidencias.NIVELES_MAP,
                           declaracion = repo_incidencias.TEXTO_DECLARACION,
                           minimo      = repo_incidencias.MINIMO_RESPUESTA)


# ═══════════ FIRMA DE ENTERADO ═══════════

@alumno_bp.route('/comentar/<int:id_incidencia>', methods=['POST'])
def comentar(id_incidencia):
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    comentario = request.form.get('comentario', '').strip()
    acepto     = request.form.get('acepto_declaracion')
    minimo     = repo_incidencias.MINIMO_RESPUESTA

    if not acepto:
        flash('Debes marcar la casilla para firmar de enterado')
        return redirect(url_for('alumno.ver_incidencia', id_incidencia=id_incidencia))

    if len(comentario) < minimo:
        flash(f'Escribe una respuesta de al menos {minimo} caracteres')
        return redirect(url_for('alumno.ver_incidencia', id_incidencia=id_incidencia))

    alumno_id = session['alumno_id']

    if repo_incidencias.pertenece_a(id_incidencia, alumno_id):
        tutor = repo_alumnos.nombre_del_tutor(alumno_id)
        repo_incidencias.firmar(
            id_incidencia = id_incidencia,
            comentario    = comentario,
            firmado_por   = tutor or f'Tutor de {session["nombre"]}'
        )
        flash('Firma y respuesta registradas ✓')

    return redirect(url_for('alumno.panel_alumno'))


# ═══════════ CHAT CON LA MAESTRA ═══════════

@alumno_bp.route('/chat', methods=['GET', 'POST'])
def chat_maestra():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']

    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()
        if contenido:
            repo_mensajes.enviar(
                id_alumno  = alumno_id,
                remitente  = 'padre',
                contenido  = contenido,
                ref_tipo   = request.form.get('ref_tipo') or None,
                ref_id     = request.form.get('ref_id') or None,
                ref_titulo = request.form.get('ref_titulo') or None
            )
            notificaciones.avisar_a_docente(
                asunto  = f'Mensaje del tutor de {session["nombre"]}',
                titulo  = 'Nuevo mensaje de un tutor',
                mensaje = f'El tutor de <b>{session["nombre"]}</b> te escribió '
                          f'en el chat privado.'
            )
        return redirect(url_for('alumno.chat_maestra'))

    repo_mensajes.marcar_vistos(alumno_id, 'maestra')

    return render_template('chat_padre.html',
                           nombre          = session['nombre'],
                           mensajes        = repo_mensajes.conversacion(alumno_id),
                           mensajes_nuevos = 0,
                           ref_tipo        = request.args.get('ref_tipo'),
                           ref_id          = request.args.get('ref_id'),
                           ref_titulo      = request.args.get('ref_titulo'))


# ═══════════ AVISAR A LA MAESTRA ═══════════

@alumno_bp.route('/avisar', methods=['GET', 'POST'])
def avisar_maestra():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']

    if request.method == 'POST':
        tipo = request.form.get('tipo')
        if tipo:
            repo_avisos.crear_de_padre(
                id_alumno    = alumno_id,
                tipo         = tipo,
                detalle      = request.form.get('detalle', '').strip(),
                fecha_aplica = request.form.get('fecha_aplica') or None,
                hora_aplica  = request.form.get('hora_aplica') or None
            )
            notificaciones.avisar_a_docente(
                asunto  = f'Aviso del tutor de {session["nombre"]}',
                titulo  = 'Nuevo aviso de un tutor',
                mensaje = f'El tutor de <b>{session["nombre"]}</b> envió un aviso. '
                          f'Revísalo en el panel.'
            )
            flash('Aviso enviado a la maestra ✓')
        return redirect(url_for('alumno.avisar_maestra'))

    return render_template('avisar_maestra.html',
                           nombre          = session['nombre'],
                           avisos_enviados = repo_avisos.de_padre(alumno_id))


# ═══════════ CONFIRMAR AVISO GENERAL ═══════════

@alumno_bp.route('/aviso/confirmar/<int:id_aviso>', methods=['POST'])
def confirmar_aviso(id_aviso):
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    repo_avisos.confirmar(id_aviso, session['alumno_id'])
    return redirect(url_for('alumno.panel_alumno'))


# ═══════════ MI PERFIL ═══════════

@alumno_bp.route('/perfil')
def mi_perfil():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']

    return render_template('mi_perfil.html',
        nombre          = session['nombre'],
        alumno          = repo_alumnos.obtener_por_id(alumno_id),
        calificaciones  = repo_academico.calificaciones_de(alumno_id),
        perfil          = repo_academico.perfil_de(alumno_id),
        actividades     = repo_academico.actividades_de(alumno_id),
        promedio        = repo_academico.promedio_general(alumno_id),
        total_logros    = repo_incidencias.contar_logros(alumno_id),
        total_firmadas  = repo_incidencias.contar_firmadas(alumno_id),
        tareas          = repo_tareas.resumen_alumno(alumno_id))


# ═══════════ CONFIGURACIÓN ═══════════

@alumno_bp.route('/configuracion', methods=['GET', 'POST'])
def configuracion():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'datos':
            repo_alumnos.actualizar_datos_tutor(
                id_alumno    = alumno_id,
                nombre_tutor = request.form.get('nombre_tutor', '').strip(),
                correo_padre = request.form.get('correo_padre', '').strip(),
                notif_correo = request.form.get('notif_correo',
                accesos = repo_accesos.ultimos_de_alumno(alumno_id, 1))
                )
            
            flash('Datos actualizados ✓')

        elif accion == 'password':
            actual  = request.form.get('password_actual', '')
            nueva   = request.form.get('password_nueva', '')
            repetir = request.form.get('password_repetir', '')

            alumno    = repo_alumnos.obtener_por_id(alumno_id)
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
@alumno_bp.route('/accesos')
def mis_accesos():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    return render_template('mis_accesos.html',
                           nombre  = session['nombre'],
                           accesos = repo_accesos.ultimos_de_alumno(session['alumno_id'], 50))