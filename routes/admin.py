"""
Rutas del panel de la maestra.

Ninguna función de este archivo escribe SQL: todo el acceso a datos
pasa por la capa de repositorios.
"""

import csv
import io
import random
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, make_response)
from werkzeug.security import check_password_hash

from config import ADMIN_PASSWORD_HASH, DOCENTE_NOMBRE
from database import hash_password
from seguridad import esta_bloqueado, registrar_fallo, limpiar
from documentos import acta_incidencia, expediente_completo
import notificaciones

from repositorios import alumnos as repo_alumnos
from repositorios import accesos as repo_accesos
from repositorios import incidencias as repo_incidencias
from repositorios import avisos as repo_avisos
from repositorios import mensajes as repo_mensajes
from repositorios import academico as repo_academico
from repositorios import tareas as repo_tareas
from repositorios import busqueda as repo_busqueda
from zoneinfo import ZoneInfo

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _es_admin():
    return session.get('admin')


# ═══════════ ACCESO ═══════════

@admin_bp.route('', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        ip = request.remote_addr

        bloqueado, minutos = esta_bloqueado(ip, 'admin')
        if bloqueado:
            flash(f'Demasiados intentos. Vuelve a intentar en {minutos} minuto(s).')
            return render_template('admin_login.html')

        if check_password_hash(ADMIN_PASSWORD_HASH, request.form.get('password', '')):
            limpiar(ip, 'admin')
            session['admin'] = True
            return redirect(url_for('admin.admin_dashboard'))

        registrar_fallo(ip, 'admin', maximo=5)
        flash('Contraseña incorrecta')

    return render_template('admin_login.html')


@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin.admin_panel'))


# ═══════════ DASHBOARD ═══════════

def _trimestre_actual():
    """Trimestre según el mes, para el ciclo escolar mexicano."""
    mes = datetime.now(ZoneInfo('America/Hermosillo')).month
    if mes in (9, 10, 11):
        return 1
    if mes in (12, 1, 2, 3):
        return 2
    return 3


@admin_bp.route('/dashboard')
def admin_dashboard():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    trimestre = _trimestre_actual()
    tabla     = repo_academico.tabla_trimestre(trimestre)
    resumen   = repo_academico.resumen_trimestre(tabla)

    tareas      = repo_tareas.todas()
    por_revisar = sum((t['total_alumnos'] or 0) - t['revisados'] for t in tareas)

    # La tarea con más entregas sin marcar, para dar contexto
    tarea_pendiente = None
    for t in tareas:
        if (t['total_alumnos'] or 0) - t['revisados'] > 0:
            tarea_pendiente = t['titulo']
            break

    materias_incompletas = sum(
        1 for campo, _ in repo_academico.MATERIAS
        if resumen['por_materia'][campo] is None
    )

    # La incidencia sin firmar más antigua, para saber qué tan urgente es
    pendientes = repo_incidencias.todas('pendientes')
    mas_vieja  = pendientes[-1]['fecha'][:10] if pendientes else None

    # Quiénes escribieron sin respuesta
    conversaciones = repo_mensajes.conversaciones()
    con_mensajes   = [c['nombre'] for c in conversaciones if c['no_leidos']]

    return render_template('admin_dashboard.html',
        alumnos                = repo_alumnos.obtener_todos(),
        mensajes_pendientes    = repo_mensajes.contar_no_leidos_maestra(),
        avisos_pendientes      = repo_avisos.contar_pendientes_de_padres(),
        incidencias_sin_firmar = repo_incidencias.contar_sin_firmar(),
        incidencia_mas_vieja   = mas_vieja,
        quien_escribio         = ', '.join(con_mensajes[:3]),
        total_incidencias      = len(repo_incidencias.todas()),
        total_tareas           = len(tareas),
        trimestre              = trimestre,
        resumen                = resumen,
        materias               = repo_academico.MATERIAS,
        conversaciones         = conversaciones[:5],
        avisos_recientes       = repo_avisos.todos(),
        tareas_por_revisar     = por_revisar,
        tarea_pendiente        = tarea_pendiente,
        materias_incompletas   = materias_incompletas,
        tipos                  = repo_incidencias.TIPOS,
        niveles                = repo_incidencias.NIVELES)

@admin_bp.route('/buscar')
def admin_buscar():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    consulta = request.args.get('q', '').strip()
    return render_template('admin_buscar.html',
                           consulta  = consulta,
                           r         = repo_busqueda.buscar(consulta),
                           tipos_map = repo_incidencias.TIPOS_MAP)


# ═══════════ ALUMNOS ═══════════

@admin_bp.route('/alumnos')
def admin_alumnos():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))
    return render_template('admin_alumnos.html',
                           alumnos = repo_alumnos.obtener_todos())


