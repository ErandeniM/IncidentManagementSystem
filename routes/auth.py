from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db, hash_password, verificar_password
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

        conn   = get_db()
        alumno = conn.execute(
            'SELECT * FROM alumnos WHERE curp = ?', (curp,)
        ).fetchone()

        valida, actualizar = (False, False)
        if alumno:
            valida, actualizar = verificar_password(password, alumno['password_hash'])

        if valida:
            if actualizar:
                conn.execute(
                    'UPDATE alumnos SET password_hash = ? WHERE id = ?',
                    (hash_password(password), alumno['id'])
                )

            conn.execute(
                'INSERT INTO registro_accesos (id_alumno, ip) VALUES (?, ?)',
                (alumno['id'], ip)
            )
            conn.commit()
            conn.close()

            limpiar(ip, 'padre')
            session['alumno_id'] = alumno['id']
            session['nombre']    = alumno['nombre']
            return redirect(url_for('alumno.panel_alumno'))

        conn.close()

        # CURP inexistente = error de dedo, más tolerancia.
        # CURP válida con contraseña mal = posible ataque, menos tolerancia.
        registrar_fallo(ip, 'padre', maximo=5 if alumno else 10)
        flash('CURP o contraseña incorrectos')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
