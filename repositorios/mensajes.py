"""
Repositorio de mensajes.

Chat privado entre el tutor de un alumno y la maestra.
"""

from repositorios.base import conexion, a_lista, ahora


# ═══════════ LECTURA ═══════════

def conversacion(id_alumno):
    """Todos los mensajes de un alumno, del más viejo al más nuevo."""
    with conexion() as conn:
        filas = conn.execute('''
            SELECT * FROM mensajes
            WHERE id_alumno = ?
            ORDER BY fecha ASC
        ''', (id_alumno,)).fetchall()
    return a_lista(filas)


def conversaciones(solo_con_mensajes=False):
    """
    Lista de alumnos con el resumen de su conversación.
    Si `solo_con_mensajes` es False, incluye a los alumnos con quienes
    todavía no hay ningún mensaje, para que la maestra pueda iniciar el chat.
    """
    union = 'INNER JOIN' if solo_con_mensajes else 'LEFT JOIN'

    with conexion() as conn:
        filas = conn.execute(f'''
            SELECT a.id, a.nombre, a.curp,
                   MAX(m.fecha) AS ultima_fecha,
                   (SELECT contenido FROM mensajes
                    WHERE id_alumno = a.id
                    ORDER BY fecha DESC LIMIT 1) AS ultimo_mensaje,
                   (SELECT remitente FROM mensajes
                    WHERE id_alumno = a.id
                    ORDER BY fecha DESC LIMIT 1) AS ultimo_remitente,
                   SUM(CASE WHEN m.remitente = 'padre' AND m.visto = 0
                            THEN 1 ELSE 0 END) AS no_leidos,
                   COUNT(m.id) AS total_mensajes
            FROM alumnos a
            {union} mensajes m ON m.id_alumno = a.id
            GROUP BY a.id
            ORDER BY (MAX(m.fecha) IS NULL), MAX(m.fecha) DESC, a.nombre
        ''').fetchall()
    return a_lista(filas)


def contar_no_leidos_maestra():
    """Mensajes de padres que la maestra no ha leído."""
    with conexion() as conn:
        return conn.execute('''
            SELECT COUNT(*) AS n FROM mensajes
            WHERE remitente = 'padre' AND visto = 0
        ''').fetchone()['n']


def contar_no_leidos_padre(id_alumno):
    """Mensajes de la maestra que ese padre no ha leído."""
    with conexion() as conn:
        return conn.execute('''
            SELECT COUNT(*) AS n FROM mensajes
            WHERE id_alumno = ? AND remitente = 'maestra' AND visto = 0
        ''', (id_alumno,)).fetchone()['n']


# ═══════════ ESCRITURA ═══════════

def enviar(id_alumno, remitente, contenido,
           ref_tipo=None, ref_id=None, ref_titulo=None):
    """
    Guarda un mensaje.

    `remitente` es 'padre' o 'maestra'.
    Los campos `ref_*` son opcionales y sirven para dejar claro sobre
    qué publicación está preguntando. El título se guarda tal cual para
    que el mensaje conserve el contexto aunque después se edite o borre
    la publicación original.
    """
    with conexion() as conn:
        cur = conn.execute('''
            INSERT INTO mensajes
                (id_alumno, remitente, contenido, fecha,
                 ref_tipo, ref_id, ref_titulo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (id_alumno, remitente, contenido, ahora(),
              ref_tipo, ref_id, ref_titulo))
        return cur.lastrowid

def marcar_vistos(id_alumno, remitente):
    """
    Marca como leídos los mensajes de un remitente.
    La maestra marca los del padre; el padre marca los de la maestra.
    """
    with conexion() as conn:
        conn.execute('''
            UPDATE mensajes SET visto = 1, fecha_visto = ?
            WHERE id_alumno = ? AND remitente = ? AND visto = 0
        ''', (ahora(), id_alumno, remitente))
