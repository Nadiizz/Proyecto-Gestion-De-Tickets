# 🎫 Sistema de Gestión de Tickets - Grupo Coyahue

![Django](https://img.shields.io/badge/Django-5.2.6-green)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![License](https://img.shields.io/badge/License-Privado-red)

Sistema integral de gestión de tickets desarrollado para el Grupo Coyahue, que permite administrar solicitudes de soporte, incidencias y problemas de manera eficiente con seguimiento completo, métricas avanzadas y sistema de SLA automatizado.

## 📋 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Instalación](#-instalación)
- [Configuración](#️-configuración)
- [Uso del Sistema](#-uso-del-sistema)
- [Roles y Permisos](#-roles-y-permisos)
- [Documentación](#-documentación)
- [Estructura del Proyecto](#-estructura-del-proyecto)

## ✨ Características Principales

### 🎯 Gestión de Tickets
- **Creación de tickets** con categorización por tipo (Incidencia, Solicitud, Problema, Cambio)
- **Asignación automática y manual** de tickets a técnicos
- **Estados del ciclo de vida**: Pendiente, En Progreso, Resuelto, Cerrado, Tiempo Excedido
- **Prioridades configurables**: Baja, Media, Alta, Crítica
- **Adjuntar archivos** (imágenes, documentos) a tickets y comentarios
- **Sistema de comentarios** con historial completo
- **Página "Mis Tickets"** para usuarios finales

### 📊 Sistema de Métricas y Analytics
- **Dashboard de métricas** con 12+ KPIs clave
- **Análisis de rendimiento**: Volumen, tiempos de respuesta y resolución
- **Métricas de calidad**: CSAT (satisfacción del cliente con sistema de estrellas)
- **Eficiencia por técnico**: Rendimiento individual con calificaciones promedio
- **Análisis de causas raíz**: Tickets por tipo, área y prioridad
- **Gráficos interactivos**: Visualización de tendencias temporales
- **Filtros por período**: 7 días, 30 días, 90 días, año, todo el tiempo

### ⏱️ Sistema SLA (Service Level Agreement)
- **SLA automático** basado en prioridad del ticket
- **Tiempos límite configurables** por administradores
- **Monitoreo en tiempo real** del estado del SLA
- **Cierre automático** de tickets que exceden el tiempo límite
- **Comando de gestión** para verificación periódica
- **Indicadores visuales** de cumplimiento de SLA

### 🔔 Sistema de Notificaciones Multi-canal
- **Email automático**: Notificaciones SMTP profesionales en HTML
- **WhatsApp**: Integración con Twilio para mensajes instantáneos
- **Notificaciones web**: Sistema de polling en tiempo real (30 segundos)
- **Campana interactiva**: Indicador visual en la barra de navegación
- **Preferencias personalizables**: Los usuarios pueden configurar qué notificaciones recibir
- **Notificaciones inteligentes**:
  - ✅ Crear ticket → Notifica a administradores
  - ✅ Asignar ticket → Notifica al técnico asignado
  - ✅ Cambiar estado → Notifica al usuario creador
  - ✅ Comentario nuevo → Notifica a involucrados
- **Historial completo**: Listado de todas las notificaciones con filtros
- **Gestión de lectura**: Marcar como leído/no leído
- **API REST**: Endpoints para gestión programática

### 🔐 Sistema de Autenticación
- **Registro validado** con dominios corporativos (@coyahue.com, @coyahue.cl)
- **Roles y permisos**: Administrador, Técnico, Usuario
- **Autenticación segura** con Django Auth
- **Gestión de grupos** automática

### 🎨 Interfaz de Usuario
- **Diseño responsive** con Bootstrap 4
- **Animaciones suaves** con CSS3
- **Tema corporativo** personalizado
- **Navegación intuitiva** con sidebar persistente
- **Formularios validados** con crispy-forms

## 🛠️ Tecnologías Utilizadas

### Backend
- **Django 5.2.6** - Framework web principal
- **Python 3.13** - Lenguaje de programación
- **PostgreSQL** - Base de datos relacional
- **psycopg2** - Adaptador PostgreSQL
- **python-decouple** - Gestión de variables de entorno
- **Twilio 9.8.7** - Integración WhatsApp

### Frontend
- **Bootstrap 4** - Framework CSS
- **django-crispy-forms** - Renderizado de formularios
- **crispy-bootstrap4** - Plantillas Bootstrap 4
- **JavaScript ES6** - Interactividad del cliente
- **CSS3** - Estilos personalizados con animaciones

### Procesamiento de Datos
- **Pandas 2.3.2** - Análisis y manipulación de datos
- **NumPy 2.3.3** - Computación numérica
- **Openpyxl 3.1.5** - Exportación a Excel

### Generación de Reportes
- **ReportLab 4.4.3** - Generación de PDFs
- **Pillow 11.3.0** - Procesamiento de imágenes

### Herramientas de Desarrollo
- **Django Widget Tweaks** - Personalización de widgets
- **pytz** - Manejo de zonas horarias
- **six** - Compatibilidad Python 2/3

## 📦 Instalación

### Prerequisitos
- Python 3.13 o superior
- PostgreSQL 12 o superior
- pip (gestor de paquetes de Python)
- Virtualenv (recomendado)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets.git
cd Proyecto-Gestion-De-Tickets
```

2. **Crear entorno virtual**
```bash
python -m venv env
```

3. **Activar entorno virtual**
```bash
# Windows
env\Scripts\activate

# Linux/Mac
source env/bin/activate
```

4. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

5. **Configurar base de datos PostgreSQL**
```sql
CREATE DATABASE tickets_db;
CREATE USER tickets_user WITH PASSWORD 'tu_password';
ALTER ROLE tickets_user SET client_encoding TO 'utf8';
ALTER ROLE tickets_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tickets_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tickets_db TO tickets_user;
```

6. **Configurar variables de entorno**
Crear archivo `.env` en la raíz del proyecto:
```env
SECRET_KEY=tu-clave-secreta-super-segura
DEBUG=True
DATABASE_NAME=tickets_db
DATABASE_USER=tickets_user
DATABASE_PASSWORD=tu_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

7. **Aplicar migraciones**
```bash
python manage.py migrate
```

8. **Crear superusuario**
```bash
python manage.py createsuperuser
```

9. **Crear grupos de usuarios**
```bash
python manage.py shell
```
```python
from django.contrib.auth.models import Group
Group.objects.create(name='Administrador')
Group.objects.create(name='Técnico')
Group.objects.create(name='Usuario')
exit()
```

10. **Ejecutar servidor de desarrollo**
```bash
python manage.py runserver
```

Acceder a: `http://127.0.0.1:8000`

## ⚙️ Configuración

### Configuración de SLA Automático

Para que el sistema verifique automáticamente los SLAs vencidos:

**Windows (Programador de Tareas):**
1. Abrir "Programador de tareas"
2. Crear tarea básica: "Verificar SLA Tickets"
3. Ejecutar cada hora:
   - Programa: `ruta\al\env\Scripts\python.exe`
   - Argumentos: `manage.py verificar_sla`
   - Directorio: `ruta\al\proyecto`

**Linux/Mac (Crontab):**
```bash
crontab -e
```
Agregar:
```
0 * * * * cd /ruta/proyecto && /ruta/env/bin/python manage.py verificar_sla
```

### Configuración de Email (Opcional)
En `settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu-email@coyahue.com'
EMAIL_HOST_PASSWORD = 'tu-password'
```

### Configuración de Notificaciones Multi-canal

**Email SMTP** - Configurar en `.env`:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=tu-email@gmail.com
```

**WhatsApp via Twilio** - Configurar en `.env`:
```env
TWILIO_ACCOUNT_SID=tu-account-sid
TWILIO_AUTH_TOKEN=tu-auth-token
TWILIO_WHATSAPP_NUMBER=+14155552671
```

**Preferencias de Notificación** - Los usuarios pueden configurar en su perfil:
- Notificaciones por email
- Notificaciones por WhatsApp
- Notificaciones web

## 🚀 Uso del Sistema

### Para Usuarios
1. **Registrarse** con correo corporativo (@coyahue.com o @coyahue.cl)
2. **Crear tickets** describiendo el problema
3. **Seleccionar tipo** de solicitud (Incidencia, Solicitud, Problema, Cambio)
4. **Adjuntar archivos** si es necesario
5. **Seguir el estado** del ticket en "Mis Tickets"
6. **Calificar el servicio** una vez resuelto (1-5 estrellas)

### Para Técnicos
1. **Ver tickets asignados** en el dashboard
2. **Cambiar estado** de los tickets
3. **Agregar comentarios** y actualizaciones
4. **Adjuntar archivos** de resolución
5. **Monitorear SLA** de cada ticket

### Para Administradores
1. **Asignar tickets** a técnicos
2. **Configurar prioridades**
3. **Establecer SLA personalizado** por ticket
4. **Ver métricas completas** del sistema
5. **Analizar rendimiento** de técnicos
6. **Exportar reportes**

## 👥 Roles y Permisos

| Rol | Permisos |
|-----|----------|
| **Usuario** | Crear tickets, ver sus propios tickets, comentar, calificar |
| **Técnico** | Ver todos los tickets, cambiar estados, comentar, ver detalles |
| **Administrador** | Todos los permisos + asignar tickets, ver métricas, configurar SLA |

## 📚 Documentación

La documentación completa del proyecto se encuentra en la carpeta `/doc`:

- **[Arquitectura del Sistema](doc/01_ARQUITECTURA.md)** - Diseño y estructura general
- **[Modelos de Datos](doc/02_MODELOS.md)** - Explicación detallada de la base de datos
- **[Vistas y Controladores](doc/03_VISTAS.md)** - Lógica de negocio
- **[Templates y Frontend](doc/04_TEMPLATES.md)** - Interfaz de usuario
- **[Sistema de Métricas y SLA](doc/METRICAS_SLA_README.md)** - Analytics y monitoreo
- **[Guía de Desarrollo](doc/05_DESARROLLO.md)** - Para desarrolladores
- **[API y Comandos](doc/06_API_COMANDOS.md)** - Referencia técnica
- **[Sistema de Notificaciones](doc/SISTEMA_NOTIFICACIONES.md)** - Documentación completa del sistema multi-canal
- **[Inicio Rápido Notificaciones](INICIO_RAPIDO_NOTIFICACIONES.md)** - Guía de configuración rápida

## 📁 Estructura del Proyecto

```
Proyecto-Gestion-De-Tickets/
├── doc/                          # Documentación completa
│   ├── SISTEMA_NOTIFICACIONES.md # Sistema de notificaciones
│   └── ...                       # Otros documentos
├── env/                          # Entorno virtual (no en Git)
├── ticket_coyahue/              # Configuración Django
│   ├── settings.py              # Configuración principal
│   ├── urls.py                  # URLs principales
│   └── wsgi.py                  # Configuración WSGI
├── tickets/                      # Aplicación principal
│   ├── management/              # Comandos personalizados
│   │   └── commands/
│   │       └── verificar_sla.py # Comando SLA
│   ├── migrations/              # Migraciones de BD
│   │   └── 0008_*.py            # Migración notificaciones
│   ├── static/                  # Archivos estáticos
│   │   └── tickets/
│   │       ├── css/
│   │       │   └── common.css   # Estilos notificaciones
│   │       ├── js/
│   │       │   └── notificaciones.js  # Polling real-time
│   │       └── img/
│   ├── templates/               # Plantillas HTML
│   │   ├── emails/
│   │   │   └── notificacion.html # Template email
│   │   ├── registration/
│   │   └── tickets/
│   │       └── lista_notificaciones.html # Historial
│   ├── admin.py                 # Configuración admin
│   ├── forms.py                 # Formularios
│   ├── models.py                # Modelos (incluye Notificacion)
│   ├── services.py              # Servicios notificaciones
│   ├── urls.py                  # URLs de la app
│   └── views.py                 # Vistas + API endpoints
├── .env                         # Variables de entorno (no en Git)
├── .gitignore                   # Archivos ignorados
├── manage.py                    # CLI de Django
├── README.md                    # Este archivo
├── requirements.txt             # Dependencias Python
├── INICIO_RAPIDO_NOTIFICACIONES.md
├── RESUMEN_NOTIFICACIONES.md
└── CHANGELOG_NOTIFICACIONES.md
```

## 🔒 Seguridad

- ✅ Secret key en variables de entorno
- ✅ DEBUG=False en producción
- ✅ CSRF protection habilitado
- ✅ Validación de correos corporativos
- ✅ Autenticación requerida en todas las vistas
- ✅ Control de acceso basado en roles
- ✅ Archivos sensibles en .gitignore

## 🤝 Contribución

Este es un proyecto privado del Grupo Coyahue. Para contribuir:
1. Crear una rama feature: `git checkout -b feature/nueva-funcionalidad`
2. Hacer commit de cambios: `git commit -m 'Agregar nueva funcionalidad'`
3. Push a la rama: `git push origin feature/nueva-funcionalidad`
4. Crear Pull Request

## 📄 Licencia

Proyecto privado - © 2025 Grupo Coyahue. Todos los derechos reservados.

## 📞 Contacto

- **Desarrollador**: Nadiizz
- **Organización**: Grupo Coyahue
- **Repositorio**: https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets

---

**Última actualización**: Diciembre 2025
