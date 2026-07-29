from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import hash_password, verificar_password
from repositorios import alumnos as repo_alumnos
from repositorios import accesos as repo_accesos
from seguridad import esta_bloqueado, registrar_fallo, limpiar

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr

        bloqueado, minutos = esta_bloqueado(ip, 'padre')
        if bloqueado:
            flash(f'Demasiados intentos. Vuelve a intentar en {minutos} minuto(s).')
            return render_template('login.html')

        curp     = request.form['curp'].strip().upper()
        password = request.form['password']
        alumno   = repo_alumnos.obtener_por_curp(curp)

        valida, actualizar = (False, False)
        if alumno:
            valida, actualizar = verificar_password(password, alumno['password_hash'])

        if valida:
            if actualizar:
                repo_alumnos.actualizar_password(alumno['id'], hash_password(password))

            repo_accesos.registrar(alumno['id'], ip)
            limpiar(ip, 'padre')

            session['alumno_id'] = alumno['id']
            session['nombre']    = alumno['nombre']
            return redirect(url_for('alumno.panel_alumno'))

        registrar_fallo(ip, 'padre', maximo=5 if alumno else 10)
        flash('CURP o contraseña incorrectos')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))