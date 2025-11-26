# 🚀 GUÍA RÁPIDA - SISTEMA DE GESTIÓN DE TICKETS v1.1.0

**¿Quieres conocer rápidamente el proyecto?** Empieza aquí.

---

## 🎯 ¿Qué es este proyecto?

Un **Sistema de Gestión de Tickets** profesional para Grupo Coyahue que permite:
- 📋 Crear y gestionar tickets de soporte
- 👥 Asignar tickets a técnicos
- 📊 Ver métricas y KPIs
- 🔔 Recibir notificaciones en tiempo real
- ⭐ Calificar calidad del servicio

---

## 🏃 Inicio Rápido (5 minutos)

### 1. Primero, Lee El Índice Maestro
```
doc/INDICE_MAESTRO.md  ← EMPIEZA AQUÍ
```

Este archivo te guiará según tu rol:
- **Desarrollador?** → Sigue ruta Developers
- **Admin/Operaciones?** → Sigue ruta Admins
- **Notificaciones?** → Sigue ruta Notificaciones

### 2. Luego, Estudia los Documentos Técnicos
```
doc/01_ARQUITECTURA.md      → Entender la estructura
doc/02_MODELOS.md           → Base de datos
doc/03_VISTAS.md            → Lógica de negocio
doc/04_TEMPLATES.md         → Frontend
doc/06_API_COMANDOS.md      → APIs y comandos
```

### 3. Para Notificaciones (NEW)
```
doc/SISTEMA_NOTIFICACIONES.md → Sistema completo
doc/03_VISTAS.md (sección NEW) → Vistas API
doc/06_API_COMANDOS.md (sección NEW) → Endpoints REST
```

---

## 🏗️ Arquitectura en 30 Segundos

```
┌─────────────────────────────────────────┐
│         FRONTEND (HTML/CSS/JS)          │
│    Bootstrap 4 + Django Templates       │
└──────────────┬──────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────┐
│      DJANGO VIEWS (Python)              │
│    13 vistas + 5 vistas API NEW         │
└──────────────┬──────────────────────────┘
               │ ORM
┌──────────────▼──────────────────────────┐
│       DJANGO MODELS (ORM)               │
│  8 modelos incluyendo Notificacion NEW  │
└──────────────┬──────────────────────────┘
               │ SQL
┌──────────────▼──────────────────────────┐
│    PostgreSQL DATABASE                  │
│  8 migraciones, 8 tablas principales    │
└─────────────────────────────────────────┘
```

---

## 📊 Componentes Principales

### 1. **Tickets** (Core)
- Crear tickets de soporte
- Asignar a técnicos
- Cambiar estado
- Agregar comentarios
- Subir archivos

### 2. **Usuarios** (Roles)
- Administrador
- Técnico (Support)
- Usuario (Cliente)

### 3. **Métricas** (Analytics)
- 12+ KPIs
- Dashboard visual
- Análisis por período
- Reportes de eficiencia

### 4. **SLA** (Seguimiento)
- Tiempos límite automáticos
- Alertas de vencimiento
- Histórico de cumplimiento

### 5. **Notificaciones** (NEW)
- Email
- WhatsApp
- Web (tiempo real)
- Preferencias por usuario

---

## 🔑 Rutas Principales

| URL | Propósito | Acceso |
|-----|-----------|--------|
| `/` | Inicio | Todos |
| `/tickets/` | Lista de tickets | Todos (filtrada por rol) |
| `/crear-ticket/` | Crear ticket | Usuarios |
| `/ticket/<id>/` | Detalles ticket | Relacionados + Admins |
| `/metricas/` | Dashboard | Admin |
| `/notificaciones/` | Mis notificaciones | Todos |
| `/admin/` | Panel admin | Admin |

---

## 🔐 Control de Acceso

```
┌─────────────┐    ┌──────────────┐    ┌────────┐
│ ADMIN       │    │ TÉCNICO      │    │ USUARIO│
├─────────────┤    ├──────────────┤    ├────────┤
│ Ver todos   │    │ Ver asignados│    │ Ver    │
│ Crear       │    │ Crear        │    │ suyos  │
│ Editar todo │    │ Editar suyos │    │ Crear  │
│ Eliminar    │    │ Comentar     │    │Comentar│
│ Asignar     │    │ Cambiar est. │    │        │
│ Métricas    │    │              │    │        │
│ Admin panel │    │              │    │        │
└─────────────┘    └──────────────┘    └────────┘
```

---

## 📱 APIs REST (NEW - v1.1.0)

### Obtener Notificaciones
```bash
curl -X GET "http://localhost:8000/api/notificaciones/" \
  -H "Cookie: sessionid=..."
```

**Respuesta:**
```json
{
  "total": 5,
  "notificaciones": [
    {
      "id": 1,
      "titulo": "Ticket Asignado",
      "tipo": "ticket_asignado",
      "leida": false
    }
  ]
}
```

### Marcar como Leída
```bash
curl -X POST "http://localhost:8000/api/notificaciones/1/marcar-leida/" \
  -H "Cookie: sessionid=..."
```

*Ver `/doc/06_API_COMANDOS.md` para más endpoints*

---

## 🛠️ Teknolohías

