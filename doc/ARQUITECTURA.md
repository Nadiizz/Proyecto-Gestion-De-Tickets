# 🏗️ Arquitectura y Estructura del Proyecto

## Visión General

Este proyecto implementa un **Sistema de Gestión de Tickets** usando el patrón **MVT (Model-View-Template)** de Django.

---

## Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Backend | Django | 5.2.6 |
| Base de Datos | PostgreSQL | 14+ |
| Frontend | HTML/CSS/JS | - |
| CSS Framework | Bootstrap 4 | (via crispy) |
| Email | Gmail SMTP | - |
| WhatsApp | Twilio API | - |
| Autenticación | Django Auth | Built-in |

---

## Estructura de Directorios

```
Proyecto-Gestion-De-Tickets/
│
├── manage.py                    # Script de gestión Django
├── requirements.txt             # Dependencias Python
├── .env                         # Variables de entorno (no en git)
│
├── ticket_coyahue/              # 📦 Configuración del proyecto
│   ├── __init__.py
│   ├── settings.py              # Configuraciones principales
│   ├── urls.py                  # URLs raíz
│   ├── wsgi.py                  # Configuración WSGI
│   └── asgi.py                  # Configuración ASGI
│
├── tickets/                     # 📦 Aplicación principal
│   ├── __init__.py
│   ├── admin.py                 # Configuración Django Admin
│   ├── apps.py                  # Configuración de la app
│   ├── models.py                # Modelos de datos (ORM)
│   ├── views.py                 # Vistas/Controladores
│   ├── urls.py                  # URLs de la aplicación
│   ├── forms.py                 # Formularios
│   ├── services.py              # Servicios (notificaciones)
│   ├── context_processors.py    # Procesadores de contexto
│   ├── tests.py                 # Tests unitarios
│   │
│   ├── migrations/              # Migraciones de BD
│   │   ├── 0001_initial.py
│   │   └── ...
│   │
│   ├── management/              # Comandos personalizados
│   │   └── commands/
│   │       └── poblar_faqs.py
│   │
│   ├── templates/               # 📄 Templates HTML
│   │   ├── registration/        # Login, registro
│   │   ├── tickets/             # Vistas de tickets
│   │   ├── admin/               # Panel admin personalizado
│   │   └── emails/              # Templates de email
│   │
│   └── static/                  # 📁 Archivos estáticos
│       └── tickets/
│           ├── css/
│           ├── js/
│           └── img/
│
├── media/                       # 📁 Archivos subidos
│   ├── tickets/archivos/
│   ├── comentarios/archivos/
│   ├── fotos_perfil/
│   └── faqs/imagenes/
│
├── logs/                        # 📁 Archivos de log
│   └── ticket_coyahue.log
│
├── static/                      # 📁 Estáticos globales
│
├── doc/                         # 📁 Documentación
│   ├── README.md
│   ├── INSTALACION.md
│   └── ...
│
└── env/                         # 📁 Entorno virtual (no en git)
```

---

## Patrón MVT (Model-View-Template)

```
┌─────────────────────────────────────────────────────────────┐
│                         USUARIO                              │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      URL DISPATCHER                          │
│                      (urls.py)                               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         VIEW                                 │
│                      (views.py)                              │
│                                                              │
│   - Recibe request                                           │
│   - Procesa lógica de negocio                               │
│   - Interactúa con Models                                    │
│   - Retorna response (render template)                       │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌───────────────────────────────┐
│         MODEL            │  │         TEMPLATE              │
│       (models.py)        │  │    (templates/*.html)         │
│                          │  │                               │
│   - Define estructura    │  │   - HTML con Django tags      │
│   - Interactúa con BD    │  │   - Presenta datos al usuario │
│   - Validaciones         │  │   - Herencia de templates     │
└──────────────────────────┘  └───────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│      BASE DE DATOS       │
│      (PostgreSQL)        │
└──────────────────────────┘
```