@admin_bp.route('/nuevo_alumno', methods=['POST'])
def nuevo_alumno():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    nombre = request.form['nombre'].strip()

    creado = repo_alumnos.crear(
        curp          = request.form['curp'].strip().upper(),
        nombre        = nombre,
        password_hash = hash_password(request.form['password']),
        correo_padre  = request.form.get('correo_padre', '').strip(),
        nombre_tutor  = request.form.get('nombre_tutor', '').strip()
    )
    

    flash(f'Alumno {nombre} registrado correctamente ✓' if creado
          else 'Error: ese CURP ya existe')
    return redirect(url_for('admin.admin_alumnos'))


@admin_bp.route('/alumno/<int:id_alumno>/password', methods=['POST'])
def resetear_password(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    nueva = request.form.get('password_nueva', '').strip()
    if len(nueva) < 6:
        flash('La contraseña debe tener al menos 6 caracteres')
        return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))

    repo_alumnos.actualizar_password(id_alumno, hash_password(nueva))
    alumno = repo_alumnos.obtener_por_id(id_alumno)

    flash(f'Contraseña de {alumno["nombre"]} restablecida. '
          f'Nueva contraseña: {nueva} ✓')
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


@admin_bp.route('/accesos')
def admin_accesos():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))
    return render_template('admin_accesos.html', accesos=repo_accesos.todos())


# ═══════════ EXPEDIENTE ═══════════

