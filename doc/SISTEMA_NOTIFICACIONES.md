# 📢 Sistema de Notificaciones - Grupo Coyahue

## Descripción General

Sistema de notificaciones multi-canal completamente funcional para la plataforma de gestión de tickets. Incluye:

- **📧 Email**: Notificaciones por correo electrónico con HTML profesional
- **📱 WhatsApp**: Notificaciones por WhatsApp (solo para tickets críticos)
- **🔔 Notificaciones Web**: Actualizaciones en tiempo real en la plataforma
- **📊 Panel de Administración**: Visualizar y gestionar todas las notificaciones
- **⏱️ Polling Automático**: Actualización cada 30 segundos de notificaciones nuevas

---

## Características Implementadas

### 1. Modelo de Datos (Notificacion)

```python
class Notificacion(models.Model):
    usuario           # FK a User - Destinatario
    ticket            # FK a Ticket - Ticket relacionado
    tipo              # Tipo: ticket_creado, ticket_asignado, ticket_comentario, estado_cambio, ticket_resuelto, ticket_cerrado
    prioridad         # baja, media, alta, critica
    titulo            # Título de la notificación
    mensaje           # Contenido del mensaje
    email_enviado     # ¿Se envió por email?
    email_fecha       # Cuándo se envió
    whatsapp_enviado  # ¿Se envió por WhatsApp?
    whatsapp_fecha    # Cuándo se envió
    leida             # ¿El usuario la leyó?
    fecha_leida       # Cuándo la leyó
    fecha_creacion    # Cuándo se creó
    enlace            # URL relacionada
```

### 2. Canales de Notificación

#### 📧 Email
- Backend: Django's `send_mail()` con SMTP
- Template: HTML profesional con estilos inline
- Proveedor: Gmail (recomendado) u otro SMTP
- Contenido: Detalles del ticket, prioridad, enlace para ver más

#### 📱 WhatsApp
- Proveedor: Twilio
- Activado: Solo para tickets **críticos**
- Contenido: Mensaje formateado con emojis y detalles clave
- Formato: `+57 XXX XXX XXXX` (configurado por usuario)

#### 🔔 Web
- Método: JavaScript polling cada 30 segundos
- UI: Campana en navbar con badge de contador
- Dropdown: 5 notificaciones más recientes
- Página completa: `/notificaciones/` con filtros

### 3. Puntos de Integración

#### Cuando se crea un ticket:
```
┌─────────────────────────┐
│ Usuario crea ticket     │
└────────────┬────────────┘
             │
             ▼
    ┌────────────────────────┐
    │ Notificar a todos los  │
    │ administradores        │
    │                        │
    │ Tipo: ticket_creado    │
    │ Prioridad: según ticket│
    └────────────────────────┘
```

#### Cuando se asigna un ticket:
```
┌─────────────────────────┐
│ Admin asigna a técnico  │
└────────────┬────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ Notificar al técnico         │
    │ (Email + WhatsApp si crítico)│
    │                              │
    │ Tipo: ticket_asignado        │
    │ Prioridad: alta/critica      │
    └──────────────────────────────┘
```

#### Cuando cambia el estado:
```
Estado: resuelto → Notificar creador (ticket_resuelto)
Estado: cerrado  → Notificar creador (ticket_cerrado)
Estado: reabierto→ Notificar técnico (estado_cambio)
```

#### Cuando se agrega un comentario:
```
┌─────────────────────────────┐
│ Se crea comentario en ticket│
└────────────┬────────────────┘
             │
             ├─► Si autor es técnico → Notificar creador
             │
             └─► Si autor es usuario → Notificar técnico
             
Tipo: ticket_comentario
Prioridad: media
```

---

## Configuración Requerida

### 1. Variables de Entorno (.env)

Copiar `.env.example` a `.env` y completar:

