# 📚 ÍNDICE MAESTRO DE DOCUMENTACIÓN

**Sistema de Gestión de Tickets - Grupo Coyahue**  
**Versión:** 1.0.0  
**Última actualización:** 25 de Noviembre 2025

---

## 🎯 GUÍA DE NAVEGACIÓN RÁPIDA

### Para Desarrolladores
1. Comienza con: [01_ARQUITECTURA.md](01_ARQUITECTURA.md) - Entiende la estructura general
2. Luego: [02_MODELOS.md](02_MODELOS.md) - Aprende los datos
3. Después: [03_VISTAS.md](03_VISTAS.md) - Entiende la lógica
4. Finalmente: [05_DESARROLLO.md](05_DESARROLLO.md) - Comienza a desarrollar

### Para Admins/Ops
1. Comienza con: [README.md](README.md) - Visión general
2. Luego: [METRICAS_SLA_README.md](METRICAS_SLA_README.md) - Cómo funciona el dashboard
3. Después: [GUIA_SISTEMA_SLA.md](GUIA_SISTEMA_SLA.md) - Configurar SLA

### Para Notificaciones
1. Lee: [SISTEMA_NOTIFICACIONES.md](SISTEMA_NOTIFICACIONES.md) - En `/doc` (raíz del proyecto)
2. Luego: [../CHANGELOG_NOTIFICACIONES.md](../CHANGELOG_NOTIFICACIONES.md) - Historial
3. Referencia: [06_API_COMANDOS.md](06_API_COMANDOS.md) - APIs disponibles

---

## 📖 DOCUMENTOS COMPLETOS

### Técnico-Arquitectónico (Desarrollo)

| Documento | Ubicación | Propósito | Audiencia |
|-----------|-----------|----------|-----------|
| **01_ARQUITECTURA.md** | `/doc/` | Diseño del sistema completo | Arquitectos, Dev Leads |
| **02_MODELOS.md** | `/doc/` | Esquema de BD y ORM | Developers |
| **03_VISTAS.md** | `/doc/` | Lógica de negocio y vistas | Developers |
| **04_TEMPLATES.md** | `/doc/` | Frontend y templates | Frontend Devs |
| **05_DESARROLLO.md** | `/doc/` | Guía de desarrollo local | Developers |
| **06_API_COMANDOS.md** | `/doc/` | APIs REST y comandos CLI | Developers, DevOps |

### Dominio-Específico

| Documento | Ubicación | Propósito | Audiencia |
|-----------|-----------|----------|-----------|
| **SISTEMA_NOTIFICACIONES.md** | `/doc/` | Sistema multi-canal de notificaciones | Developers, Admins |
| **METRICAS_SLA_README.md** | `/doc/` | Dashboard de métricas | Admins, KPI Team |
| **GUIA_SISTEMA_SLA.md** | `/doc/` | Cómo configurar SLA | Admins, Project Managers |

### Especializados (Referencia)

| Documento | Ubicación | Propósito | Audiencia |
|-----------|-----------|----------|-----------|
| **CORRECCIONES_MALAS_PRACTICAS.md** | `/doc/` | Bugs corregidos e implementación | Code Review, QA |
| **MEJORAS_IMPLEMENTADAS.md** | `/doc/` | Features agregadas | Project Managers |

### Cambios y Seguimiento (Raíz del Proyecto)

| Documento | Ubicación | Propósito | Audiencia |
|-----------|-----------|----------|-----------|
| **RESUMEN_NOTIFICACIONES.md** | `/` (raíz) | Resumen de notificaciones | Todos |
| **CHANGELOG_NOTIFICACIONES.md** | `/` (raíz) | Historial de cambios | Todos |
| **INICIO_RAPIDO_NOTIFICACIONES.md** | `/` (raíz) | Quick start para notificaciones | Developers |
| **REVISION_FINAL.md** | `/` (raíz) | Reporte de revisión completa | Stakeholders |
| **RESUMEN_EJECUTIVO.md** | `/` (raíz) | Para ejecutivos | C-Level, Managers |
| **PRE_DEPLOY_CHECKLIST.md** | `/` (raíz) | Verificación pre-deployment | DevOps, QA |