@admin_bp.route('/alumno/<int:id_alumno>')
def admin_expediente(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    return render_template('admin_expediente.html',
        alumno         = repo_alumnos.obtener_por_id(id_alumno),
        incidencias    = repo_incidencias.de_alumno(id_alumno),
        calificaciones = repo_academico.calificaciones_de(id_alumno),
        perfil         = repo_academico.perfil_de(id_alumno),
        actividades    = repo_academico.actividades_de(id_alumno, pendientes_primero=True),
        id_alumno      = id_alumno,
        tipos          = repo_incidencias.TIPOS,
        niveles        = repo_incidencias.NIVELES,
        tipos_map      = repo_incidencias.TIPOS_MAP,
        niveles_map    = repo_incidencias.NIVELES_MAP)


@admin_bp.route('/alumno/<int:id_alumno>/pdf')
def expediente_pdf(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    alumno = repo_alumnos.obtener_por_id(id_alumno)
    if not alumno:
        flash('No se encontró el alumno')
        return redirect(url_for('admin.admin_alumnos'))

    pdf = expediente_completo(
        alumno         = alumno,
        incidencias    = repo_incidencias.de_alumno(id_alumno, mas_recientes_primero=False),
        calificaciones = repo_academico.calificaciones_de(id_alumno),
        perfil         = repo_academico.perfil_de(id_alumno)
    )

    respuesta = make_response(pdf)
    respuesta.headers['Content-Type'] = 'application/pdf'
    respuesta.headers['Content-Disposition'] = \
        f'attachment; filename=expediente_{alumno["curp"]}.pdf'
    return respuesta


# ═══════════ INCIDENCIAS ═══════════

@admin_bp.route('/nueva_incidencia/<int:id_alumno>', methods=['POST'])
def nueva_incidencia(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    tipo = request.form['tipo']

    repo_incidencias.crear(
        id_alumno      = id_alumno,
        tipo           = tipo,
        descripcion    = request.form['descripcion'].strip(),
        accion_docente = request.form.get('accion_docente', '').strip(),
        nivel          = request.form.get('nivel', 'informativo')
    )

    alumno = repo_alumnos.obtener_por_id(id_alumno)
    notificaciones.avisar_a_padre(
        id_alumno = id_alumno,
        asunto    = f'Nueva notificación — {alumno["nombre"]}',
        titulo    = 'Nueva notificación escolar',
        mensaje   = (f'Se registró una notificación de tipo '
                     f'<b>{repo_incidencias.etiqueta_tipo(tipo)}</b> para '
                     f'<b>{alumno["nombre"]}</b>. Ingresa al portal para leer '
                     f'el detalle y registrar tu firma de enterado.'),
        tipo      = 'logro' if tipo == 'logro' else 'incidencia'
    )

    flash('Incidencia registrada ✓')
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno))


@admin_bp.route('/incidencias')
def admin_todas_incidencias():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    filtro = request.args.get('filtro', 'todo')
    return render_template('admin_todas_incidencias.html',
                           incidencias = repo_incidencias.todas(filtro),
                           filtro      = filtro,
                           alumnos     = repo_alumnos.obtener_todos(),
                           tipos       = repo_incidencias.TIPOS,
                           niveles     = repo_incidencias.NIVELES,
                           tipos_map   = repo_incidencias.TIPOS_MAP,
                           niveles_map = repo_incidencias.NIVELES_MAP)
    
@admin_bp.route('/incidencia/<int:id_incidencia>/acta')
def acta_pdf(id_incidencia):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    inc = repo_incidencias.obtener(id_incidencia)
    if not inc:
        flash('No se encontró la incidencia')
        return redirect(url_for('admin.admin_dashboard'))

    alumno     = repo_alumnos.obtener_por_id(inc['id_alumno'])
    pdf, folio = acta_incidencia(inc, alumno)

    respuesta = make_response(pdf)
    respuesta.headers['Content-Type'] = 'application/pdf'
    respuesta.headers['Content-Disposition'] = f'inline; filename=acta_{folio}.pdf'
    return respuesta


# ═══════════ PERFIL Y ACTIVIDADES ═══════════

@admin_bp.route('/guardar_perfil/<int:id_alumno>', methods=['POST'])
def guardar_perfil(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    repo_academico.guardar_perfil(
        id_alumno = id_alumno,
        valores   = {campo: request.form.get(campo, 0)
                     for campo, _ in repo_academico.AREAS},
        nota      = request.form.get('nota', '').strip()
    )
    flash('Perfil actualizado ✓')
    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno) + '#tab-perfil')


