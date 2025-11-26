"""
Servicios para envío de notificaciones por múltiples canales:
- Email
- WhatsApp (Twilio)
- Notificaciones en tiempo real (Web)
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from .models import Notificacion
import logging

logger = logging.getLogger('tickets')

# Configuración de Twilio
try:
    from twilio.rest import Client
    TWILIO_DISPONIBLE = True
except ImportError:
    TWILIO_DISPONIBLE = False
    logger.warning("Twilio no instalado. WhatsApp no disponible.")


def crear_notificacion_completa(usuario, ticket, tipo, prioridad='media'):
    """
    Crea una notificación y dispara el envío por todos los canales configurados.
    
    Args:
        usuario: Usuario que recibe la notificación (objeto User)
        ticket: Ticket relacionado (objeto Ticket)
        tipo: Tipo de notificación (str) - 'ticket_asignado', 'ticket_comentario', etc
        prioridad: Prioridad (str) - 'baja', 'media', 'alta', 'critica'
    
    Returns:
        Notificacion: Objeto de notificación creado
    """
    
    # Generar contenido según el tipo
    contenido = generar_contenido_notificacion(tipo, ticket)
    
    # Crear registro en BD
    notificacion = Notificacion.objects.create(
        usuario=usuario,
        ticket=ticket,
        tipo=tipo,
        prioridad=prioridad,
        titulo=contenido['titulo'],
        mensaje=contenido['mensaje'],
        enlace=f'/ticket/{ticket.id}/'
    )
    
    logger.info(f"Notificación creada para {usuario.username}: {tipo} - Prioridad: {prioridad}")
    
    # Enviar por EMAIL (si está habilitado)
    try:
        perfil = usuario.perfilusuario
        if perfil.notificaciones_email:
            enviar_email(usuario, notificacion, ticket)
    except Exception as e:
        logger.error(f"Error al enviar email a {usuario.username}: {str(e)}")
    
    # Enviar por WhatsApp (si es CRÍTICA y está habilitado)
    try:
        perfil = usuario.perfilusuario
        if prioridad == 'critica' and perfil.notificaciones_whatsapp:
            if perfil.numero_whatsapp:
                enviar_whatsapp(usuario, notificacion, ticket)
            else:
                logger.warning(f"Usuario {usuario.username} no tiene número WhatsApp registrado")
    except Exception as e:
        logger.error(f"Error al enviar WhatsApp a {usuario.username}: {str(e)}")
    
    return notificacion


def generar_contenido_notificacion(tipo, ticket):
    """
    Genera el contenido de la notificación según su tipo.
    
    Args:
        tipo: Tipo de notificación
        ticket: Objeto Ticket
    
    Returns:
        dict: Diccionario con 'titulo' y 'mensaje'
    """
    
    contenidos = {
        'ticket_creado': {
            'titulo': '🆕 Nuevo Ticket Creado',
            'mensaje': f'Se creó un nuevo ticket: {ticket.titulo}'
        },
        'ticket_asignado': {
            'titulo': '📌 Te Asignaron un Ticket',
            'mensaje': f'Te asignaron: {ticket.titulo}'
        },
        'ticket_comentario': {
            'titulo': '💬 Nuevo Comentario',
            'mensaje': f'Hay un nuevo comentario en: {ticket.titulo}'
        },
        'ticket_resuelto': {
            'titulo': '✅ Ticket Resuelto',
            'mensaje': f'Tu ticket ha sido resuelto: {ticket.titulo}'
        },
        'ticket_cerrado': {
            'titulo': '🔒 Ticket Cerrado',
            'mensaje': f'Tu ticket ha sido cerrado: {ticket.titulo}'
        },
        'estado_cambio': {
            'titulo': '🔄 Cambio de Estado',
            'mensaje': f'{ticket.titulo} → Nuevo estado: {ticket.get_estado_display()}'
        },
    }
    
    return contenidos.get(tipo, {'titulo': 'Notificación', 'mensaje': 'Nueva notificación'})


def enviar_email(usuario, notificacion, ticket):
    """
    Envía email con la notificación.
    
    Args:
        usuario: Usuario destinatario
        notificacion: Objeto Notificacion
        ticket: Objeto Ticket relacionado
    """
    
    try:
        # Preparar contexto
        contexto = {
            'usuario': usuario,
            'notificacion': notificacion,
            'ticket': ticket,
            'url_ticket': f"http://{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}/ticket/{ticket.id}/",
        }
        
        # Renderizar template HTML
        html_message = render_to_string('emails/notificacion.html', contexto)
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject=f"🎫 {notificacion.titulo}",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Marcar como enviado
        notificacion.email_enviado = True
        notificacion.email_fecha = timezone.now()
        notificacion.save(update_fields=['email_enviado', 'email_fecha'])
        
        logger.info(f"Email enviado a {usuario.email} - Notificación #{notificacion.id}")
        
    except Exception as e:
        logger.error(f"Error enviando email a {usuario.email}: {str(e)}")


def enviar_whatsapp(usuario, notificacion, ticket):
    """
    Envía WhatsApp al usuario para tickets CRÍTICOS usando Twilio.
    
    Args:
        usuario: Usuario destinatario
        notificacion: Objeto Notificacion
        ticket: Objeto Ticket relacionado
    """
    
    if not TWILIO_DISPONIBLE:
        logger.warning("Twilio no disponible. Instalarlo con: pip install twilio")
        return
    
    try:
        # Validar configuración
        if not hasattr(settings, 'TWILIO_ACCOUNT_SID') or not settings.TWILIO_ACCOUNT_SID:
            logger.error("TWILIO_ACCOUNT_SID no configurado en settings.py")
            return
        
        # Inicializar cliente Twilio
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        numero_destino = f"whatsapp:{usuario.perfilusuario.numero_whatsapp}"
        
        # Crear mensaje
        mensaje_texto = f"""
