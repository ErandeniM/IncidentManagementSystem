"""
Generación de documentos PDF.

Dos documentos con propósitos distintos:

  · acta_incidencia    → una sola incidencia, formato formal de una hoja,
                         pensada para imprimirse, firmarse y anexarse.
  · expediente_completo → historial del alumno, para seguimiento y análisis.
"""

import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image)

from config import DOCENTE_NOMBRE, GRUPO_NOMBRE, ESCUELA_NOMBRE


RUTA_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'logo.png')

AZUL     = colors.HexColor('#2c3e50')
GRIS     = colors.HexColor('#636e72')
CLARO    = colors.HexColor('#f8f9fa')
BORDE    = colors.HexColor('#dee2e6')
TENUE    = colors.HexColor('#b2bec3')
NARANJA  = colors.HexColor('#ff6b35')
FONDO    = colors.HexColor('#f0eee5')

AREAS = [
    ('logico',    'Lógico-matemático'),
    ('fisico',    'Físico-deportivo'),
    ('artistico', 'Artístico'),
    ('social',    'Social'),
    ('lenguaje',  'Lenguaje'),
]


# ═══════════ ESTILOS ═══════════

def _estilos():
    return {
        'inst':   ParagraphStyle('inst', fontSize=10, fontName='Helvetica-Bold',
                                 alignment=1, spaceAfter=2, textColor=AZUL),
        'sub':    ParagraphStyle('sub', fontSize=8, fontName='Helvetica',
                                 alignment=1, spaceAfter=4, textColor=GRIS),
        'titulo': ParagraphStyle('titulo', fontSize=15, fontName='Helvetica-Bold',
                                 alignment=1, spaceBefore=10, spaceAfter=2, textColor=AZUL),
        'folio':  ParagraphStyle('folio', fontSize=9, fontName='Helvetica-Bold',
                                 alignment=1, spaceAfter=16, textColor=GRIS),
        'h2':     ParagraphStyle('h2', fontSize=10, fontName='Helvetica-Bold',
                                 spaceBefore=14, spaceAfter=6, textColor=AZUL),
        'texto':  ParagraphStyle('texto', fontSize=9.5, fontName='Helvetica',
                                 leading=14, textColor=colors.HexColor('#2d3436')),
        'normal': ParagraphStyle('normal', fontSize=9, fontName='Helvetica',
                                 spaceAfter=4, textColor=colors.HexColor('#2d3436')),
        'resumen': ParagraphStyle('resumen', fontSize=8, fontName='Helvetica',
                                  spaceAfter=14, textColor=GRIS),
        'nota':   ParagraphStyle('nota', fontSize=7.5, fontName='Helvetica',
                                 leading=10, textColor=TENUE),
    }


def _estilo_tabla(columnas_etiqueta=(0,)):
    """
    Estilo base de las tablas.
    `columnas_etiqueta` indica cuáles columnas son rótulos y llevan
    fondo gris y negritas.
    """
    reglas = [
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID',     (0, 0), (-1, -1), 0.4, BORDE),
        ('VALIGN',   (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING',  (0, 0), (-1, -1), 6),
    ]
    for col in columnas_etiqueta:
        reglas += [
            ('FONTNAME',   (col, 0), (col, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (col, 0), (col, -1), CLARO),
            ('TEXTCOLOR',  (col, 0), (col, -1), GRIS),
        ]
    return TableStyle(reglas)


def _estilo_encabezado():
    """Estilo para tablas con encabezado oscuro."""
    return TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0), AZUL),
        ('TEXTCOLOR',      (0, 0), (-1, 0), colors.white),
        ('FONTNAME',       (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, CLARO]),
        ('GRID',           (0, 0), (-1, -1), 0.3, BORDE),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING',        (0, 0), (-1, -1), 4),
    ])


# ═══════════ PIEZAS COMPARTIDAS ═══════════

def _encabezado_institucional(story, s, con_logo=True):
    if con_logo and os.path.exists(RUTA_LOGO):
        try:
            logo = Image(RUTA_LOGO, width=0.85 * inch, height=0.85 * inch, kind='proportional')
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 6))
        except Exception:
            pass

    ciclo = f'{datetime.now().year}-{datetime.now().year + 1}'
    story.append(Paragraph(ESCUELA_NOMBRE.upper(), s['inst']))
    story.append(Paragraph(
        f'{GRUPO_NOMBRE} · Docente: {DOCENTE_NOMBRE} · Ciclo escolar {ciclo}',
        s['sub']))


def _pie(canvas, documento):
    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(TENUE)
    canvas.setStrokeColor(BORDE)
    canvas.line(inch, 0.75 * inch, letter[0] - inch, 0.75 * inch)
    canvas.drawString(inch, 0.6 * inch,
                      f'{ESCUELA_NOMBRE} · Documento generado por el sistema de seguimiento escolar')
    canvas.drawRightString(letter[0] - inch, 0.6 * inch, f'Página {documento.page}')
    canvas.restoreState()