@admin_bp.route('/nueva_actividad/<int:id_alumno>', methods=['POST'])
def nueva_actividad(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    actividad = request.form['actividad'].strip()
    categoria = request.form.get('categoria', 'General')

    if request.form.get('todo_el_grupo'):
        n = repo_academico.crear_actividad_para_todos(actividad, categoria)
        flash(f'Actividad asignada a {n} alumno(s) ✓')
    else:
        repo_academico.crear_actividad(id_alumno, actividad, categoria)
        flash('Actividad agregada ✓')

    return redirect(url_for('admin.admin_expediente', id_alumno=id_alumno) + '#tab-actividades')


# ═══════════ CALIFICACIONES ═══════════

@admin_bp.route('/calificaciones')
def admin_calificaciones():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    trimestre = request.args.get('trimestre', 1, type=int)
    if trimestre not in (1, 2, 3):
        trimestre = 1

    alumnos = repo_academico.tabla_trimestre(trimestre)
    resumen = repo_academico.resumen_trimestre(alumnos)

    return render_template('admin_calificaciones.html',
                           alumnos      = alumnos,
                           trimestre    = trimestre,
                           materias     = repo_academico.MATERIAS,
                           completos    = resumen['completos'],
                           total        = resumen['total'],
                           avance       = resumen['avance'],
                           prom_materia = resumen['por_materia'],
                           prom_grupo   = resumen['promedio'])


@admin_bp.route('/calificaciones/guardar', methods=['POST'])
def guardar_calificaciones():
    if not _es_admin():
        return jsonify({'ok': False}), 403

    d = request.get_json()

    def num(v):
        try:
            return float(v) if v not in (None, '') else None
        except (ValueError, TypeError):
            return None

    notas = {campo: num(d.get(campo)) for campo, _ in repo_academico.MATERIAS}

    repo_academico.guardar_calificaciones(
        id_alumno     = d.get('id_alumno'),
        trimestre     = d.get('trimestre'),
        notas         = notas,
        inasistencias = int(d.get('inasistencias') or 0),
        observaciones = (d.get('observaciones') or '').strip()
    )

    llenas = [n for n in notas.values() if n is not None]
    return jsonify({
        'ok':       True,
        'completo': len(llenas) == len(repo_academico.MATERIAS),
        'promedio': round(sum(llenas) / len(llenas), 1) if llenas else None
    })


# ═══════════ AVISOS ═══════════

@admin_bp.route('/avisos')
def admin_avisos():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))
    return render_template('admin_avisos.html', avisos=repo_avisos.todos())


@admin_bp.route('/nuevo_aviso', methods=['POST'])
def nuevo_aviso():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    titulo    = request.form['titulo'].strip()
    contenido = request.form['contenido'].strip()

    repo_avisos.crear(titulo, contenido)
    notificaciones.avisar_a_todos(
        asunto  = f'Aviso escolar — {titulo}',
        titulo  = titulo,
        mensaje = contenido,
        tipo    = 'aviso'
    )

    flash('Aviso publicado ✓')
    return redirect(url_for('admin.admin_avisos'))


@admin_bp.route('/aviso/editar/<int:id_aviso>', methods=['POST'])
def editar_aviso(id_aviso):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    titulo    = request.form['titulo'].strip()
    contenido = request.form['contenido'].strip()

    repo_avisos.editar(id_aviso, titulo, contenido)
    notificaciones.avisar_a_todos(
        asunto  = f'Aviso actualizado — {titulo}',
        titulo  = f'Aviso actualizado: {titulo}',
        mensaje = f'{contenido}<br><br><i>Este aviso fue modificado, '
                  f'por eso te pedimos confirmarlo de nuevo.</i>',
        tipo    = 'aviso'
    )

    flash('Aviso actualizado. Los padres deberán confirmar nuevamente.')
    return redirect(url_for('admin.admin_avisos'))


@admin_bp.route('/aviso/eliminar/<int:id_aviso>', methods=['POST'])
def eliminar_aviso(id_aviso):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    repo_avisos.eliminar(id_aviso)
    flash('Aviso eliminado')
    return redirect(url_for('admin.admin_avisos'))


@admin_bp.route('/aviso/confirmaciones/<int:id_aviso>')
def ver_confirmaciones(id_aviso):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    return render_template('admin_confirmaciones.html',
                           aviso       = repo_avisos.obtener(id_aviso),
                           confirmados = repo_avisos.quien_confirmo(id_aviso),
                           pendientes  = repo_avisos.quien_falta(id_aviso))

@admin_bp.route('/avisos-padres')
def admin_avisos_padres():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    return render_template('admin_avisos_padres.html',
                           avisos = repo_avisos.todos_de_padres())


@admin_bp.route('/aviso-padre/<int:id_aviso>/acusar', methods=['POST'])
def acusar_aviso_padre(id_aviso):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    repo_avisos.acusar_de_padre(id_aviso, DOCENTE_NOMBRE)
    flash('Aviso marcado como leído ✓')
    return redirect(url_for('admin.admin_avisos_padres'))


