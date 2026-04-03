import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import CORREO_REMITENTE, CORREO_CLAVE


def enviar_correo(destinatario, asunto, cuerpo_html):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = CORREO_REMITENTE
        msg['To']      = destinatario
        msg.attach(MIMEText(cuerpo_html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(CORREO_REMITENTE, CORREO_CLAVE)
            smtp.sendmail(CORREO_REMITENTE, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