```bash
# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=app_password  # Contraseña de aplicación, no la normal

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxxx...
TWILIO_AUTH_TOKEN=xxxx...
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

### 2. Configurar Gmail (recomendado)

1. Habilitar autenticación de dos factores
2. Generar contraseña de aplicación (16 caracteres)
3. Usar esa contraseña en `EMAIL_HOST_PASSWORD`

[Instrucciones oficiales](https://support.google.com/accounts/answer/185833)

### 3. Configurar Twilio (opcional, para WhatsApp)

1. Crear cuenta en [twilio.com](https://www.twilio.com)
2. Verificar número de WhatsApp de prueba
3. Obtener Account SID y Auth Token
4. Configurar número de WhatsApp Business
5. Rellenar en .env

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
# o específicamente:
pip install twilio
```

### 5. Permisos del usuario

Para recibir notificaciones, el usuario debe:

1. Ir a **Mi Perfil**
2. Habilitar "Notificaciones por Email" ✓
3. Habilitar "Notificaciones por WhatsApp" ✓ (opcional)
4. Ingresar número con formato: `+57301234567`

---

## Endpoints API

### Obtener todas las notificaciones

```
GET /api/notificaciones/?limite=20

Respuesta:
{
    "notificaciones": [
        {
            "id": 1,
            "titulo": "Ticket Asignado",
            "tipo": "ticket_asignado",
            "prioridad": "alta",
            "leida": false,
            "fecha_creacion": "2025-11-25T10:30:00",
            "ticket_id": 42,
            "enlace": "/tickets/42/"
        }
    ],
    "total": 1
}
```

### Obtener solo nuevas (no leídas)

```
GET /api/notificaciones/nuevas/?limite=5
```

### Marcar como leída

```
POST /api/notificaciones/<id>/marcar-leida/

Respuesta:
{
    "success": true,
    "mensaje": "Notificación marcada como leída"
}
```

### Marcar todas como leídas

```
POST /api/notificaciones/marcar-todas-leidas/
```

---

## Interfaz de Usuario

### Campana de Notificaciones (Navbar)

- **Icono**: 🔔 con badge de contador rojo
- **Hover**: Escala de animación
- **Click**: Abre dropdown
- **Dropdown**:
  - Encabezado con opción "Marcar todas"
  - Hasta 5 notificaciones recientes
  - Emojis según tipo (📋, 💬, ✅, etc.)
  - Badge de prioridad (colores)
  - Botón ✕ para marcar como leída
  - Enlace a página completa

### Página Completa (/notificaciones/)

- **Filtros**: Tipo, Prioridad, Estado (leída/sin leer)
- **Estadísticas**: Total de notificaciones
- **Cards**: Información detallada por notificación
- **Paginación**: 20 por página
- **Info de entrega**: Íconos de Email ✉️ y WhatsApp 💬 si se enviaron
- **Acciones**: Ver más, Marcar como leída, Marcar todas

---

## Funciones Principales

### crear_notificacion_completa()

```python
from tickets.services import crear_notificacion_completa

crear_notificacion_completa(
    usuario=user,
    ticket=ticket,
    tipo='ticket_asignado',  # Ver TIPOS_NOTIFICACION
    prioridad='critica'       # baja, media, alta, critica
)

# Automáticamente:
# 1. Crea registro en BD
# 2. Envía email si usuario habilitó
# 3. Envía WhatsApp si es crítico + usuario habilitó + tiene número
# 4. Registra logs
```

### marcar_notificacion_leida()

```python
from tickets.services import marcar_notificacion_leida

marcar_notificacion_leida(notificacion)
# Marca como leída y guarda timestamp
```

### obtener_notificaciones_no_leidas()

```python
from tickets.services import obtener_notificaciones_no_leidas

nuevas = obtener_notificaciones_no_leidas(user, limite=5)
# Retorna QuerySet de las 5 más recientes sin leer
```

---

## Archivos Modificados/Creados

### Nuevos:
- `tickets/services.py` - Lógica de notificaciones (270 líneas)
- `tickets/static/tickets/js/notificaciones.js` - Polling y UI (400 líneas)
- `tickets/templates/tickets/lista_notificaciones.html` - Página de notificaciones
- `tickets/templates/emails/notificacion.html` - Template de email HTML
- `.env.example` - Variables de entorno