@admin_bp.route('/aviso/restaurar/<int:id_aviso>', methods=['POST'])
def restaurar_aviso(id_aviso):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    repo_avisos.restaurar(id_aviso)
    flash('Aviso restaurado ✓')
    return redirect(url_for('admin.admin_comunicacion') + '?hoja=avisos')
# ═══════════ MENSAJES ═══════════

@admin_bp.route('/mensajes')
def admin_mensajes():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))
    return render_template('admin_mensajes.html',
                           conversaciones = repo_mensajes.conversaciones())


@admin_bp.route('/mensajes/<int:id_alumno>', methods=['GET', 'POST'])
def admin_chat(id_alumno):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()
        if contenido:
            repo_mensajes.enviar(id_alumno, 'maestra', contenido)
            notificaciones.avisar_a_padre(
                id_alumno = id_alumno,
                asunto    = 'Nuevo mensaje de la maestra',
                titulo    = 'Tienes un mensaje nuevo',
                mensaje   = 'La maestra te respondió en el chat privado. '
                            'Ingresa al portal para leerlo.',
                tipo      = 'mensaje'
            )
        return redirect(url_for('admin.admin_chat', id_alumno=id_alumno))

    repo_mensajes.marcar_vistos(id_alumno, 'padre')

    return render_template('admin_chat.html',
                           alumno   = repo_alumnos.obtener_por_id(id_alumno),
                           mensajes = repo_mensajes.conversacion(id_alumno))


# ═══════════ TAREAS DE ENTREGA ═══════════

@admin_bp.route('/tareas')
def admin_tareas():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))
    return render_template('admin_tareas.html',
                           tareas   = repo_tareas.todas(),
                           materias = repo_tareas.MATERIAS)


@admin_bp.route('/tareas/nueva', methods=['POST'])
def nueva_tarea():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    titulo  = request.form['titulo'].strip()
    entrega = request.form.get('fecha_entrega') or None

    repo_tareas.crear(
        titulo        = titulo,
        descripcion   = request.form.get('descripcion', '').strip(),
        materia       = request.form.get('materia', 'General'),
        fecha_entrega = entrega
    )

    notificaciones.avisar_a_todos(
        asunto  = f'Nueva tarea — {titulo}',
        titulo  = titulo,
        mensaje = (request.form.get('descripcion', '').strip() or 'Nueva tarea publicada.')
                  + (f'<br><br><b>Fecha de entrega:</b> {entrega}' if entrega else ''),
        tipo    = 'tarea'
    )

    flash('Tarea publicada ✓')
    return redirect(url_for('admin.admin_tareas'))


@admin_bp.route('/tareas/<int:id_tarea>/editar', methods=['POST'])
def editar_tarea(id_tarea):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    repo_tareas.editar(
        id_tarea      = id_tarea,
        titulo        = request.form['titulo'].strip(),
        descripcion   = request.form.get('descripcion', '').strip(),
        materia       = request.form.get('materia', 'General'),
        fecha_entrega = request.form.get('fecha_entrega') or None
    )
    flash('Tarea actualizada ✓')
    return redirect(url_for('admin.admin_tareas'))


@admin_bp.route('/tareas/<int:id_tarea>/eliminar', methods=['POST'])
def eliminar_tarea(id_tarea):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    repo_tareas.eliminar(id_tarea)
    flash('Tarea eliminada')
    return redirect(url_for('admin.admin_tareas'))


@admin_bp.route('/tareas/<int:id_tarea>/revisar')
def revisar_tarea(id_tarea):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    tarea = repo_tareas.obtener(id_tarea)
    if not tarea:
        flash('No se encontró la tarea')
        return redirect(url_for('admin.admin_tareas'))

    return render_template('admin_tarea_revision.html',
                           tarea       = tarea,
                           alumnos     = repo_tareas.lista_revision(id_tarea),
                           estados     = repo_tareas.ESTADOS,
                           estados_map = repo_tareas.ESTADOS_MAP)


