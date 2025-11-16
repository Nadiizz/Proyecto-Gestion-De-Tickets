# Arquitectura del Sistema - Gestión de Tickets Coyahue

## 📐 Visión General

El Sistema de Gestión de Tickets está construido siguiendo el patrón arquitectónico **MVT (Model-View-Template)** de Django, con una clara separación de responsabilidades y siguiendo los principios SOLID.

## 🏗️ Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Templates │  │    CSS     │  │ JavaScript │            │
│  │   HTML     │  │  Bootstrap │  │    ES6     │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE APLICACIÓN                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   Views    │  │   Forms    │  │    URLs    │            │
│  │  (Logic)   │  │(Validation)│  │  (Routing) │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE DOMINIO                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   Models   │  │  Managers  │  │ Business   │            │
│  │  (Entities)│  │   (ORM)    │  │   Logic    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PERSISTENCIA                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ PostgreSQL │  │  Archivos  │  │   Cache    │            │
│  │    ORM     │  │   Estáticos│  │  (Futuro)  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Componentes Principales

### 1. **Capa de Presentación (Templates)**
**Ubicación**: `tickets/templates/`

**Responsabilidad**: Renderizar la interfaz de usuario

**Componentes**:
- `base_intranet.html` - Template base con sidebar y navegación
- `base_login.html` - Template para autenticación
- `ticket_list.html` - Lista de tickets con filtros
- `ticket_detalle.html` - Vista detallada de ticket
- `ticket_form.html` - Formulario de creación
- `metricas.html` - Dashboard de analytics
- `mis_tickets.html` - Vista personal del usuario

**Tecnologías**: Django Template Language, Bootstrap 4, CSS3, JavaScript

### 2. **Capa de Aplicación (Views & Forms)**
**Ubicación**: `tickets/views.py`, `tickets/forms.py`

**Responsabilidad**: Procesar solicitudes y coordinar la lógica de negocio

**Vistas Principales**:
- `ticket_list()` - Lista y búsqueda de tickets
- `crear_ticket()` - Creación de nuevos tickets
- `ticket_detalle()` - Detalles y comentarios
- `asignar_ticket()` - Asignación a técnicos
- `cambiar_estado()` - Gestión de estados
- `metricas()` - Análisis y reportes
- `calificar_ticket()` - Sistema de ratings

**Formularios**:
- `TicketForm` - Validación de creación de tickets
- `CustomUserCreationForm` - Registro con validación de dominio
- `BusquedaTicketForm` - Filtros avanzados

**Características**:
- ✅ Decoradores de autenticación (`@login_required`)
- ✅ Control de acceso por roles (`@user_passes_test`)
- ✅ Validación en servidor
- ✅ Manejo de errores con `get_object_or_404`
- ✅ Optimización de queries (querysets reutilizables)

### 3. **Capa de Dominio (Models)**
**Ubicación**: `tickets/models.py`

**Responsabilidad**: Definir entidades del negocio y reglas de dominio

**Entidades Principales**:

#### **Ticket** (Entidad Principal)
```python
- Estado del ciclo de vida (pendiente → en_progreso → resuelto → cerrado)
- Sistema de prioridades (baja → media → alta → crítica)
- Tipos de solicitud (incidencia, solicitud, problema, cambio)
- Tracking de SLA (tiempo_limite_resolucion)
- Sistema de ratings (calificacion_satisfaccion 1-5)
- Relaciones: creador, asignado_a
```

#### **Comentario**
```python
- Sistema de comunicación interno
- Autor y timestamp
- Relación con Ticket
```

#### **HistorialEstado**
```python
- Auditoría de cambios de estado
- Trazabilidad completa
- Quién y cuándo cambió el estado
```

#### **ArchivoTicket / ArchivoComentario**
```python
- Gestión de adjuntos
- Validación de tipos de archivo
- Almacenamiento organizado
```

**Métodos de Negocio**:
- `calcular_tiempo_primera_respuesta()` - Métrica de SLA
- `calcular_tiempo_resolucion()` - Tiempo total de resolución
- `calcular_tiempo_limite_sla()` - Cálculo automático de deadline
- `dias_desde_creacion()` - Antigüedad del ticket

### 4. **Capa de Persistencia**
**Ubicación**: PostgreSQL Database

**Esquema de Base de Datos**:
```sql
tickets_ticket (Principal)
├── tickets_comentario (1:N)
├── tickets_historialestado (1:N)
├── tickets_archivoticket (1:N)
└── auth_user (FK: creador, asignado_a)

tickets_comentario
└── tickets_archivocomentario (1:N)
```

**Optimizaciones**:
- Índices en campos de búsqueda frecuente
- Relaciones con `select_related` y `prefetch_related`
- Queries agregadas con `annotate` y `aggregate`

## 🔄 Flujo de Datos

### Creación de Ticket
```
1. Usuario → GET /nuevo/
2. View renderiza TicketForm
3. Usuario completa formulario → POST /nuevo/
4. Form valida datos
5. View crea Ticket + ArchivoTicket
6. Redirect a ticket_list
```

