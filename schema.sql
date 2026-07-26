CREATE TABLE alumnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    curp TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    correo_padre TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE incidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,
    tipo TEXT,
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
    FOREIGN KEY(id_incidencia) REFERENCES incidencias(id)
);

CREATE TABLE calificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    materia TEXT NOT NULL,
    periodo TEXT,
    calificacion REAL,
    comentario TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE registro_accesos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip TEXT,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizado TIMESTAMP,
    activo BOOLEAN DEFAULT 1
);

CREATE TABLE mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    remitente TEXT NOT NULL,
    contenido TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visto BOOLEAN DEFAULT 0,
    fecha_visto TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
);

CREATE TABLE avisos_padre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alumno INTEGER NOT NULL,
    tipo TEXT NOT NULL,           -- 'paso_temprano', 'no_asistira', etc
    detalle TEXT,                  -- información específica
    fecha_aplica DATE,             -- para qué día es
    hora_aplica TEXT,              -- si aplica hora
    fecha_creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visto_maestra BOOLEAN DEFAULT 0,
    fecha_visto TIMESTAMP,
    FOREIGN KEY(id_alumno) REFERENCES alumnos(id)
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