---

## 🗺️ MAPA DE CONTENIDOS

### 1. ARQUITECTURA Y DISEÑO

**01_ARQUITECTURA.md** (354 líneas)
```
├─ Visión General
├─ Arquitectura de Alto Nivel (4 capas)
├─ Componentes Principales
│  ├─ Capa de Presentación
│  ├─ Capa de Aplicación
│  ├─ Capa de Dominio
│  └─ Capa de Persistencia
├─ Flujo de Datos
├─ Patrones de Diseño
├─ Consideraciones de Escalabilidad
└─ Seguridad
```

### 2. BASE DE DATOS

**02_MODELOS.md** (495 líneas)
```
├─ Diagrama de Relaciones
├─ Modelos Principales
│  ├─ Ticket (18 campos)
│  ├─ Comentario
│  ├─ ArchivoTicket
│  ├─ HistorialEstado
│  ├─ RolPersonalizado
│  ├─ PerfilUsuario
│  └─ Notificacion (16 campos) ✨ NEW
├─ Métodos de Modelos
├─ Consultas ORM
└─ Índices y Performance
```

### 3. LÓGICA DE NEGOCIO

**03_VISTAS.md** (620 líneas)
```
├─ Vista General
├─ Autenticación y Registro
├─ Gestión de Tickets
│  ├─ ticket_list()
│  ├─ ticket_create()
│  ├─ ticket_detalle()
│  ├─ asignar_ticket()
│  └─ cambiar_estado()
├─ Métricas y Analytics
├─ Sistema de Permisos
└─ Manejo de Errores
```

### 4. FRONTEND

**04_TEMPLATES.md** (Variables páginas)
```
├─ Estructura de Templates
├─ Templates Principales
│  ├─ base_intranet.html
│  ├─ ticket_list.html
│  ├─ ticket_detalle.html
│  ├─ cambiar_estado.html
│  └─ lista_notificaciones.html ✨ NEW
├─ CSS y Estilos
├─ JavaScript
│  └─ notificaciones.js ✨ NEW
└─ Componentes Reutilizables
```

### 5. GUÍAS Y REFERENCIAS

**05_DESARROLLO.md** (Setup local)
```
├─ Requisitos
├─ Instalación
├─ Configuración
├─ Estructura de Carpetas
├─ Convenciones de Código
└─ Debugging
```

**06_API_COMANDOS.md** (695 líneas)
```
├─ Comandos de Django
├─ Endpoints REST
│  ├─ GET /api/notificaciones/
│  ├─ GET /api/notificaciones/nuevas/
│  ├─ POST /api/notificaciones/<id>/marcar-leida/
│  └─ POST /api/notificaciones/marcar-todas-leidas/ ✨ NEW
├─ Ejemplos cURL
└─ Testing de APIs
```

### 6. SISTEMAS ESPECIALIZADOS

**SISTEMA_NOTIFICACIONES.md** (465 líneas)
```
├─ Descripción General
├─ Características Implementadas
│  ├─ Modelo Notificacion
│  ├─ Canales (Email, WhatsApp, Web)
│  └─ Puntos de Integración
├─ Flujos de Notificación (4)
├─ Configuración
│  ├─ Email SMTP
│  ├─ WhatsApp Twilio
│  └─ Web Polling
├─ Ejemplos de Código
├─ Troubleshooting
└─ Limitaciones y Futuro
```

**METRICAS_SLA_README.md** (~200 líneas)
```
├─ Dashboard de Métricas
├─ KPIs Principales (12+)
├─ Sistema SLA
├─ Gráficos y Visualizaciones
├─ Filtros y Análisis
└─ Exportar Reportes
```

**GUIA_SISTEMA_SLA.md** (~300 líneas)
```
├─ Concepto de SLA
├─ Configuración Automática
├─ Tiempos Límite por Prioridad
├─ Monitoreo en Tiempo Real
├─ Alertas y Acciones
└─ Escalaciones
```

---

## 📌 INFORMACIÓN CLAVE