@admin_bp.route('/tareas/marcar', methods=['POST'])
def marcar_entrega():
    if not _es_admin():
        return jsonify({'ok': False}), 403

    d = request.get_json()
    repo_tareas.marcar(
        id_tarea  = d.get('id_tarea'),
        id_alumno = d.get('id_alumno'),
        estado    = d.get('estado'),
        nota      = (d.get('nota') or '').strip()
    )
    return jsonify({'ok': True})


@admin_bp.route('/tareas/<int:id_tarea>/marcar-todos', methods=['POST'])
def marcar_todos_entrega(id_tarea):
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    n = repo_tareas.marcar_todos(id_tarea, request.form.get('estado', 'cumplio'))
    flash(f'{n} alumno(s) marcados ✓')
    return redirect(url_for('admin.revisar_tarea', id_tarea=id_tarea))


# ═══════════ ALTA MASIVA POR CSV ═══════════

PALABRAS = ['casa', 'sol', 'luna', 'flor', 'mar', 'nube', 'arbol', 'rio', 'cielo', 'campo']


def generar_password():
    """Contraseña simple de dictar por teléfono. Ej: luna-4821"""
    return f'{random.choice(PALABRAS)}-{random.randint(1000, 9999)}'


@admin_bp.route('/alumnos/importar', methods=['GET', 'POST'])
def importar_alumnos():
    if not _es_admin():
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

        creados, errores = [], []

        for num, fila in enumerate(csv.DictReader(io.StringIO(contenido)), start=2):
            curp   = (fila.get('curp')   or '').strip().upper()
            nombre = (fila.get('nombre') or '').strip()
            correo = (fila.get('correo') or '').strip()
            tutor  = (fila.get('tutor')  or '').strip()
            passwd = (fila.get('contrasena') or '').strip() or generar_password()

            if not curp or not nombre:
                errores.append(f'Fila {num}: falta CURP o nombre')
                continue
            if len(curp) != 10:
                errores.append(f'Fila {num}: el CURP debe tener 10 caracteres ({curp})')
                continue

            if repo_alumnos.crear(curp, nombre, hash_password(passwd), correo, tutor):
                creados.append({'curp': curp, 'nombre': nombre, 'password': passwd})
            else:
                errores.append(f'Fila {num}: el CURP {curp} ya existe')

        resultados = {'creados': creados, 'errores': errores}

    return render_template('admin_importar.html', resultados=resultados)

@admin_bp.route('/alumnos/plantilla-csv')
def plantilla_csv():
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    salida   = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(['curp', 'nombre', 'correo', 'contrasena'])
    escritor.writerow(['MABC010101', 'María G.', 'mama.maria@gmail.com', ''])
    escritor.writerow(['LOPZ020202', 'Juan P.', 'papa.juan@gmail.com', ''])

    respuesta = make_response('\ufeff' + salida.getvalue())
    respuesta.headers['Content-Type'] = 'text/csv; charset=utf-8'
    respuesta.headers['Content-Disposition'] = 'attachment; filename=plantilla_alumnos.csv'
    
    return respuesta

@admin_bp.route('/comunicacion')
def admin_comunicacion():
    """Mensajes, avisos publicados y avisos de tutores, en pestañas."""
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    return render_template('admin_comunicacion.html',
        conversaciones = repo_mensajes.conversaciones(),
        avisos         = repo_avisos.todos(),
        avisos_padres  = repo_avisos.todos_de_padres(),
        hoja           = request.args.get('hoja', 'mensajes'))


@admin_bp.route('/ajustes')
def admin_ajustes():
    """Accesos al sistema y datos del grupo."""
    if not _es_admin():
        return redirect(url_for('admin.admin_panel'))

    return render_template('admin_ajustes.html',
        accesos = repo_accesos.todos(),
        alumnos = repo_alumnos.obtener_todos())