| Componente | Tecnología |
|-----------|-----------|
| Backend | Django 5.2.6 |
| Frontend | Bootstrap 4 |
| Base de Datos | PostgreSQL |
| ORM | Django ORM |
| Forms | django-crispy-forms |
| APIs | Django Views (JSON) |
| JavaScript | ES6 + Fetch API |
| Notificaciones | Email, WhatsApp, Web |

---

## 📁 Estructura de Carpetas Clave

```
project/
├── doc/                          ← DOCUMENTACIÓN
│   ├── INDICE_MAESTRO.md        ← START HERE
│   ├── 01-06_TECNICO.md         ← Documentación técnica
│   └── SISTEMA_NOTIFICACIONES.md ← NEW
├── tickets/                      ← APLICACIÓN DJANGO
│   ├── models.py                ← Base de datos (ORM)
│   ├── views.py                 ← Lógica (+ 5 nuevas vistas)
│   ├── forms.py                 ← Formularios
│   ├── templates/               ← HTML (+ nueva template)
│   ├── static/                  ← CSS, JS, Imágenes
│   └── migrations/              ← 8 migraciones BD
├── ticket_coyahue/              ← CONFIGURACIÓN
│   ├── settings.py              ← Configuraciones
│   ├── urls.py                  ← Rutas
│   └── wsgi.py                  ← Producción
├── manage.py                     ← CLI de Django
├── requirements.txt              ← Dependencias
└── README.md                     ← Info general
```

---

## 🚀 Primeros Pasos (Development)

### 1. Clone the Repository
```bash
git clone https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets.git
cd Proyecto-Gestion-De-Tickets
```

### 2. Setup Virtual Environment
```bash
python -m venv env
env\Scripts\Activate.ps1  # Windows PowerShell
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Database
```bash
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

**Abre**: `http://localhost:8000`

---

## 📚 Documentación por Rol

### 👨‍💻 Para Desarrolladores
1. `doc/01_ARQUITECTURA.md` - Diseño general
2. `doc/02_MODELOS.md` - ORM y BD
3. `doc/03_VISTAS.md` - Vistas y lógica
4. `doc/05_DESARROLLO.md` - Setup y desarrollo
5. `doc/06_API_COMANDOS.md` - Comandos y APIs

### 👨‍✈️ Para Administradores
1. `doc/METRICAS_SLA_README.md` - Dashboard
2. `doc/GUIA_SISTEMA_SLA.md` - Configuración
3. `doc/01_ARQUITECTURA.md` - Visión general

### 📱 Para Notificaciones
1. `doc/SISTEMA_NOTIFICACIONES.md` - Completo
2. `doc/03_VISTAS.md` (sección NEW) - Vistas API
3. `doc/06_API_COMANDOS.md` (sección NEW) - Endpoints

---

## 🎓 Conceptos Clave

### Ticket
```
Unidad de trabajo que representa:
- Problema reportado por usuario
- Asignado a un técnico
- Progresa por estados (pendiente → resuelto → cerrado)
- Tiene comentarios y archivos adjuntos
```

### Estado del Ticket
```
pendiente → en_progreso → resuelto → cerrado
            ↓
        tiempo_excedido (si se vence SLA)
```

### SLA (Service Level Agreement)
```
Tiempo máximo para responder según prioridad:
- Crítica: 1 hora
- Alta: 4 horas
- Media: 1 día
- Baja: 3 días
```

### Notificación (NEW)
```
Aviso automático que se envía a usuario cuando:
- Ticket es creado
- Ticket es asignado
- Alguien comenta
- Estado cambia
- Ticket es resuelto

Canales: Email, WhatsApp, Web
```

---

## 🐛 Debugging

### Ver Logs
```bash
# Todos los logs
cat logs/app.log

# Últimas 50 líneas
tail -50 logs/app.log
```

### Django Shell
```bash
python manage.py shell

from tickets.models import Ticket
tickets = Ticket.objects.all()
print(tickets.count())
```

### Ver Queries SQL
```bash
python manage.py shell

from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as queries:
    # Tu código aquí
    pass

for q in queries:
    print(q['sql'])
```

---

## 📞 Contacto y Soporte

- **Proyecto**: Sistema de Gestión de Tickets
- **Organización**: Grupo Coyahue
- **Versión**: 1.1.0
- **Estado**: ✅ Listo para Producción
- **Documentación**: `/doc/`
- **GitHub**: https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets

---

## 🎯 Próximos Pasos

**Eres nuevo?**
1. Lee `doc/INDICE_MAESTRO.md` según tu rol
2. Explora la documentación técnica
3. Realiza el setup de desarrollo
4. Crea un ticket de prueba

**¿Necesitas ayuda?**
- Revisión de código: Ver `doc/05_DESARROLLO.md`
- Problemas: Buscar en `doc/CORRECCIONES_MALAS_PRACTICAS.md`
- APIs: Consultar `doc/06_API_COMANDOS.md`

---

## ✅ Checklist de Validación

- [ ] He leído `doc/INDICE_MAESTRO.md`
- [ ] He revisado documentación según mi rol
- [ ] He hecho setup local
- [ ] He creado un usuario de prueba
- [ ] He creado un ticket de prueba
- [ ] He probado las notificaciones
- [ ] He revisado las APIs

---

**¿Listo para comenzar?** → Abre `doc/INDICE_MAESTRO.md`

---

*Documento de Inicio Rápido v1.1.0*  
*Última actualización: Enero 2025*  
*¿Preguntas? Revisa la documentación completa en `/doc/`*
