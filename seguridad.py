"""
Límite de intentos de inicio de sesión.

Tras varios intentos fallidos desde la misma IP se bloquea temporalmente,
para frenar ataques de fuerza bruta.

Nota: el registro vive en memoria, así que se reinicia al reiniciar Flask.
Para el tamaño actual del sistema es suficiente.
"""

from datetime import datetime, timedelta

MAX_INTENTOS    = 5     # intentos fallidos permitidos
BLOQUEO_MINUTOS = 15    # bloqueo tras agotarlos

# { "ip:ambito": (intentos_fallidos, bloqueado_hasta) }
_registro = {}


def _clave(ip, ambito):
    return f'{ip or "desconocida"}:{ambito}'


def esta_bloqueado(ip, ambito='padre', maximo=MAX_INTENTOS):
    """Devuelve (bloqueado, minutos_restantes)."""
    k   = _clave(ip, ambito)
    reg = _registro.get(k)
    if not reg:
        return False, 0

    _, hasta = reg
    if hasta:
        if datetime.now() < hasta:
            restantes = int((hasta - datetime.now()).total_seconds() // 60) + 1
            return True, restantes
        _registro.pop(k, None)

    return False, 0


def registrar_fallo(ip, ambito='padre', maximo=MAX_INTENTOS):
    """Suma un intento fallido y bloquea si se agotaron."""
    k = _clave(ip, ambito)
    intentos, _ = _registro.get(k, (0, None))
    intentos += 1

    if intentos >= maximo:
        _registro[k] = (0, datetime.now() + timedelta(minutes=BLOQUEO_MINUTOS))
    else:
        _registro[k] = (intentos, None)


def limpiar(ip, ambito='padre'):
    """Borra el contador tras un inicio de sesión exitoso."""
    _registro.pop(_clave(ip, ambito), None)