"""
Rutas del portal de padres.

Ninguna función de este archivo escribe SQL: todo el acceso a datos
pasa por la capa de repositorios.
"""

from datetime import date

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
from repositorios import busqueda as repo_busqueda

alumno_bp = Blueprint('alumno', __name__)


def _sesion_activa():
    return 'alumno_id' in session


def _es_logro(incidencia):
    return incidencia['tipo'] in ('logro', 'Logro')


# ═══════════════════════════════════════════════════════════
#  INICIO
# ═══════════════════════════════════════════════════════════

@alumno_bp.route('/panel')
def panel_alumno():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id   = session['alumno_id']
    incidencias = repo_incidencias.de_alumno(alumno_id)

    # ── Bandeja: incidencias, avisos generales y lo que mandó el tutor ──
    avisos_feed = []

    for inc in incidencias:
        if _es_logro(inc):
            continue
        t = repo_incidencias.TIPOS_MAP.get(inc['tipo'], {})
        avisos_feed.append({
            'clase':    'incidencia',
            'id':       inc['id'],
            'titulo':   (inc['descripcion'] or '')[:44],
            'icono':    t.get('icono', 'ti-alert-triangle'),
            'fecha':    (inc['fecha'] or '')[:10],
            'atendido': bool(inc['enterado']),
            'orden':    inc['fecha'] or '',
        })

    for av in repo_avisos.activos_para(alumno_id):
        avisos_feed.append({
            'clase':    'general',
            'id':       av['id'],
            'titulo':   av['titulo'],
            'fecha':    (av['fecha'] or '')[:10],
            'atendido': bool(av['confirmado_por_padre']),
            'orden':    av['fecha'] or '',
        })

    for ap in repo_avisos.de_padre(alumno_id):
        avisos_feed.append({
            'clase':    'enviado',
            'id':       ap['id'],
            'titulo':   repo_avisos.etiqueta_tipo_padre(ap['tipo']),
            'fecha':    (ap['fecha_creado'] or '')[:10],
            'atendido': bool(ap['visto_maestra']),
            'orden':    ap['fecha_creado'] or '',
        })

    # Primero lo que falta atender; dentro de cada grupo, lo más reciente
    avisos_feed.sort(key=lambda a: a['orden'], reverse=True)
    avisos_feed.sort(key=lambda a: a['atendido'])

    logros      = [i for i in incidencias if _es_logro(i)]
    actividades = repo_academico.actividades_de(alumno_id)

    return render_template('alumno.html',
        nombre           = session['nombre'],
        avisos_feed      = avisos_feed,
        tareas           = repo_tareas.de_alumno(alumno_id),
        estados_map      = repo_tareas.ESTADOS_MAP,
        ultimo_logro     = logros[0] if logros else None,
        ultima_actividad = actividades[0] if actividades else None,
        promedio         = repo_academico.promedio_general(alumno_id))


# ═══════════════════════════════════════════════════════════
#  SECCIONES DEL MENÚ
# ═══════════════════════════════════════════════════════════

@alumno_bp.route('/avisos')
def avisos():
    """Bandeja completa: incidencias, avisos generales y los enviados."""
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    filtro    = request.args.get('filtro', 'todo')

    incidencias = [i for i in repo_incidencias.de_alumno(alumno_id)
                   if not _es_logro(i)]
    generales   = repo_avisos.activos_para(alumno_id)
    enviados    = repo_avisos.de_padre(alumno_id)

    if filtro == 'incidencias':
        generales, enviados = [], []
    elif filtro == 'generales':
        incidencias, enviados = [], []
    elif filtro == 'enviados':
        incidencias, generales = [], []

    return render_template('padre_avisos.html',
        nombre      = session['nombre'],
        incidencias = incidencias,
        generales   = generales,
        enviados    = enviados,
        filtro      = filtro,
        tipos_map   = repo_incidencias.TIPOS_MAP)


@alumno_bp.route('/tareas')
def tareas():
    """Historial de tareas con su estado de cumplimiento."""
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    return render_template('padre_tareas.html',
        nombre      = session['nombre'],
        tareas      = repo_tareas.de_alumno(alumno_id),
        resumen     = repo_tareas.resumen_alumno(alumno_id),
        estados_map = repo_tareas.ESTADOS_MAP)