def _documento(buffer, margen_superior=0.8):
    return SimpleDocTemplate(buffer, pagesize=letter,
                             rightMargin=inch, leftMargin=inch,
                             topMargin=margen_superior * inch, bottomMargin=inch)


def _ficha_alumno(alumno):
    return Table([
        ['Alumno', alumno['nombre'],
         'CURP', alumno['curp']],
        ['Tutor', alumno.get('nombre_tutor') or 'No registrado',
         'Contacto', alumno.get('correo_padre') or '—'],
    ], colWidths=[0.8 * inch, 2.2 * inch, 0.8 * inch, 2.2 * inch],
        style=_estilo_tabla(columnas_etiqueta=(0, 2)))


def _barra(valor, ancho=2.4 * inch, alto=11):
    """Dibuja una barra de progreso para el perfil de habilidades."""
    d = Drawing(ancho, alto)
    d.add(Rect(0, 0, ancho, alto, fillColor=FONDO, strokeColor=BORDE, strokeWidth=0.5))
    if valor > 0:
        d.add(Rect(0, 0, ancho * min(valor, 100) / 100, alto,
                   fillColor=NARANJA, strokeColor=None))
    return d


# ═══════════ ACTA DE INCIDENCIA ═══════════

def acta_incidencia(inc, alumno):
    """
    Genera el acta de una sola incidencia.
    Devuelve (bytes_del_pdf, folio).
    """
    from repositorios.incidencias import etiqueta_tipo, etiqueta_nivel

    s      = _estilos()
    buffer = io.BytesIO()
    doc    = _documento(buffer)
    story  = []

    _encabezado_institucional(story, s)

    folio = f"{inc['fecha'][:4]}-{inc['id']:04d}" if inc.get('fecha') else f"{inc['id']:04d}"
    story.append(Paragraph('Registro de incidencia escolar', s['titulo']))
    story.append(Paragraph(f'Folio {folio}', s['folio']))

    # 1. Identificación
    story.append(Paragraph('1. Datos de identificación', s['h2']))
    story.append(Table([
        ['Alumno', alumno['nombre'], 'CURP',  alumno['curp']],
        ['Tutor',  alumno.get('nombre_tutor') or 'No registrado', 'Grupo', GRUPO_NOMBRE],
    ], colWidths=[0.75 * inch, 2.3 * inch, 0.7 * inch, 2.25 * inch],
        style=_estilo_tabla(columnas_etiqueta=(0, 2))))

    # 2. Datos del evento
    fecha = inc.get('fecha') or ''
    story.append(Paragraph('2. Datos del evento', s['h2']))
    story.append(Table([
        ['Fecha', fecha[:10],                       'Hora',  fecha[11:16]],
        ['Tipo',  etiqueta_tipo(inc.get('tipo')),   'Nivel', etiqueta_nivel(inc.get('nivel'))],
    ], colWidths=[0.75 * inch, 2.3 * inch, 0.7 * inch, 2.25 * inch],
        style=_estilo_tabla(columnas_etiqueta=(0, 2))))

    # 3. Descripción
    story.append(Paragraph('3. Descripción del hecho', s['h2']))
    story.append(Table([[Paragraph(inc.get('descripcion') or '—', s['texto'])]],
                       colWidths=[6.0 * inch],
                       style=TableStyle([
                           ('GRID',    (0, 0), (-1, -1), 0.4, BORDE),
                           ('VALIGN',  (0, 0), (-1, -1), 'TOP'),
                           ('PADDING', (0, 0), (-1, -1), 8),
                       ])))

    # 4. Atención brindada
    story.append(Paragraph('4. Atención brindada por la docente', s['h2']))
    story.append(Table([[Paragraph(
        inc.get('accion_docente') or 'No se registró acción específica.', s['texto'])]],
        colWidths=[6.0 * inch],
        style=TableStyle([
            ('GRID',       (0, 0), (-1, -1), 0.4, BORDE),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f4fce4')),
            ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
            ('PADDING',    (0, 0), (-1, -1), 8),
        ])))

    # 5. Trazabilidad
    story.append(Paragraph('5. Trazabilidad de la notificación', s['h2']))
    story.append(Table([
        ['Registrada',       fecha[:16] or '—'],
        ['Vista por tutor',  (inc.get('fecha_visto') or '')[:16] or 'Sin abrir'],
        ['Firma de enterado', (inc.get('fecha_enterado') or '')[:16] or 'Pendiente'],
        ['Firmada por',      inc.get('firmado_por') or '—'],
    ], colWidths=[1.6 * inch, 4.4 * inch], style=_estilo_tabla()))

    # 6. Respuesta del tutor
    if inc.get('comentario_padre'):
        story.append(Paragraph('6. Respuesta del tutor', s['h2']))
        story.append(Table([[Paragraph(f'"{inc["comentario_padre"]}"', s['texto'])]],
                           colWidths=[6.0 * inch],
                           style=TableStyle([
                               ('GRID',       (0, 0), (-1, -1), 0.4, BORDE),
                               ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f9ff')),
                               ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
                               ('PADDING',    (0, 0), (-1, -1), 8),
                           ])))

    # Firmas
    story.append(Spacer(1, 40))
    story.append(Table([
        ['_____________________________', '', '_____________________________'],
        [f'Docente: {DOCENTE_NOMBRE}', '', f'Tutor: {alumno.get("nombre_tutor") or ""}'],
    ], colWidths=[2.6 * inch, 0.8 * inch, 2.6 * inch],
        style=TableStyle([
            ('FONTSIZE',   (0, 0), (-1, -1), 8),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR',  (0, 1), (-1, 1), GRIS),
            ('TOPPADDING', (0, 1), (-1, 1), 3),
        ])))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f'Documento generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}. '
        'Los registros de visualización y firma provienen de la bitácora del sistema.',
        s['nota']))

    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    buffer.seek(0)
    return buffer.read(), folio