🔴 *TICKET CRÍTICO ASIGNADO*

{notificacion.titulo}

📋 *{ticket.titulo}*
ID: #{ticket.id}
Prioridad: ⚠️ *CRÍTICA*
Creado por: {ticket.creado_por.get_full_name()}

{ticket.descripcion[:100]}...

👉 *Abrir ticket:*
http://tu-app.com/ticket/{ticket.id}/

⏰ *Responde ASAP*
        """.strip()
        
        # Enviar por WhatsApp
        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            body=mensaje_texto,
            to=numero_destino
        )
        
        # Marcar como enviado
        notificacion.whatsapp_enviado = True
        notificacion.whatsapp_fecha = timezone.now()
        notificacion.save(update_fields=['whatsapp_enviado', 'whatsapp_fecha'])
        
        logger.info(f"WhatsApp enviado a {usuario.perfilusuario.numero_whatsapp} - SID: {message.sid}")
        
    except Exception as e:
        logger.error(f"Error enviando WhatsApp a {usuario.perfilusuario.numero_whatsapp}: {str(e)}")


def marcar_notificacion_leida(notificacion):
    """Marca una notificación como leída."""
    if not notificacion.leida:
        notificacion.leida = True
        notificacion.fecha_leida = timezone.now()
        notificacion.save(update_fields=['leida', 'fecha_leida'])


def marcar_todas_leidas(usuario):
    """Marca todas las notificaciones no leídas como leídas."""
    Notificacion.objects.filter(usuario=usuario, leida=False).update(
        leida=True,
        fecha_leida=timezone.now()
    )


def obtener_notificaciones_no_leidas(usuario, limite=5):
    """
    Obtiene las notificaciones no leídas más recientes del usuario.
    
    Args:
        usuario: Usuario
        limite: Número máximo de notificaciones a retornar
    
    Returns:
        QuerySet: Notificaciones no leídas ordenadas por fecha
    """
    return Notificacion.objects.filter(
        usuario=usuario,
        leida=False
    ).select_related('ticket').order_by('-fecha_creacion')[:limite]


def obtener_todas_notificaciones(usuario, limite=20):
    """
    Obtiene todas las notificaciones del usuario (leídas y no leídas).
    
    Args:
        usuario: Usuario
        limite: Número máximo de notificaciones a retornar
    
    Returns:
        QuerySet: Todas las notificaciones ordenadas por fecha
    """
    return Notificacion.objects.filter(
        usuario=usuario
    ).select_related('ticket').order_by('-fecha_creacion')[:limite]
