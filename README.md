# 🏫 Sistema de Seguimiento Escolar

> Portal digital de comunicación trazable entre docentes y padres de familia, diseñado desde la experiencia real del aula.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-3-blue?style=flat-square&logo=sqlite)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.1-purple?style=flat-square&logo=bootstrap)
![Status](https://img.shields.io/badge/Estado-En%20desarrollo%20activo-orange?style=flat-square)

---

## 📋 ¿Qué es este sistema?

Una aplicación web que digitaliza y formaliza la comunicación entre el docente y los padres de familia en educación primaria. Cada incidencia registrada genera una cadena de evidencia verificable: el docente notifica, el padre es informado, el padre confirma que lo leyó y firma su enterado con texto escrito y timestamp exacto.

**El problema que resuelve:** cuando un padre alega que nunca fue informado de algo, el sistema demuestra con evidencia objetiva que sí lo fue, cuándo abrió la notificación y qué respondió.

---

## ✨ Funcionalidades principales

### Panel de la maestra (admin)
- 📝 Registro de incidencias por tipo — Caída, Llanto, Logro, Comentario, Otro
- 📧 Notificación automática por correo al padre al registrar cada incidencia
- 📊 Registro de calificaciones por materia y periodo
- 🧠 Perfil de aprendizaje del alumno en 5 dimensiones con sliders
- 🎯 Actividades recomendadas para reforzar en casa
- 📢 Avisos generales con popup inteligente para todos los padres
- 📋 Registro de accesos — quién entró, cuándo y desde qué IP
- 📄 Generación de PDF del expediente completo del alumno
- 🗂️ Pestañas persistentes — el sistema recuerda en qué sección estabas trabajando

### Portal del padre de familia
- 🔐 Acceso individual con CURP del alumno y contraseña
- 👁️ Visto automático con timestamp al abrir cada incidencia
- ✍️ Firma de enterado obligatoria con texto escrito
- 📊 Consulta de calificaciones con indicador visual de color
- 🧠 Perfil de aprendizaje en gráfica radar
- 🎯 Actividades recomendadas por categoría
- 📢 Avisos con popup que no vuelve a aparecer si ya fue leído

---

## 🔐 Flujo de evidencia

```
Maestra registra incidencia
        ↓
Correo automático al padre (sin revelar el detalle)
        ↓
Padre ingresa al portal → IP + timestamp registrados
        ↓
Padre abre el detalle → visto automático con timestamp
        ↓
Padre escribe respuesta obligatoria → enterado firmado con timestamp
        ↓
Maestra ve el estado completo en el expediente
```

Cada paso queda registrado en la base de datos. Nadie puede alegar desconocimiento.

---

## 🛠️ Tecnologías

| Componente | Tecnología |
|---|---|
| Backend | Python 3 + Flask |
| Base de datos | SQLite |
| Frontend | Bootstrap 5 + Nunito (Google Fonts) |
| Gráficas | Chart.js |
| Correo | smtplib + Gmail SMTP |
| PDF | ReportLab |
| Control de versiones | Git + GitHub |

---

## 📁 Estructura del proyecto

```
IncidentManagementSystem/
├── app.py                  ← arranque de Flask y registro de blueprints
├── config.py               ← claves y configuración (excluido de git)
├── database.py             ← conexión a SQLite y utilidades
├── email_utils.py          ← función de envío de correo
├── schema.sql              ← estructura de la base de datos
├── routes/
│   ├── __init__.py
│   ├── auth.py             ← login y logout de padres
│   ├── alumno.py           ← panel del padre
│   └── admin.py            ← panel completo de la maestra
└── templates/
    ├── login.html
    ├── alumno.html
    ├── detalle_incidencia.html
    ├── admin_login.html
    ├── admin_dashboard.html
    ├── admin_expediente.html
    ├── admin_accesos.html
    └── admin_avisos.html
```

---

## 🚀 Instalación local

### Requisitos
- Python 3.8 o superior
- pip

### Pasos

**1. Clonar el repositorio**
```bash
git clone https://github.com/ErandeniM/IncidentManagementSystem.git
cd IncidentManagementSystem
```

**2. Crear entorno virtual**
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate           # Windows
```

**3. Instalar dependencias**
```bash
pip install flask reportlab
```

**4. Crear el archivo de configuración**

Crea un archivo `config.py` en la raíz con este contenido:
```python
DATABASE       = 'incidencias.db'
SECRET_KEY     = 'tu_clave_secreta_aqui'
ADMIN_PASSWORD = 'tu_contraseña_admin'

CORREO_REMITENTE = 'tu_correo@gmail.com'
CORREO_CLAVE     = 'tu_contraseña_de_aplicacion'
```

> ⚠️ El archivo `config.py` está excluido del repositorio por seguridad. Nunca lo subas a GitHub.

**5. Correr la aplicación**
```bash
python app.py
```

**6. Acceder**
- Portal de padres → `http://127.0.0.1:5000`
- Panel de la maestra → `http://127.0.0.1:5000/admin`

Al iniciar por primera vez se crea automáticamente la base de datos con un alumno de ejemplo:
- **CURP:** `MABC010101`
- **Contraseña:** `maria2024`

---

## 📧 Configuración de correo Gmail

Para que las notificaciones automáticas funcionen necesitas una **contraseña de aplicación** de Gmail:

1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. Seguridad → Verificación en dos pasos (actívala)
3. Busca **Contraseñas de aplicación**
4. Selecciona "Correo" y "Otro dispositivo"
5. Copia la clave de 16 caracteres generada
6. Pégala en `CORREO_CLAVE` de tu `config.py`

> Nota: en redes universitarias o corporativas los puertos SMTP pueden estar bloqueados. Prueba desde red doméstica o datos móviles.

---

## 🗄️ Base de datos

El sistema usa SQLite con 8 tablas:

| Tabla | Contenido |
|---|---|
| `alumnos` | Registro de alumnos con credenciales y correo del padre |
| `incidencias` | Eventos registrados por la maestra |
| `incidencia_seguimiento` | Estado de cada incidencia: visto, enterado, firma |
| `calificaciones` | Registro académico por materia y periodo |
| `perfil_alumno` | Perfil de aprendizaje en 5 dimensiones |
| `actividades_recomendadas` | Sugerencias para reforzar en casa |
| `avisos` | Comunicados generales con estado activo/inactivo |
| `registro_accesos` | Log de cada inicio de sesión con IP y timestamp |

---

## 📌 Estado del proyecto

| Función | Estado |
|---|---|
| Login de padres + registro de accesos | ✅ Completo |
| Expediente digital con 4 secciones | ✅ Completo |
| Visto automático y firma de enterado | ✅ Completo |
| Avisos generales con popup inteligente | ✅ Completo |
| Pestañas persistentes en admin | ✅ Completo |
| Notificaciones por correo | ✅ Código listo |
| Generación de PDF | ✅ Código listo |
| Arquitectura modular con Blueprints | ✅ Completo |
| Tabla de calificaciones tipo spreadsheet | 🔄 En desarrollo |
| Integración con IA | 📋 Planeado |
| Generador de planeaciones didácticas | 📋 Planeado |

---

## 🔭 Visión a futuro

- Captura masiva de calificaciones en tabla tipo hoja de cálculo con campos formativos de la NEM
- Asistente con IA para redacción de incidencias
- Detección de patrones de conducta y alertas preventivas
- Generador de planeaciones didácticas alineadas a la Nueva Escuela Mexicana
- Protocolos de seguridad escolar dinámicos
- Exportación a Excel del cuadro de calificaciones
- Notificaciones push en versión móvil

---

## 👩‍💻 Autora

**Erandeni Mendivil**
Docente de Educación Primaria | Estudiante de Ingeniería en Sistemas
Hermosillo, Sonora — México

> Proyecto desarrollado desde una necesidad real del aula, con proyección hacia validación institucional SEC/SEP como herramienta estándar de documentación y comunicación escolar.

---

## 📄 Licencia

Este proyecto es de desarrollo personal con fines educativos e institucionales. Todos los derechos reservados © 2025 Erandeni Mendivil.