# ═══════════ EXPEDIENTE COMPLETO ═══════════

def expediente_completo(alumno, incidencias, calificaciones, perfil):
    """
    Genera el expediente completo del alumno.
    Devuelve los bytes del PDF.
    """
    from repositorios.incidencias import etiqueta_tipo

    s      = _estilos()
    buffer = io.BytesIO()
    doc    = _documento(buffer)
    story  = []

    _encabezado_institucional(story, s)
    story.append(Paragraph('Expediente del alumno', s['titulo']))
    story.append(Spacer(1, 10))
    story.append(_ficha_alumno(alumno))
    story.append(Spacer(1, 8))

    # Resumen
    firmadas   = sum(1 for i in incidencias if i.get('enterado'))
    pendientes = len(incidencias) - firmadas
    story.append(Paragraph(
        f'Total de incidencias: <b>{len(incidencias)}</b> · '
        f'Firmadas por el tutor: <b>{firmadas}</b> · '
        f'Pendientes de firma: <b>{pendientes}</b> · '
        f'Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}',
        s['resumen']))

    # ── Incidencias ──
    story.append(Paragraph('Incidencias', s['h2']))
    if incidencias:
        datos = [['#', 'Tipo', 'Fecha', 'Visto', 'Firmado', 'Firmó', 'Respuesta']]
        for inc in incidencias:
            datos.append([
                str(inc['numero']),
                etiqueta_tipo(inc.get('tipo'))[:18],
                (inc.get('fecha') or '')[:10] or '—',
                (inc.get('fecha_visto') or '')[:10] or '✗',
                (inc.get('fecha_enterado') or '')[:10] or '✗',
                (inc.get('firmado_por') or '—')[:18],
                (inc.get('comentario_padre') or '—')[:42],
            ])
        tabla = Table(datos, colWidths=[0.3 * inch, 1.15 * inch, 0.75 * inch,
                                        0.7 * inch, 0.7 * inch, 1.1 * inch, 1.8 * inch])
        tabla.setStyle(_estilo_encabezado())
        story.append(tabla)
    else:
        story.append(Paragraph('Sin incidencias registradas.', s['normal']))

    # ── Calificaciones ──
    story.append(Paragraph('Calificaciones', s['h2']))
    if calificaciones:
        datos = [['Trim.', 'Lenguajes', 'Ciencias', 'Ética', 'Comunitario', 'Faltas', 'Prom.']]
        for cal in calificaciones:
            notas  = [cal['lenguajes'], cal['ciencias'], cal['etica'], cal['comunitario']]
            llenas = [n for n in notas if n is not None]
            prom   = round(sum(llenas) / len(llenas), 1) if llenas else '—'
            datos.append([
                str(cal['trimestre']),
                *[('—' if n is None else str(int(n))) for n in notas],
                str(cal['inasistencias'] or 0),
                str(prom),
            ])
        tabla = Table(datos, colWidths=[0.5 * inch, 1 * inch, 1 * inch, 1 * inch,
                                        1.1 * inch, 0.6 * inch, 0.6 * inch])
        estilo = _estilo_encabezado()
        estilo.add('ALIGN', (0, 0), (-1, -1), 'CENTER')
        tabla.setStyle(estilo)
        story.append(tabla)
    else:
        story.append(Paragraph('Sin calificaciones registradas.', s['normal']))

    # ── Perfil ──
    story.append(Paragraph('Perfil de habilidades', s['h2']))
    if perfil:
        datos = [['Área', 'Nivel', 'Representación']]
        for campo, etiqueta in AREAS:
            valor = perfil[campo] or 0
            datos.append([etiqueta, f'{valor}%', _barra(valor)])

        tabla = Table(datos, colWidths=[2.0 * inch, 0.7 * inch, 2.6 * inch])
        estilo = _estilo_encabezado()
        estilo.add('ALIGN', (1, 0), (1, -1), 'CENTER')
        estilo.add('LEFTPADDING', (2, 1), (2, -1), 6)
        tabla.setStyle(estilo)
        story.append(tabla)

        if perfil.get('nota'):
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                f'<b>Observación de la maestra:</b> {perfil["nota"]}', s['normal']))
    else:
        story.append(Paragraph('Perfil sin registrar.', s['normal']))

    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    buffer.seek(0)
    return buffer.read()
