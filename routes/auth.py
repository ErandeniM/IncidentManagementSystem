from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db, hash_password, verificar_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
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
            # Migra el hash viejo al formato seguro
            if actualizar:
                conn.execute(
                    'UPDATE alumnos SET password_hash = ? WHERE id = ?',
                    (hash_password(password), alumno['id'])
                )

            # Registro de acceso
            conn.execute(
                'INSERT INTO registro_accesos (id_alumno, ip) VALUES (?, ?)',
                (alumno['id'], request.remote_addr)
            )
            conn.commit()
            conn.close()

            session['alumno_id'] = alumno['id']
            session['nombre']    = alumno['nombre']
            return redirect(url_for('alumno.panel_alumno'))

        conn.close()
        flash('CURP o contraseña incorrectos')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
