-- ═══════════════════════════════════════════════════════════
--  Mi Salón — esquema de la base de datos
--
--  Define la estructura completa. Se ejecuta solo cuando la base
--  no existe todavía (ver init_db en database.py). Los cambios
--  sobre una base ya creada van por migrar.py.
-- ═══════════════════════════════════════════════════════════


-- ── Alumnos y sus tutores ──────────────────────────────────

CREATE TABLE alumnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    curp TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    correo_padre TEXT,
    nombre_tutor TEXT,
    notif_correo BOOLEAN DEFAULT 1,
    id_grupo INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        acepto_aviso INTEGER DEFAULT 0,
    fecha_acepto_aviso TIMESTAMP,
    acepto_aviso_por TEXT
);


-- ── Incidencias y su seguimiento ───────────────────────────
--  Se separan a propósito: la incidencia es el hecho que registra
--  la docente; el seguimiento es la reacción del tutor.

CREATE TABLE incidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo TEXT,
    nivel TEXT DEFAULT 'informativo',
    descripcion TEXT NOT NULL,
    accion_docente TEXT,
    id_docente INTEGER DEFAULT 1,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE incidencia_seguimiento (
    id_incidencia INTEGER PRIMARY KEY,
    visto BOOLEAN DEFAULT 0,
    fecha_visto TIMESTAMP,
    enterado BOOLEAN DEFAULT 0,
    fecha_enterado TIMESTAMP,
    comentario_padre TEXT,
    fecha_comentario TIMESTAMP,
    firmado_por TEXT,
    acepto_declaracion INTEGER DEFAULT 0,
    FOREIGN KEY(id_incidencia) REFERENCES incidencias(id)
);


-- ── Seguimiento académico ──────────────────────────────────

CREATE TABLE calificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    lenguajes REAL,
    ciencias REAL,
    etica REAL,
    comunitario REAL,
    inasistencias INTEGER DEFAULT 0,
    observaciones TEXT,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_docente INTEGER DEFAULT 1,
    UNIQUE(id_alumno, trimestre),
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE perfil_alumno (
    id_alumno INTEGER PRIMARY KEY,
    logico INTEGER DEFAULT 0,
    fisico INTEGER DEFAULT 0,
    artistico INTEGER DEFAULT 0,
    social INTEGER DEFAULT 0,
    lenguaje INTEGER DEFAULT 0,
    nota TEXT,
    actualizado TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE actividades_recomendadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    actividad TEXT NOT NULL,
    categoria TEXT DEFAULT 'General',
    completada BOOLEAN DEFAULT 0,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_docente INTEGER DEFAULT 1,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);


-- ── Tareas con fecha y control de cumplimiento ─────────────

CREATE TABLE tareas_entrega (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    materia TEXT,
    fecha_asignada TIMESTAMP,
    fecha_entrega DATE,
    id_docente INTEGER DEFAULT 1
);

CREATE TABLE entregas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_tarea INTEGER NOT NULL,
    id_alumno INTEGER NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    nota TEXT,
    fecha_registro TIMESTAMP,
    UNIQUE(id_tarea, id_alumno),
    FOREIGN KEY(id_tarea) REFERENCES tareas_entrega(id) ON DELETE CASCADE,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);


-- ── Avisos generales y sus confirmaciones ──────────────────

CREATE TABLE avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizado TIMESTAMP,
    activo BOOLEAN DEFAULT 1,
    id_docente INTEGER DEFAULT 1,
        eliminado INTEGER DEFAULT 0,
    fecha_eliminado TIMESTAMP
);

CREATE TABLE avisos_confirmaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aviso INTEGER NOT NULL,
    id_alumno INTEGER NOT NULL,
    fecha_confirmado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id_aviso, id_alumno),
    FOREIGN KEY(id_aviso) REFERENCES avisos(id) ON DELETE CASCADE,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);


-- ── Avisos logísticos que envía el tutor ───────────────────

CREATE TABLE avisos_padre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    detalle TEXT,
    fecha_aplica DATE,
    hora_aplica TEXT,
    fecha_creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visto_maestra BOOLEAN DEFAULT 0,
    fecha_visto TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id),
    acusado_por TEXT
);


-- ── Chat privado tutor / docente ───────────────────────────

CREATE TABLE mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    remitente TEXT NOT NULL,
    contenido TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visto BOOLEAN DEFAULT 0,
    fecha_visto TIMESTAMP,
    ref_tipo TEXT,
    ref_id INTEGER,
    ref_titulo TEXT,
    id_docente INTEGER DEFAULT 1,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);


-- ── Bitácora de accesos ────────────────────────────────────

CREATE TABLE registro_accesos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip TEXT,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

-- ── Calendario escolar ─────────────────────────────────────

CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    fecha_fin DATE,                    -- para periodos como vacaciones
    titulo TEXT NOT NULL,
    detalle TEXT,
    tipo TEXT DEFAULT 'escuela',       -- ver TIPOS en repositorios/eventos.py
    oficial INTEGER DEFAULT 0,         -- 1 = viene del calendario SEC
    hay_clases INTEGER DEFAULT 1,
    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_docente INTEGER DEFAULT 1
);

-- ═══════════════════════════════════════════════════════════
--  Índices
--
--  SQLite solo indexa llaves primarias y restricciones UNIQUE.
--  Sin estos, cada consulta con WHERE id_alumno = ? recorre la
--  tabla completa.
-- ═══════════════════════════════════════════════════════════

CREATE INDEX idx_incidencias_alumno    ON incidencias(id_alumno);
CREATE INDEX idx_incidencias_fecha     ON incidencias(fecha);
CREATE INDEX idx_calificaciones_alumno ON calificaciones(id_alumno);
CREATE INDEX idx_actividades_alumno    ON actividades_recomendadas(id_alumno);
CREATE INDEX idx_entregas_tarea        ON entregas(id_tarea);
CREATE INDEX idx_entregas_alumno       ON entregas(id_alumno);
CREATE INDEX idx_confirmaciones_aviso  ON avisos_confirmaciones(id_aviso);
CREATE INDEX idx_confirmaciones_alumno ON avisos_confirmaciones(id_alumno);
CREATE INDEX idx_avisos_padre_alumno   ON avisos_padre(id_alumno);
CREATE INDEX idx_mensajes_alumno       ON mensajes(id_alumno, fecha);
CREATE INDEX idx_accesos_alumno        ON registro_accesos(id_alumno, fecha);
CREATE INDEX idx_eventos_fecha ON eventos(fecha);