### Modificados:
- `tickets/models.py` - Modelo Notificacion + campos en PerfilUsuario
- `tickets/views.py` - API endpoints + integración en vistas
- `tickets/urls.py` - Rutas de API + página de notificaciones
- `tickets/admin.py` - Registro de modelo en admin
- `tickets/static/tickets/css/common.css` - Estilos de campana y dropdown
- `tickets/templates/tickets/base_intranet.html` - Campana en navbar
- `requirements.txt` - twilio==9.8.7
- `ticket_coyahue/settings.py` - Configuración EMAIL y TWILIO
- Migration 0008 - Tabla Notificacion + campos en PerfilUsuario

---

## Flujo de Uso

### 1. Primer acceso (Usuario)

```
→ Ir a Mi Perfil
→ Habilitar "Notificaciones por Email"
→ (Opcional) Habilitar WhatsApp + ingresar número
→ Guardar
```

### 2. Crear ticket (Administrador)

```
→ Todos los admins reciben notificación en:
  ├─ Email (inmediato)
  ├─ WhatsApp (si crítico)
  └─ Badge web (30 seg máximo)
```

### 3. Asignar ticket (Administrador)

```
→ Técnico recibe notificación:
  ├─ Email (inmediato)
  ├─ WhatsApp (si crítico)
  └─ Banner web en navbar
```

### 4. Agregar comentario (Cualquiera)

```
→ Técnico ↔ Usuario intercambian comentarios
→ Ambos reciben notificaciones
→ Pueden marcar como leídas en dropdown o página
```

### 5. Resolver ticket (Técnico)

```
→ Usuario creador recibe:
  ├─ Notificación "Ticket Resuelto"
  └─ Puede revisar en /notificaciones/
```

---

## Troubleshooting

### Email no se envía

**Problema**: `SMTPAuthenticationError`

**Solución**:
- Verificar `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en .env
- Si usa Gmail: usar contraseña de aplicación (no la normal)
- Verificar que 2FA está habilitado en Gmail

### WhatsApp no funciona

**Problema**: `TwilioRestException`

**Solución**:
- Verificar `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN`
- Verificar formato `TWILIO_WHATSAPP_NUMBER` (debe empezar con `whatsapp:`)
- Verificar que el número del usuario tenga formato `+57301234567`
- Verificar que la cuenta Twilio está en estado activo

### Notificaciones no aparecen

**Problema**: Dropdown vacío, sin badge

**Solución**:
- Abrir consola del navegador (F12) y revisar errores de red
- Verificar que `/api/notificaciones/nuevas/` responde correctamente
- Verificar que `notificaciones.js` está cargando
- Revisar cookies (CSRF token)

### Base de datos desactualizada

**Problema**: Errores de atributo en Notificacion

**Solución**:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Monitoreo

### Ver notificaciones creadas

```bash
# En Django shell
python manage.py shell

from tickets.models import Notificacion
Notificacion.objects.all().count()

# Ver últimas 5
Notificacion.objects.order_by('-fecha_creacion')[:5]

# Ver no leídas
Notificacion.objects.filter(leida=False).count()

# Ver fallos de email
Notificacion.objects.filter(email_enviado=False)
```

### Ver logs

```bash
# En archivo logs/tickets.log
tail -f logs/tickets.log
```

---

## Seguridad

✅ **CSRF Protection**: Todos los endpoints POST requieren token CSRF
✅ **Permisos**: Solo usuarios autenticados pueden acceder
✅ **Rate Limiting**: No implementado (considerar para producción)
✅ **Variables sensibles**: En .env (nunca commitear)
✅ **Validación**: Todos los inputs validados antes de usar

---

## Próximas Mejoras

- [ ] Rate limiting en API
- [ ] Webhooks de Twilio para confirmación de entrega
- [ ] WebSocket para actualizaciones en tiempo real (sin polling)
- [ ] Plantillas personalizables de email
- [ ] Notificaciones por SMS (Twilio)
- [ ] Preferencias por tipo de notificación
- [ ] Digest diario/semanal
- [ ] Búsqueda en notificaciones
- [ ] Exportar notificaciones

---

## Contacto / Soporte

Para problemas o preguntas sobre el sistema de notificaciones:
- Revisar logs en `logs/tickets.log`
- Consultar Django debug toolbar en desarrollo
- Verificar credenciales en .env

---

**Última actualización**: Noviembre 2025
**Versión**: 1.0.0
**Estado**: Producción ✅
