# 📋 Sistema de Gestión de Tickets - Coyahue

## Documentación Técnica del Proyecto

**Versión:** 1.0  
**Última actualización:** Diciembre 2025
**Framework:** Django 5.2.6  
**Base de datos:** PostgreSQL

---

## 📁 Índice

1. [Arquitectura del Sistema](#arquitectura-del-sistema)
2. [Modelo de Datos](#modelo-de-datos)
3. [Sistema de Roles y Permisos](#sistema-de-roles-y-permisos)
4. [Flujo de Estados de Tickets](#flujo-de-estados-de-tickets)
5. [Sistema de Notificaciones](#sistema-de-notificaciones)
6. [SLA y Métricas](#sla-y-métricas)
7. [Configuración del Entorno](#configuración-del-entorno)
8. [API Endpoints](#api-endpoints)

---

## 🏗️ Arquitectura del Sistema

```
Proyecto-Gestion-De-Tickets/
├── ticket_coyahue/          # Configuración principal Django
│   ├── settings.py          # Configuraciones del proyecto
│   ├── urls.py              # URLs principales
│   └── wsgi.py              # Configuración WSGI
├── tickets/                 # Aplicación principal
│   ├── models.py            # Modelos de datos
│   ├── views.py             # Controladores (vistas)
│   ├── services.py          # Servicios de notificaciones
│   ├── forms.py             # Formularios
│   ├── urls.py              # Rutas de la aplicación
│   ├── context_processors.py # Procesadores de contexto
│   ├── templates/           # Templates HTML
│   └── static/              # Archivos estáticos (CSS, JS)
├── media/                   # Archivos subidos por usuarios
├── logs/                    # Archivos de log
└── doc/                     # Documentación
```

---

## 📊 Modelo de Datos

### Entidades Principales

#### 1. **Ticket**
Entidad central del sistema que representa una solicitud de soporte.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `titulo` | CharField(200) | Título del ticket |
| `descripcion` | TextField | Descripción detallada |
| `estado` | CharField | Estado actual (ver estados) |
| `prioridad` | CharField | baja, media, alta, critica |
| `tipo` | CharField | incidencia, solicitud, problema, cambio |
| `categoria` | FK → Categoria | Categoría principal |
| `subcategoria` | FK → Subcategoria | Subcategoría específica |
| `creador` | FK → User | Usuario que creó el ticket |
| `asignado_a` | FK → User | Técnico asignado |
| `fecha_creacion` | DateTime | Fecha de creación |
| `fecha_cierre` | DateTime | Fecha de resolución |
| `tiempo_limite_resolucion` | DateTime | Deadline SLA |
| `calificacion_satisfaccion` | Integer(1-5) | Rating del usuario |

#### 2. **PerfilUsuario**
Extiende el modelo User de Django con información adicional.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user` | OneToOne → User | Usuario Django |
| `telefono` | CharField | Teléfono de contacto |
| `departamento` | CharField | Departamento |
| `cargo` | CharField | Cargo en la empresa |
| `foto_perfil` | ImageField | Avatar del usuario |
| `rol_personalizado` | FK → RolPersonalizado | Rol con permisos |
| `notificaciones_email` | Boolean | Recibir emails |
| `notificaciones_whatsapp` | Boolean | Recibir WhatsApp |
| `numero_whatsapp` | CharField | Número WhatsApp (+56...) |

#### 3. **Notificacion**
Sistema de notificaciones multi-canal.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `usuario` | FK → User | Destinatario |
| `ticket` | FK → Ticket | Ticket relacionado |
| `tipo` | CharField | Tipo de notificación |
| `prioridad` | CharField | Prioridad de la notificación |
| `titulo` | CharField | Título |
| `mensaje` | TextField | Contenido |
| `email_enviado` | Boolean | Estado envío email |
| `whatsapp_enviado` | Boolean | Estado envío WhatsApp |
| `leida` | Boolean | Si fue leída en web |

---

## 👥 Sistema de Roles y Permisos

### Grupos Tradicionales

| Grupo | Permisos |
|-------|----------|
| **Administrador** | Acceso total al sistema |
| **Técnico** | Gestionar tickets asignados, ver todos los tickets |
| **Usuario** | Crear tickets, ver sus propios tickets |

### Roles Personalizados (RolPersonalizado)

Permiten crear roles híbridos con permisos específicos:

```python
permisos_disponibles = {
    'puede_ver_metricas': False,
    'puede_ver_todos_tickets': False,
    'puede_asignar_tickets': False,
    'puede_cambiar_estado': False,
    'puede_gestionar_usuarios': False,
    'puede_crear_roles': False,
}
```

### Jerarquía de Permisos

```
Administrador
    ├── Gestionar usuarios
    ├── Crear/editar roles
    ├── Asignar tickets
    ├── Ver métricas
    └── Todo lo de Técnico

Técnico
    ├── Ver todos los tickets
    ├── Autoasignarse tickets
    ├── Cambiar estado de tickets
    └── Todo lo de Usuario

Usuario
    ├── Crear tickets
    ├── Ver sus propios tickets
    ├── Agregar comentarios
    └── Calificar tickets resueltos
```

---

## 🔄 Flujo de Estados de Tickets

### Estados Disponibles

| Estado | Descripción | Emoji |
|--------|-------------|-------|
| `pendiente` | Ticket nuevo sin asignar | ⏳ |
| `en_progreso` | Técnico trabajando | 🟡 |
| `resuelto` | Solucionado, pendiente de cierre | 🟢 |
| `cerrado` | Ticket finalizado | ⚫ |
| `tiempo_excedido` | SLA vencido | ⚠️ |

### Transiciones Permitidas

```
pendiente ──────────► en_progreso
    │                      │
    │                      ▼
    └────────────────► resuelto ──────► cerrado
                          │
                          ▼
                      pendiente (reapertura)

tiempo_excedido ────► pendiente / en_progreso
```

### Matriz de Transiciones

```python
TRANSICIONES_ESTADO_VALIDAS = {
    'pendiente': ['en_progreso', 'asignado'],
    'asignado': ['en_progreso', 'cerrado'],
    'en_progreso': ['resuelto', 'pendiente', 'en_progreso'],
    'resuelto': ['cerrado', 'pendiente'],
    'cerrado': [],  # Solo admin puede reabrir
    'tiempo_excedido': ['pendiente', 'en_progreso'],
}
```

---

## 📧 Sistema de Notificaciones

### Canales Disponibles

1. **Email** - Para todas las notificaciones (si está habilitado)
2. **WhatsApp** - Solo para tickets **CRÍTICOS** (vía Twilio)
3. **Web** - Notificaciones en tiempo real en la aplicación

### Tipos de Notificaciones

| Tipo | Descripción | Email | WhatsApp |
|------|-------------|-------|----------|
| `ticket_creado` | Nuevo ticket creado | ✅ | ❌ |
| `ticket_asignado` | Ticket asignado a técnico | ✅ | Solo críticos |
| `ticket_comentario` | Nuevo comentario | ✅ | ❌ |
| `ticket_resuelto` | Ticket resuelto | ✅ | ❌ |
| `ticket_cerrado` | Ticket cerrado | ✅ | ❌ |
| `estado_cambio` | Cambio de estado | ✅ | ❌ |

### Configuración de Email (Gmail SMTP)

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password
DEFAULT_FROM_EMAIL=noreply@coyahue.com
```

### Configuración de WhatsApp (Twilio)

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

> **Nota:** Los usuarios deben enviar primero "join <sandbox>" al número de Twilio para activar el sandbox.

## ⏱️ SLA y Métricas

### Tiempos de SLA por Prioridad

| Prioridad | Tiempo Límite | Descripción |
|-----------|---------------|-------------|
| **Crítica** | 4 horas | Emergencias, sistemas caídos |
| **Alta** | 8 horas | Problemas importantes |
| **Media** | 24 horas | Solicitudes normales |
| **Baja** | 48 horas | Mejoras, consultas |

### Cálculo de SLA

```python
def calcular_tiempo_limite_sla(self, horas_personalizadas=None):
    if horas_personalizadas:
        return self.fecha_creacion + timedelta(hours=int(horas_personalizadas))
    
    horas_por_prioridad = {
        'critica': 4,
        'alta': 8,
        'media': 24,
        'baja': 48,
    }
    horas = horas_por_prioridad.get(self.prioridad, 24)
    return self.fecha_creacion + timedelta(hours=horas)
```

### Métricas Disponibles

- **Tiempo promedio de primera respuesta**
- **Tiempo promedio de resolución**
- **Tasa de cumplimiento de SLA**
- **Tickets por técnico**
- **Tickets por categoría/tipo**
- **Satisfacción del cliente (CSAT)**

---

## ⚙️ Configuración del Entorno

### Archivo `.env`

```env
# Django
SECRET_KEY=django-insecure-xxxxxxxxxxxxxxxxxxxxx
DEBUG=True
DB_PASSWORD=tu_password_postgres

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=app_password_de_16_caracteres
DEFAULT_FROM_EMAIL=Sistema Tickets <noreply@coyahue.com>

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Requisitos del Sistema

```txt
Django>=5.2.6
psycopg2-binary
python-decouple
crispy-bootstrap4
django-crispy-forms
twilio
Pillow
```

### Base de Datos

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ticket_coyahue',
        'USER': 'postgres',
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

## 🔌 API Endpoints

### Tickets

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/` | Lista de tickets |
| GET | `/ticket/<id>/` | Detalle de ticket |
| POST | `/nuevo/` | Crear ticket |
| POST | `/asignar/<id>/` | Asignar ticket |
| POST | `/autoasignar/<id>/` | Autoasignarse ticket |
| POST | `/estado/<id>/` | Cambiar estado |
| POST | `/calificar/<id>/` | Calificar ticket |

### Notificaciones (API JSON)

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/notificaciones/` | Todas las notificaciones |
| GET | `/api/notificaciones/nuevas/` | Solo no leídas |
| POST | `/api/notificaciones/<id>/marcar-leida/` | Marcar como leída |
| POST | `/api/notificaciones/marcar-todas-leidas/` | Marcar todas |

### Subcategorías (API JSON)

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/subcategorias/<categoria_id>/` | Subcategorías de una categoría |

### Panel de Administración

| URL | Descripción |
|-----|-------------|
| `/admin-panel/` | Dashboard principal |
| `/admin-panel/usuarios/` | Gestión de usuarios |
| `/admin-panel/roles/` | Gestión de roles |
| `/admin-panel/categorias/` | Gestión de categorías |
| `/admin-panel/faqs/` | Gestión de FAQs |

---

## 🚀 Comandos Útiles

```bash
# Activar entorno virtual
.\env\Scripts\activate

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor de desarrollo
python manage.py runserver

# Verificar proyecto
python manage.py check

# Poblar FAQs de ejemplo
python manage.py poblar_faqs
```

---

## 📝 Notas Importantes

1. **Dominios de email**: Solo se permiten correos `@coyahue.com` o `@coyahue.cl` para registro.

2. **WhatsApp Sandbox**: Los usuarios deben activar el sandbox de Twilio antes de recibir mensajes.

3. **SLA Automático**: El sistema verifica cada hora los tickets que excedieron el SLA y los marca automáticamente.

4. **Archivos Permitidos**: PDF, DOC, DOCX, TXT, JPG, JPEG, PNG, GIF, XLSX, XLS, ZIP (máx. 10 MB).

5. **Videos en FAQs**: Se pueden embeber videos de YouTube y Vimeo en las respuestas de FAQ.

---

**© 2024 Sistema de Gestión de Tickets - Coyahue**

**Última actualización**: Diciembre 2025
