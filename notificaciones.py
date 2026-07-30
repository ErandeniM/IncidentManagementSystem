"""
Notificaciones por correo.

Los correos se envían en segundo plano para que la página no se quede
esperando al servidor de correo. Si un padre desactivó los avisos en su
Configuración, no se le manda nada.
"""

import threading

from email_utils import enviar_correo
from database import get_db
from config import DOCENTE_NOMBRE, DOCENTE_CORREO, ESCUELA_NOMBRE, URL_BASE


# Colores del encabezado según el tipo de notificación
COLORES = {
    'incidencia': ('#ff9600', '#ff6b35'),
    'logro':      ('#89e219', '#58cc02'),
    'aviso':      ('#7dd3fc', '#1cb0f6'),
    'tarea':      ('#ffc107', '#e0a800'),
    'mensaje':    ('#7dd3fc', '#1cb0f6'),
}

ICONOS = {
    'incidencia': '📋',
    'logro':      '⭐',
    'aviso':      '📢',
    'tarea':      '💡',
    'mensaje':    '💬',
}


# ═══════════ PLANTILLA HTML ═══════════

def _plantilla(titulo, mensaje, tipo='aviso', texto_boton='Abrir el portal', url=None):
    c1, c2 = COLORES.get(tipo, COLORES['aviso'])
    icono  = ICONOS.get(tipo, '📢')
    enlace = url or URL_BASE

    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;background:#fefcf5;padding:20px;">
      <div style="background:linear-gradient(135deg,{c1},{c2});padding:24px;border-radius:18px 18px 0 0;text-align:center;">
        <div style="font-size:38px;line-height:1;">{icono}</div>
        <h2 style="color:#fff;margin:10px 0 0;font-size:20px;">{titulo}</h2>
      </div>

      <div style="background:#fff;padding:24px;border:1px solid #eee;border-top:none;border-radius:0 0 18px 18px;">
        <p style="color:#3c3c3c;font-size:15px;line-height:1.6;margin:0 0 20px;">{mensaje}</p>

        <div style="text-align:center;margin:24px 0;">
          <a href="{enlace}"
             style="display:inline-block;background:{c2};color:#fff;text-decoration:none;
                    padding:14px 28px;border-radius:12px;font-weight:bold;font-size:15px;">
            {texto_boton}
          </a>
        </div>

        <p style="color:#999;font-size:12px;line-height:1.5;margin:20px 0 0;border-top:1px solid #eee;padding-top:16px;">
          Mensaje automático de {ESCUELA_NOMBRE} — Maestra {DOCENTE_NOMBRE}.<br>
          Puedes desactivar estos avisos en tu Configuración dentro del portal.
        </p>
      </div>
    </div>
    """


# ═══════════ ENVÍO ═══════════

def _enviar_en_segundo_plano(destinatarios, asunto, html):
    """Manda los correos en un hilo aparte para no frenar la página."""
    def tarea():
        for correo in destinatarios:
            try:
                enviar_correo(correo, asunto, html)
            except Exception as e:
                print(f'[notificaciones] no se pudo enviar a {correo}: {e}')

    threading.Thread(target=tarea, daemon=True).start()


def _correo_de_alumno(id_alumno):
    """Correo del padre de un alumno, solo si tiene los avisos activados."""
    conn = get_db()
    fila = conn.execute(
        'SELECT correo_padre, notif_correo FROM alumnos WHERE id = ?',
        (id_alumno,)
    ).fetchone()
    conn.close()

    if fila and fila['correo_padre'] and fila['notif_correo']:
        return [fila['correo_padre']]
    return []


def _correos_de_todos():
    """Correos de todos los padres que tienen los avisos activados."""
    conn  = get_db()
    filas = conn.execute('''
        SELECT correo_padre FROM alumnos
        WHERE correo_padre IS NOT NULL
          AND correo_padre != ''
          AND notif_correo = 1
    ''').fetchall()
    conn.close()
    return [f['correo_padre'] for f in filas]


# ═══════════ FUNCIONES PÚBLICAS ═══════════

def avisar_a_padre(id_alumno, asunto, titulo, mensaje, tipo='aviso'):
    """Notifica al padre de un alumno específico."""
    destinatarios = _correo_de_alumno(id_alumno)
    if destinatarios:
        _enviar_en_segundo_plano(destinatarios, asunto, _plantilla(titulo, mensaje, tipo))


def avisar_a_todos(asunto, titulo, mensaje, tipo='aviso'):
    """Notifica a todos los padres del grupo."""
    destinatarios = _correos_de_todos()
    if destinatarios:
        _enviar_en_segundo_plano(destinatarios, asunto, _plantilla(titulo, mensaje, tipo))


def avisar_a_docente(asunto, titulo, mensaje):
    """Notifica a la maestra."""
    if DOCENTE_CORREO:
        html = _plantilla(titulo, mensaje, 'mensaje',
                          texto_boton='Abrir el panel',
                          url=f'{URL_BASE}/admin')
        _enviar_en_segundo_plano([DOCENTE_CORREO], asunto, html)