@alumno_bp.route('/como-vamos')
def como_vamos():
    """Logros, calificaciones, perfil y actividades sugeridas."""
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']
    logros    = [i for i in repo_incidencias.de_alumno(alumno_id)
                 if _es_logro(i)]

    return render_template('padre_como_vamos.html',
        nombre         = session['nombre'],
        alumno         = repo_alumnos.obtener_por_id(alumno_id),
        logros         = logros,
        calificaciones = repo_academico.calificaciones_de(alumno_id),
        perfil         = repo_academico.perfil_de(alumno_id),
        actividades    = repo_academico.actividades_de(alumno_id),
        promedio       = repo_academico.promedio_general(alumno_id),
        tareas         = repo_tareas.resumen_alumno(alumno_id),
        materias       = repo_academico.MATERIAS,
        areas          = repo_academico.AREAS)


# ═══════════════════════════════════════════════════════════
#  DETALLE Y FIRMA
# ═══════════════════════════════════════════════════════════

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
                           nombre      = session['nombre'],
                           inc         = inc,
                           tipos_map   = repo_incidencias.TIPOS_MAP,
                           niveles_map = repo_incidencias.NIVELES_MAP,
                           declaracion = repo_incidencias.TEXTO_DECLARACION,
                           minimo      = repo_incidencias.MINIMO_RESPUESTA)


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
            firmado_por   = tutor or f'Tutor de {session["nombre"]}',
            declaracion   = repo_incidencias.TEXTO_DECLARACION
        )
        flash('Firma y respuesta registradas ✓')

    return redirect(url_for('alumno.avisos'))


@alumno_bp.route('/aviso/confirmar/<int:id_aviso>', methods=['POST'])
def confirmar_aviso(id_aviso):
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    repo_avisos.confirmar(id_aviso, session['alumno_id'])
    flash('Aviso confirmado ✓')
    return redirect(request.referrer or url_for('alumno.panel_alumno'))


# ═══════════════════════════════════════════════════════════
#  CHAT
# ═══════════════════════════════════════════════════════════

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
                           nombre     = session['nombre'],
                           mensajes   = repo_mensajes.conversacion(alumno_id),
                           ref_tipo   = request.args.get('ref_tipo'),
                           ref_id     = request.args.get('ref_id'),
                           ref_titulo = request.args.get('ref_titulo'))


# ═══════════════════════════════════════════════════════════
#  AVISOS RÁPIDOS
# ═══════════════════════════════════════════════════════════

@alumno_bp.route('/avisar', methods=['GET', 'POST'])
def avisar_maestra():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    alumno_id = session['alumno_id']

    if request.method == 'POST':
        tipo         = request.form.get('tipo')
        fecha_aplica = request.form.get('fecha_aplica') or None

        if not tipo:
            flash('Selecciona un tipo de aviso')
            return redirect(url_for('alumno.avisar_maestra'))

        if fecha_aplica:
            try:
                if date.fromisoformat(fecha_aplica) < date.today():
                    flash('No puedes avisar sobre una fecha que ya pasó')
                    return redirect(url_for('alumno.avisar_maestra'))
            except ValueError:
                flash('La fecha no es válida')
                return redirect(url_for('alumno.avisar_maestra'))

        repo_avisos.crear_de_padre(
            id_alumno    = alumno_id,
            tipo         = tipo,
            detalle      = request.form.get('detalle', '').strip(),
            fecha_aplica = fecha_aplica,
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


# ═══════════════════════════════════════════════════════════
#  CUENTA
# ═══════════════════════════════════════════════════════════

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
                notif_correo = request.form.get('notif_correo')
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
                           accesos = repo_accesos.ultimos_de_alumno(alumno_id, 1))


@alumno_bp.route('/accesos')
def mis_accesos():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    return render_template('mis_accesos.html',
                           nombre  = session['nombre'],
                           accesos = repo_accesos.ultimos_de_alumno(session['alumno_id'], 50))


# ═══════════════════════════════════════════════════════════
#  BÚSQUEDA
# ═══════════════════════════════════════════════════════════

@alumno_bp.route('/buscar')
def buscar():
    if not _sesion_activa():
        return redirect(url_for('auth.login'))

    consulta = request.args.get('q', '').strip()
    return render_template('buscar_padre.html',
                           nombre      = session['nombre'],
                           consulta    = consulta,
                           r           = repo_busqueda.buscar_del_padre(session['alumno_id'], consulta),
                           tipos_map   = repo_incidencias.TIPOS_MAP,
                           estados_map = repo_tareas.ESTADOS_MAP)