### Asignación de Ticket
```
1. Admin → GET /asignar/<id>/
2. View obtiene Ticket y lista de técnicos
3. Admin selecciona técnico + SLA → POST
4. View actualiza Ticket (asignado_a, tiempo_limite)
5. Se crea HistorialEstado
6. Redirect a ticket_list
```

### Sistema de Métricas
```
1. Admin → GET /metricas/?dias=30
2. View define queryset base con filtro de fecha
3. Se ejecutan múltiples agregaciones:
   - Count() para volúmenes
   - Avg() para promedios
   - TruncDate() para series temporales
4. Se calculan KPIs derivados
5. View renderiza con context de métricas
6. JavaScript aplica animaciones y gráficos
```

## 🔐 Seguridad

### Autenticación y Autorización
```python
# Niveles de acceso
Usuario Regular:
  - Puede crear tickets
  - Ve solo sus propios tickets
  - Puede comentar y calificar

Técnico:
  - Ve todos los tickets
  - Puede cambiar estados
  - Puede comentar

Administrador:
  - Todos los permisos de Técnico +
  - Puede asignar tickets
  - Puede configurar SLA
  - Accede a métricas
```

### Validaciones de Seguridad
- ✅ CSRF Protection en todos los formularios
- ✅ Validación de dominio en registro (@coyahue.com/cl)
- ✅ Control de acceso en cada vista
- ✅ Sanitización de entrada de usuario
- ✅ SECRET_KEY en variables de entorno
- ✅ DEBUG=False en producción

## 📊 Sistema de Métricas

### Arquitectura de Analytics
```
┌─────────────────────────────────────┐
│       Vista metricas()              │
│                                     │
│  1. Filtro por período (días)      │
│  2. Queryset base reutilizable      │
│  3. Agregaciones en BD              │
│  4. Cálculos derivados en Python   │
│  5. Preparación de datos para JS   │
└─────────────────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│       Template metricas.html        │
│                                     │
│  - Cards con animaciones CSS        │
│  - Gráficos de barras dinámicos    │
│  - Tabla de eficiencia técnicos    │
│  - Selector de período             │
└─────────────────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│       JavaScript (Frontend)         │
│                                     │
│  - Aplicar anchos a gráficos       │
│  - Animaciones de entrada          │
│  - Interactividad                  │
└─────────────────────────────────────┘
```

### KPIs Calculados
1. **Volumen**: Count de tickets por estado
2. **Tiempos**: Promedio de listas calculadas en Python
3. **Satisfacción**: Avg de calificaciones
4. **Eficiencia**: Agregación con filter en annotate
5. **Tendencias**: TruncDate + Group By día

## ⚙️ Sistema SLA

### Arquitectura de Monitoreo
```
┌──────────────────────────────────────┐
│   Comando: verificar_sla.py          │
│                                      │
│  1. Query tickets con SLA activo     │
│  2. Verificar si tiempo_limite pasó  │
│  3. Actualizar estado a              │
│     'tiempo_excedido'                │
│  4. Registrar en historial           │
└──────────────────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│   Programador de Tareas              │
│   (Cron/Task Scheduler)              │
│                                      │
│  Ejecuta cada hora                   │
└──────────────────────────────────────┘
```

### Cálculo de SLA
```python
# Por prioridad (default)
CRITICA:  4 horas
ALTA:     8 horas
MEDIA:    24 horas
BAJA:     48 horas

# Personalizado
Admin especifica horas manualmente
```

## 🎨 Patrones de Diseño Implementados

### 1. **MVT (Model-View-Template)**
- Separación clara de responsabilidades
- Models: Lógica de negocio
- Views: Controladores
- Templates: Presentación

### 2. **Repository Pattern** (via Django ORM)
- Models actúan como repositorios
- Abstracción de la capa de datos
- Queries reutilizables

### 3. **Decorator Pattern**
- `@login_required` para autenticación
- `@user_passes_test` para autorización
- Composición de comportamientos

### 4. **Template Method**
- Templates base con blocks
- Herencia de plantillas
- Reutilización de estructura

### 5. **Strategy Pattern**
- Diferentes estrategias de cálculo de SLA
- Por prioridad vs personalizado

## 📈 Escalabilidad

### Optimizaciones Actuales
- ✅ Querysets optimizados (select_related, prefetch_related)
- ✅ Índices en campos frecuentes
- ✅ Paginación en listados
- ✅ Static files cacheables
- ✅ Agregaciones en BD (no en Python)

### Mejoras Futuras
- 🔄 Sistema de cache (Redis)
- 🔄 Procesamiento asíncrono (Celery)
- 🔄 CDN para archivos estáticos
- 🔄 Compresión de respuestas
- 🔄 API REST (Django REST Framework)

## 🔧 Configuración del Entorno

### Desarrollo
```python
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
DATABASES = local PostgreSQL
```

### Producción
```python
DEBUG = False
ALLOWED_HOSTS = ['dominio.coyahue.com']
DATABASES = production PostgreSQL
STATIC_ROOT configurado
MEDIA_ROOT configurado
HTTPS habilitado
```

---

**Siguiente**: [Modelos de Datos →](02_MODELOS.md)