---

## Modelos (models.py)

### Diagrama de Entidades

```
┌─────────────────┐     ┌─────────────────┐
│   auth_user     │     │  RolPersonalizado│
│   (Django)      │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │ 1:1                   │ 1:N
         ▼                       │
┌─────────────────┐              │
│ PerfilUsuario   │◄─────────────┘
└────────┬────────┘
         │
         │ 1:N (creador)
         │ 1:N (asignado_a)
         ▼
┌─────────────────┐     ┌─────────────────┐
│     Ticket      │────►│   Categoria     │
│                 │     └────────┬────────┘
│                 │              │ 1:N
│                 │              ▼
│                 │     ┌─────────────────┐
│                 │────►│  Subcategoria   │
└────────┬────────┘     └─────────────────┘
         │
    ┌────┼────┬────────────┐
    │    │    │            │
    ▼    ▼    ▼            ▼
┌──────┐ ┌──────┐ ┌──────────────┐ ┌─────────────┐
│Comen-│ │Histo-│ │ArchivoTicket │ │Notificacion │
│tario │ │rial  │ └──────────────┘ └─────────────┘
└──┬───┘ └──────┘
   │
   ▼
┌──────────────────┐
│ArchivoComentario │
└──────────────────┘
```

### Modelos Principales

| Modelo | Descripción | Campos Clave |
|--------|-------------|--------------|
| `Ticket` | Entidad central | titulo, estado, prioridad, creador, asignado_a |
| `Comentario` | Comunicación | ticket, autor, mensaje |
| `HistorialEstado` | Auditoría | ticket, estado_anterior, estado_nuevo |
| `Notificacion` | Alertas | usuario, ticket, tipo, leida |
| `PerfilUsuario` | Extensión User | telefono, rol_personalizado, notificaciones |
| `RolPersonalizado` | Permisos | puede_ver_metricas, puede_asignar, etc. |

---

## Vistas (views.py)

### Organización

```python
# ============================================
# FUNCIONES DE VERIFICACIÓN DE PERMISOS
# ============================================
def es_admin(user): ...
def es_tecnico(user): ...
def puede_ver_metricas(user): ...

# ============================================
# VISTAS DE TICKETS
# ============================================
@login_required
def ticket_list(request): ...

@login_required
def ticket_create(request): ...

@login_required
def ticket_detalle(request, ticket_id): ...

# ============================================
# VISTAS DE GESTIÓN (Admin Panel)
# ============================================
@login_required
def admin_panel(request): ...

@login_required
def admin_usuarios(request): ...

# ============================================
# API ENDPOINTS (JSON)
# ============================================
@login_required
def api_notificaciones(request): ...
```

### Flujo de una Vista Típica

```python
@login_required
def ticket_create(request):
    # 1. Verificar permisos adicionales si necesario
    usuario_es_admin = es_admin(request.user)
    
    # 2. Procesar POST
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            # 3. Guardar en BD
            ticket = form.save(commit=False)
            ticket.creador = request.user
            ticket.save()
            
            # 4. Lógica adicional (SLA, notificaciones)
            ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
            ticket.save()
            
            # 5. Enviar notificaciones
            for admin in administradores:
                crear_notificacion_completa(admin, ticket, 'ticket_creado')
            
            # 6. Logging
            logger.info(f'Ticket #{ticket.id} creado')
            
            # 7. Mensaje y redirect
            messages.success(request, 'Ticket creado exitosamente.')
            return redirect('ticket_list')
    
    # 3. GET: Mostrar formulario vacío
    else:
        form = TicketForm()
    
    # 4. Renderizar template
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'es_admin': usuario_es_admin,
    })
```

---

## Servicios (services.py)

Encapsula lógica de negocio compleja, especialmente notificaciones.

