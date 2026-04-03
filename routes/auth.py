from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db, hash_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        curp     = request.form['curp'].strip().upper()
        password = request.form['password']
        conn     = get_db()
        alumno   = conn.execute(
            'SELECT * FROM alumnos WHERE curp = ?', (curp,)
        ).fetchone()
        conn.close()

        if alumno and alumno['password_hash'] == hash_password(password):
            session['alumno_id'] = alumno['id']
            session['nombre']    = alumno['nombre']
            conn2 = get_db()
            conn2.execute(
                'INSERT INTO registro_accesos (id_alumno, ip) VALUES (?, ?)',
                (alumno['id'], request.remote_addr)
            )
            conn2.commit()
            conn2.close()
            return redirect(url_for('alumno.panel_alumno'))
        flash('CURP o contraseña incorrectos')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
