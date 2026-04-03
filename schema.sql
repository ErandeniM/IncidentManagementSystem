-- ─────────────────────────────────────────────
--  TABLA: alumnos
-- ─────────────────────────────────────────────
CREATE TABLE alumnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    curp TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    correo_padre TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
--  TABLA: incidencias
-- ─────────────────────────────────────────────
CREATE TABLE incidencias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno   INTEGER NOT NULL,
    fecha       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,
    tipo        TEXT,   -- 'Caída', 'Llanto', 'Comentario', 'Logro', 'Otro'
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

-- ─────────────────────────────────────────────
--  TABLA: incidencia_seguimiento
-- ─────────────────────────────────────────────
CREATE TABLE incidencia_seguimiento (
    id_incidencia   INTEGER PRIMARY KEY,
    visto           BOOLEAN   DEFAULT 0,
    fecha_visto     TIMESTAMP,
    enterado        BOOLEAN   DEFAULT 0,
    fecha_enterado  TIMESTAMP,
    comentario_padre TEXT,
    fecha_comentario TIMESTAMP,
    FOREIGN KEY(id_incidencia) REFERENCES incidencias(id)
);

-- ─────────────────────────────────────────────
--  TABLA: calificaciones
-- ─────────────────────────────────────────────
CREATE TABLE calificaciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno    INTEGER NOT NULL,
    materia      TEXT NOT NULL,
    periodo      TEXT NOT NULL,   -- 'Bimestre 1', 'Bimestre 2', etc.
    calificacion REAL NOT NULL,   -- 0.0 a 10.0
    comentario   TEXT,
    fecha        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

-- ─────────────────────────────────────────────
--  TABLA: perfil_alumno  (valores 0-100 por área)
-- ─────────────────────────────────────────────
CREATE TABLE perfil_alumno (
    id_alumno  INTEGER PRIMARY KEY,
    logico     INTEGER DEFAULT 0,
    fisico     INTEGER DEFAULT 0,
    artistico  INTEGER DEFAULT 0,
    social     INTEGER DEFAULT 0,
    lenguaje   INTEGER DEFAULT 0,
    nota       TEXT,               -- observación libre de la maestra
    actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

-- ─────────────────────────────────────────────
--  TABLA: actividades_recomendadas
-- ─────────────────────────────────────────────
CREATE TABLE actividades_recomendadas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno   INTEGER NOT NULL,
    actividad   TEXT NOT NULL,
    categoria   TEXT,    -- 'Académica', 'Física', 'Artística', 'Social'
    completada  BOOLEAN DEFAULT 0,
    fecha       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE registro_accesos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip TEXT,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

--AVISOS GENERALES PARA TODOS LOS ALUMNOS (ej. eventos, recordatorios, etc.)--
CREATE TABLE avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT 1
);