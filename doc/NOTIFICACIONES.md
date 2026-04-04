# 📧 Configuración de Notificaciones

Este documento detalla la configuración del sistema de notificaciones multi-canal.

---

## Canales de Notificación

| Canal | Uso | Requisitos |
|-------|-----|------------|
| **Email** | Todas las notificaciones | Servidor SMTP (Gmail) |
| **WhatsApp** | Solo tickets CRÍTICOS | Cuenta Twilio |
| **Web** | En tiempo real | Ninguno adicional |

---

## 1. Configuración de Email (Gmail SMTP)

### Paso 1: Habilitar Verificación en 2 Pasos

1. Ir a [myaccount.google.com](https://myaccount.google.com)
2. Seguridad → Verificación en 2 pasos
3. Activar y configurar

### Paso 2: Crear Contraseña de Aplicación

1. En la misma página de Seguridad
2. Buscar "Contraseñas de aplicaciones"
3. Seleccionar app: **Correo**
4. Seleccionar dispositivo: **Ordenador Windows**
5. **Copiar la contraseña de 16 caracteres**

### Paso 3: Configurar `.env`

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=Sistema Tickets <noreply@coyahue.com>
```

### Paso 4: Verificar Configuración

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'Test Email',
    'Este es un correo de prueba.',
    settings.DEFAULT_FROM_EMAIL,
    ['tu_correo@gmail.com'],
    fail_silently=False,
)
```

---

## 2. Configuración de WhatsApp (Twilio)

### Paso 1: Crear Cuenta en Twilio

1. Ir a [twilio.com](https://www.twilio.com)
2. Crear cuenta gratuita
3. Verificar número de teléfono

### Paso 2: Activar WhatsApp Sandbox

1. En la consola de Twilio, ir a **Messaging → Try it out → Send a WhatsApp message**
2. Seguir instrucciones para activar el sandbox
3. El número de sandbox es: `+14155238886`

### Paso 3: Unirse al Sandbox

Desde el teléfono que recibirá notificaciones:

1. Abrir WhatsApp
2. Enviar mensaje a: `+1 415 523 8886`
3. Contenido del mensaje: `join <código-sandbox>`
4. Esperar confirmación

### Paso 4: Obtener Credenciales

En la consola de Twilio:
- **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Auth Token**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Paso 5: Configurar `.env`

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Paso 6: Configurar Perfil de Usuario

En el sistema, cada usuario debe:

1. Ir a **Mi Perfil**
2. Activar "Notificaciones WhatsApp"
3. Ingresar número con formato: `+56912345678`
4. Guardar cambios

---

## 3. Flujo de Notificaciones

### Cuándo se Envían

```python
# Tipos de notificación
TIPOS_NOTIFICACION = [
    ('ticket_creado', 'Ticket Creado'),        # → Admins
    ('ticket_asignado', 'Ticket Asignado'),    # → Técnico asignado
    ('ticket_comentario', 'Nuevo Comentario'), # → Creador o Técnico
    ('estado_cambio', 'Cambio de Estado'),     # → Técnico (si reabierto)
    ('ticket_resuelto', 'Ticket Resuelto'),    # → Creador
    ('ticket_cerrado', 'Ticket Cerrado'),      # → Creador
]
```

### Prioridad de Notificación

| Prioridad Ticket | Prioridad Notif | WhatsApp |
|------------------|-----------------|----------|
| Crítica | `critica` | ✅ Sí |
| Alta | `alta` | ❌ No |
| Media | `media` | ❌ No |
| Baja | `baja` | ❌ No |

### Código de Envío (services.py)

```python
def crear_notificacion_completa(usuario, ticket, tipo, prioridad='media'):
    # 1. Crear registro en BD
    notificacion = Notificacion.objects.create(...)
    
    # 2. Enviar Email (si habilitado)
    if perfil.notificaciones_email:
        enviar_email(usuario, notificacion, ticket)
    
    # 3. Enviar WhatsApp (solo si CRÍTICA y habilitado)
    if prioridad == 'critica' and perfil.notificaciones_whatsapp:
        enviar_whatsapp(usuario, notificacion, ticket)
    
    return notificacion
```

---

## 4. Personalización de Templates

### Email Template

Ubicación: `tickets/templates/emails/notificacion.html`

Variables disponibles:
- `{{ usuario }}` - Usuario destinatario
- `{{ notificacion }}` - Objeto notificación
- `{{ ticket }}` - Objeto ticket
- `{{ url_ticket }}` - URL al ticket

### Mensaje WhatsApp

El mensaje se construye en `services.py`:

```python
mensaje_texto = f"""
🔴 *TICKET CRÍTICO ASIGNADO*

{notificacion.titulo}

📋 *{ticket.titulo}*
ID: #{ticket.id}
Prioridad: ⚠️ *CRÍTICA*
Creado por: {ticket.creador.get_full_name()}

{ticket.descripcion[:100]}...

👉 *Requiere atención inmediata*
"""
```

---

## 5. Troubleshooting

### Email no se envía

1. Verificar logs en consola (DEBUG prints)
2. Comprobar `notificaciones_email = True` en perfil
3. Verificar credenciales Gmail
4. Probar envío manual desde shell

### WhatsApp no se envía

1. Verificar que el ticket sea prioridad `critica`
2. Comprobar `notificaciones_whatsapp = True` en perfil
3. Verificar que `numero_whatsapp` tenga formato correcto
4. Confirmar que el usuario se unió al sandbox
5. Revisar logs de Twilio en su consola

### Debug en Terminal

Los mensajes de debug se muestran en la terminal del servidor:

```
[DEBUG EMAIL] Intentando enviar email a user@example.com...
[DEBUG EMAIL] Email enviado exitosamente a user@example.com
```

O en caso de error:

```
[DEBUG EMAIL ERROR] Error al enviar email a user@example.com: ...
```

---

## 6. Costos

### Gmail SMTP
- **Gratis** hasta 500 emails/día

### Twilio WhatsApp
- **Sandbox**: Gratis (solo para desarrollo)
- **Producción**: ~$0.005 por mensaje (varía por país)

---

## 7. Migrar a Producción

### Email
Gmail SMTP funciona bien para volúmenes bajos. Para producción considerar:
- Amazon SES
- SendGrid
- Mailgun

### WhatsApp
Para producción con Twilio:
1. Solicitar número WhatsApp Business
2. Aprobar plantillas de mensajes
3. Configurar webhook para respuestas
