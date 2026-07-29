"""
Generación de documentos PDF.

Por ahora contiene el acta individual de incidencia: un documento formal
de una hoja, pensado para imprimirse, firmarse y anexarse a un expediente.
"""

import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image)
from repositorios.incidencias import etiqueta_tipo, etiqueta_nivel

from config import DOCENTE_NOMBRE, GRUPO_NOMBRE, ESCUELA_NOMBRE


RUTA_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'logo.png')

AZUL   = colors.HexColor('#2c3e50')
GRIS   = colors.HexColor('#636e72')
CLARO  = colors.HexColor('#f8f9fa')
BORDE  = colors.HexColor('#dee2e6')
TENUE  = colors.HexColor('#b2bec3')


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
        'nota':   ParagraphStyle('nota', fontSize=7.5, fontName='Helvetica',
                                 leading=10, textColor=TENUE),
    }


def _estilo_tabla(columnas_etiqueta=(0,)):
    """
    Estilo base de las tablas del acta.
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


# ═══════════ ENCABEZADO Y PIE ═══════════

def _encabezado(story, s):
    if os.path.exists(RUTA_LOGO):
        try:
            logo = Image(RUTA_LOGO, width=0.85 * inch, height=0.85 * inch, kind='proportional')
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 6))
        except Exception:
            pass

    story.append(Paragraph(ESCUELA_NOMBRE.upper(), s['inst']))
    story.append(Paragraph(
        f"{GRUPO_NOMBRE} · Docente responsable: {DOCENTE_NOMBRE}", s['sub']))


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


# ═══════════ ACTA DE INCIDENCIA ═══════════

def acta_incidencia(inc, alumno):
    """
    Genera el acta de una sola incidencia.
    Devuelve los bytes del PDF listos para enviar al navegador.
    """
    s      = _estilos()
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=inch, leftMargin=inch,
                               topMargin=0.8 * inch, bottomMargin=inch)
    story = []

    _encabezado(story, s)

    folio = f"{inc['fecha'][:4]}-{inc['id']:04d}" if inc.get('fecha') else f"{inc['id']:04d}"
    story.append(Paragraph('Registro de incidencia escolar', s['titulo']))
    story.append(Paragraph(f'Folio {folio}', s['folio']))
    
# ── Identificación ──
    story.append(Paragraph('1. Datos de identificación', s['h2']))
    story.append(Table([
        ['Alumno',  alumno['nombre'],                              'CURP', alumno['curp']],
        ['Tutor',   alumno.get('nombre_tutor') or 'No registrado', 'Grupo', GRUPO_NOMBRE],
    ], colWidths=[0.75 * inch, 2.3 * inch, 0.7 * inch, 2.25 * inch],
        style=_estilo_tabla(columnas_etiqueta=(0, 2))))
    
    # ── Datos del evento ── #
    fecha = inc.get('fecha') or ''
    story.append(Paragraph('2. Datos del evento', s['h2']))
    story.append(Table([
        ['Fecha', fecha[:10], 'Hora',  fecha[11:16]],
        ['Tipo',  etiqueta_tipo(inc.get('tipo')), 'Nivel', etiqueta_nivel(inc.get('nivel'))],
    ], colWidths=[0.75 * inch, 2.3 * inch, 0.7 * inch, 2.25 * inch],
        style=_estilo_tabla(columnas_etiqueta=(0, 2))))

    # ── Descripción ──
    story.append(Paragraph('3. Descripción del hecho', s['h2']))
    story.append(Table([[Paragraph(inc.get('descripcion') or '—', s['texto'])]],
                       colWidths=[6.0 * inch],
                       style=TableStyle([
                           ('GRID',   (0, 0), (-1, -1), 0.4, BORDE),
                           ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('PADDING', (0, 0), (-1, -1), 8),
                       ])))

    # ── Acción del docente ──
    story.append(Paragraph('4. Atención brindada por la docente', s['h2']))
    story.append(Table([[Paragraph(inc.get('accion_docente') or 'No se registró acción específica.', s['texto'])]],
                       colWidths=[6.0 * inch],
                       style=TableStyle([
                           ('GRID',       (0, 0), (-1, -1), 0.4, BORDE),
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f4fce4')),
                           ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
                           ('PADDING',    (0, 0), (-1, -1), 8),
                       ])))

    # ── Trazabilidad ──
    story.append(Paragraph('5. Trazabilidad de la notificación', s['h2']))
    story.append(Table([
        ['Registrada',      fecha[:16] or '—'],
        ['Vista por tutor', (inc.get('fecha_visto') or '')[:16] or 'Sin abrir'],
        ['Firma de enterado', (inc.get('fecha_enterado') or '')[:16] or 'Pendiente'],
        ['Firmada por',     inc.get('firmado_por') or '—'],
    ], colWidths=[1.6 * inch, 4.4 * inch], style=_estilo_tabla()))

    # ── Respuesta del tutor ──
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

    # ── Firmas ──
    story.append(Spacer(1, 40))
    story.append(Table([
        ['_____________________________', '', '_____________________________'],
        [f'Docente: {DOCENTE_NOMBRE}', '', f'Tutor: {alumno.get("nombre_tutor") or ""}'],
    ], colWidths=[2.6 * inch, 0.8 * inch, 2.6 * inch],
        style=TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN',    (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (0, 1), (-1, 1), GRIS),
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
