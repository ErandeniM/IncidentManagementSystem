"""
Repositorio de alumnos.

Todo el SQL de la tabla `alumnos` vive aquí. Ninguna ruta debe
escribir consultas sobre esta tabla directamente.
"""

from repositorios.base import conexion, a_dict, a_lista


# ═══════════ LECTURA ═══════════

def obtener_todos():
    """Lista de alumnos ordenada por nombre."""
    with conexion() as conn:
        filas = conn.execute(
            'SELECT id, nombre, curp FROM alumnos ORDER BY nombre'
        ).fetchall()
    return a_lista(filas)


def obtener_por_id(id_alumno):
    """Un alumno completo, o None si no existe."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT * FROM alumnos WHERE id = ?', (id_alumno,)
        ).fetchone()
    return a_dict(fila)


def obtener_por_curp(curp):
    """Busca por CURP. Se usa al iniciar sesión."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT * FROM alumnos WHERE curp = ?', (curp,)
        ).fetchone()
    return a_dict(fila)


def contar():
    """Cuántos alumnos hay registrados."""
    with conexion() as conn:
        return conn.execute('SELECT COUNT(*) AS n FROM alumnos').fetchone()['n']


# ═══════════ ESCRITURA ═══════════

def crear(curp, nombre, password_hash, correo_padre=''):
    """
    Registra un alumno nuevo.
    Devuelve el id creado, o None si el CURP ya existía.
    """
    try:
        with conexion() as conn:
            cur = conn.execute('''
                INSERT INTO alumnos (curp, nombre, password_hash, correo_padre)
                VALUES (?, ?, ?, ?)
            ''', (curp, nombre, password_hash, correo_padre))
            return cur.lastrowid
    except Exception:
        return None


def actualizar_password(id_alumno, password_hash):
    """Cambia la contraseña de un alumno."""
    with conexion() as conn:
        conn.execute(
            'UPDATE alumnos SET password_hash = ? WHERE id = ?',
            (password_hash, id_alumno)
        )


def actualizar_datos_tutor(id_alumno, nombre_tutor, correo_padre, notif_correo):
    """
    Actualiza los datos de contacto del padre.
    Si un campo llega vacío, conserva el valor anterior.
    """
    with conexion() as conn:
        actual = conn.execute(
            'SELECT nombre_tutor, correo_padre FROM alumnos WHERE id = ?',
            (id_alumno,)
        ).fetchone()

        conn.execute('''
            UPDATE alumnos
            SET nombre_tutor = ?, correo_padre = ?, notif_correo = ?
            WHERE id = ?
        ''', (
            nombre_tutor or (actual['nombre_tutor'] if actual else None),
            correo_padre or (actual['correo_padre'] if actual else None),
            1 if notif_correo else 0,
            id_alumno
        ))


# ═══════════ NOTIFICACIONES ═══════════

def nombre_del_tutor(id_alumno):
    """Nombre del tutor, o None si no lo ha registrado."""
    with conexion() as conn:
        fila = conn.execute(
            'SELECT nombre_tutor FROM alumnos WHERE id = ?', (id_alumno,)
        ).fetchone()
    return fila['nombre_tutor'] if fila else None


def correo_para_notificar(id_alumno):
    """
    Correo del padre, solo si tiene las notificaciones activadas.
    Devuelve lista vacía si no debe recibir nada.
    """
    with conexion() as conn:
        fila = conn.execute(
            'SELECT correo_padre, notif_correo FROM alumnos WHERE id = ?',
            (id_alumno,)
        ).fetchone()

    if fila and fila['correo_padre'] and fila['notif_correo']:
        return [fila['correo_padre']]
    return []


def correos_para_notificar():
    """Correos de todos los padres con notificaciones activadas."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT correo_padre FROM alumnos
            WHERE correo_padre IS NOT NULL
              AND correo_padre != ''
              AND notif_correo = 1
        ''').fetchall()
    return [f['correo_padre'] for f in filas]

def crear(curp, nombre, password_hash, correo_padre='', nombre_tutor=''):
    """
    Registra un alumno nuevo.
    Devuelve el id creado, o None si el CURP ya existía.
    """
    try:
        with conexion() as conn:
            cur = conn.execute('''
                INSERT INTO alumnos (curp, nombre, password_hash, correo_padre, nombre_tutor)
                VALUES (?, ?, ?, ?, ?)
            ''', (curp, nombre, password_hash, correo_padre, nombre_tutor))
            return cur.lastrowid
    except Exception:
        return None