```python
# Función principal
def crear_notificacion_completa(usuario, ticket, tipo, prioridad='media'):
    # 1. Crear registro en BD
    notificacion = Notificacion.objects.create(...)
    
    # 2. Enviar por Email
    if perfil.notificaciones_email:
        enviar_email(usuario, notificacion, ticket)
    
    # 3. Enviar por WhatsApp (solo críticos)
    if prioridad == 'critica' and perfil.notificaciones_whatsapp:
        enviar_whatsapp(usuario, notificacion, ticket)
    
    return notificacion
```

---

## Templates

### Herencia de Templates

```
base.html (estructura general)
    │
    ├── base_intranet.html (layout con sidebar)
    │       │
    │       ├── ticket_list.html
    │       ├── ticket_detalle.html
    │       ├── metricas.html
    │       └── admin/*.html
    │
    └── registration/
            ├── login.html
            └── registro.html
```

### Ejemplo de Herencia

```html
<!-- base_intranet.html -->
{% extends 'tickets/base.html' %}

{% block content %}
<div class="intranet-layout">
    <aside class="sidebar">
        {% include 'tickets/partials/sidebar.html' %}
    </aside>
    <main class="main-content">
        {% block main_content %}{% endblock %}
    </main>
</div>
{% endblock %}

<!-- ticket_list.html -->
{% extends 'tickets/base_intranet.html' %}

{% block main_content %}
    <h1>Lista de Tickets</h1>
    {% for ticket in tickets %}
        ...
    {% endfor %}
{% endblock %}
```

---

## Archivos Estáticos

### Estructura CSS

```
static/tickets/css/
├── styles.css           # Estilos globales
├── ticket_detalle.css   # Estilos específicos
├── metricas.css
├── login.css
└── admin.css
```

### Convención de Nombres

- **Clases generales:** `.btn`, `.card`, `.badge`
- **Específicas de módulo:** `.ticket-card`, `.comment-item`
- **Estados:** `.status-pendiente`, `.priority-critica`

---

## Configuración (settings.py)

### Secciones Principales

```python
# ============================================
# DJANGO CORE
# ============================================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
INSTALLED_APPS = [...]
MIDDLEWARE = [...]

# ============================================
# BASE DE DATOS
# ============================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        ...
    }
}

# ============================================
# CONSTANTES DE APLICACIÓN
# ============================================
GRUPO_ADMINISTRADOR = 'Administrador'
TICKETS_POR_PAGINA = 10
MAX_FILE_SIZE = 10 * 1024 * 1024

# ============================================
# EMAIL
# ============================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'

# ============================================
# TWILIO (WhatsApp)
# ============================================
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
```

---

## Logging

### Configuración

```python
LOGGING = {
    'handlers': {
        'file': {
            'filename': 'logs/ticket_coyahue.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
        },
        'console': {...},
    },
    'loggers': {
        'tickets': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}
```

### Uso en Código

```python
import logging
logger = logging.getLogger('tickets')

# En vistas/servicios
logger.info(f'Ticket #{ticket.id} creado por {user.username}')
logger.warning(f'SLA excedido para ticket #{ticket.id}')
logger.error(f'Error enviando email: {str(e)}')
```

### Formato de Log

```
INFO 2024-12-08 10:30:00 views Ticket #123 creado por admin
WARNING 2024-12-08 14:00:00 views Ticket #456 reabierto por usuario1
ERROR 2024-12-08 15:30:00 services Error enviando email: Connection refused
```

---

## Seguridad

### Medidas Implementadas

| Medida | Descripción |
|--------|-------------|
| CSRF Protection | Token en formularios |
| XSS Prevention | Auto-escape en templates |
| SQL Injection | ORM de Django |
| Session Security | Cookies HTTP-only |
| Password Hashing | PBKDF2 por defecto |

### Para Producción

```python
# settings.py (producción)
DEBUG = False
SECRET_KEY = 'clave-segura-50-caracteres'
ALLOWED_HOSTS = ['tudominio.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```