### Stack Tecnológico
- **Backend:** Django 5.2.6, Python 3.13.5
- **BD:** PostgreSQL (10+ tablas)
- **Email:** SMTP (Gmail/Custom)
- **WhatsApp:** Twilio REST API
- **Frontend:** Bootstrap 4, JavaScript ES6

### Modelos Principales
- **Ticket**: 18 campos (incluyendo SLA)
- **Notificacion**: 16 campos (Email, WhatsApp, Web) ✨
- **User**: Django Auth
- **PerfilUsuario**: Extensión de User + prefs notificaciones

### APIs Nuevas (Notificaciones)
- ✅ GET /api/notificaciones/ - Todas
- ✅ GET /api/notificaciones/nuevas/ - No leídas
- ✅ POST /api/notificaciones/<id>/marcar-leida/
- ✅ POST /api/notificaciones/marcar-todas-leidas/

### Estado de Implementación
- ✅ Sistema completo funcional
- ✅ 100% documentado
- ✅ Error handling implementado
- ✅ Listo para producción

---

## 🔗 REFERENCIAS CRUZADAS

### Si necesitas entender...
- **"Cómo crear un ticket"** → Lee: 03_VISTAS.md + 04_TEMPLATES.md
- **"Cómo funciona el SLA"** → Lee: GUIA_SISTEMA_SLA.md + 02_MODELOS.md
- **"Cómo enviar notificaciones"** → Lee: SISTEMA_NOTIFICACIONES.md + 06_API_COMANDOS.md
- **"Arquitectura general"** → Lee: 01_ARQUITECTURA.md
- **"Setup del proyecto"** → Lee: 05_DESARROLLO.md
- **"Detalles de la BD"** → Lee: 02_MODELOS.md
- **"Seguridad del sistema"** → Lee: 01_ARQUITECTURA.md (última sección)

---

## 🚀 QUICK LINKS

### Desarrollo Local
```bash
# Setup inicial
python -m venv env
env\Scripts\activate  # Windows
source env/bin/activate  # Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Deployment
- Seguir: [PRE_DEPLOY_CHECKLIST.md](../PRE_DEPLOY_CHECKLIST.md)
- Paso a paso en: [REVISION_FINAL.md](../REVISION_FINAL.md)

### Testing
- API: Usar ejemplos en [06_API_COMANDOS.md](06_API_COMANDOS.md)
- Notificaciones: Ver [SISTEMA_NOTIFICACIONES.md](SISTEMA_NOTIFICACIONES.md)

---

## 📊 ESTADÍSTICAS DE DOCUMENTACIÓN

| Métrica | Valor |
|---------|-------|
| **Total de documentos** | 15 archivos |
| **Líneas de documentación** | 4,000+ líneas |
| **Tamaño total** | ~200 KB |
| **Diagramas ASCII** | 20+ |
| **Ejemplos de código** | 50+ |
| **Tablas de referencia** | 25+ |

---

## ✅ CHECKLIST DE DOCUMENTACIÓN

- [x] Arquitectura documentada
- [x] Modelos documentados
- [x] Vistas documentadas
- [x] Templates documentados
- [x] Guía de desarrollo
- [x] APIs documentadas
- [x] Sistema de notificaciones completo
- [x] Métricas y SLA documentado
- [x] Guías de configuración
- [x] Changelog de mejoras
- [x] Reporte de revisión
- [x] Checklist pre-deploy
- [x] Resumen ejecutivo
- [x] Ejemplos de código
- [x] Troubleshooting

---

## 📞 SOPORTE

Para preguntas sobre:
- **Desarrollo:** Consulta 05_DESARROLLO.md
- **Arquitectura:** Consulta 01_ARQUITECTURA.md
- **Notificaciones:** Consulta SISTEMA_NOTIFICACIONES.md
- **Deploy:** Consulta PRE_DEPLOY_CHECKLIST.md
- **Bugs reportados:** Consulta CORRECCIONES_MALAS_PRACTICAS.md

---

**Generado:** 25/11/2025  
**Versión:** 1.0.0  
**Estado:** ✅ Completo
