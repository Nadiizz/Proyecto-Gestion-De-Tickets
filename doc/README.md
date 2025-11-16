# 📚 Documentación del Sistema de Gestión de Tickets

Bienvenido a la documentación completa del Sistema de Gestión de Tickets desarrollado para Grupo Coyahue.

## 📖 Índice de Documentación

### 1. [Arquitectura del Sistema](01_ARQUITECTURA.md)
Descripción completa de la arquitectura MVT, componentes principales, flujo de datos, patrones de diseño y sistema de seguridad.

**Contenido:**
- Visión general de la arquitectura
- Diagrama de capas (Presentación, Aplicación, Dominio, Persistencia)
- Componentes principales y responsabilidades
- Flujo de datos en operaciones clave
- Sistema de métricas y analytics
- Sistema de SLA y monitoreo
- Patrones de diseño implementados
- Consideraciones de escalabilidad

---

### 2. [Modelos de Datos](02_MODELOS.md)
Documentación detallada de todos los modelos, campos, relaciones y métodos del sistema.

**Contenido:**
- Diagrama de relaciones de la base de datos
- **Modelo Ticket**: 18 campos con documentación completa
  * Campos de identificación
  * Campos de clasificación (estado, prioridad, tipo)
  * Campos de asignación y fechas
  * Campos SLA y tracking
  * Campos de satisfacción
  * Métodos del modelo (calcular tiempos, SLA, etc.)
- **Modelo Comentario**: Sistema de comunicación
- **Modelo ArchivoTicket/ArchivoComentario**: Gestión de adjuntos
- **Modelo HistorialEstado**: Auditoría de cambios
- Consultas comunes del ORM

---

### 3. [Vistas y Controladores](03_VISTAS.md)
Explicación detallada de todas las vistas (13 vistas principales), lógica de negocio y controladores.

**Contenido:**
- Vista general del controlador
- **Autenticación**: registro_usuario()
- **Gestión de Tickets**:
  * ticket_list() - Lista con filtros y paginación
  * crear_ticket() - Creación con archivos
  * ticket_detalle() - Vista detallada con comentarios
  * asignar_ticket() - Asignación a técnicos
  * cambiar_estado() - Gestión de estados
- **Sistema de Métricas**: metricas()
  * 12+ KPIs calculados
  * Análisis de rendimiento, calidad y eficiencia
  * Gráficos y visualizaciones
- **Calificaciones**: calificar_ticket()
- **Vista Personal**: mis_tickets()
- Funciones auxiliares de permisos

---

### 4. [Templates y Frontend](04_TEMPLATES.md)
Documentación de la estructura de templates, componentes HTML, CSS y JavaScript.

**Contenido:**
- Estructura de templates
- **Templates Base**:
  * base_intranet.html - Con sidebar y navegación
  * base_login.html - Para autenticación
- **Templates de Tickets**:
  * ticket_list.html - Lista con filtros y búsqueda
  * ticket_form.html - Formulario de creación con crispy-forms
  * ticket_detalle.html - Vista completa con comentarios, historial, archivos
  * asignar_ticket.html - Asignación y SLA
  * cambiar_estado.html - Cambio de estado para técnicos
- **Dashboard de Métricas**: metricas.html
  * Cards animados
  * Gráficos de barras dinámicos
  * Tabla de eficiencia de técnicos
  * Selector de período
- **Sistema de Calificaciones**: Estrellas interactivas
- JavaScript personalizado

---

### 5. [Guía de Desarrollo](05_DESARROLLO.md)
Guía completa para desarrolladores que trabajarán en el proyecto.

**Contenido:**
- Configuración del entorno de desarrollo
- Estructura del código y convenciones
- Flujo de trabajo con Git (branching strategy)
- Convenciones de commits (Conventional Commits)
- Testing (crear tests para modelos y vistas)
- Mejores prácticas:
  * Optimización de queries (select_related, prefetch_related)
  * Manejo de transacciones
  * Seguridad (CSRF, validación, control de acceso)
- Desarrollo de frontend (CSS, JavaScript)
- Migraciones de base de datos
- Comandos de gestión personalizados
- Debugging y logging

---

### 6. [API y Comandos](06_API_COMANDOS.md)
Referencia técnica de comandos, queries y APIs del sistema.

**Contenido:**
- **Comandos de Django**:
  * Gestión de base de datos
  * Gestión de usuarios
  * Servidor de desarrollo
  * Shell interactivo
  * Archivos estáticos
- **Comandos Personalizados**:
  * verificar_sla - Monitoreo automático de SLA
  * Programación con Task Scheduler/Cron
- **Queries del ORM**:
  * Filtros básicos y avanzados
  * Búsquedas de texto
  * Ordenamiento y limitación
  * Agregaciones y anotaciones
  * Agrupación y relaciones
  * Manejo de fechas
  * Actualización y eliminación en masa
- **URLs del Sistema**: Mapeo completo
- **Permisos y Decoradores**: Control de acceso
- **Exportación de Datos**: CSV, Excel, PDF
- **Debugging y Profiling**

---

### 7. [Sistema de Métricas y SLA](METRICAS_SLA_README.md)
Documentación específica del sistema de métricas, analytics y SLA.

**Contenido:**
- Descripción del sistema de métricas
- 12+ KPIs implementados:
  * Métricas de rendimiento
  * Métricas de calidad (CSAT)
  * Métricas de eficiencia
  * Análisis de causas raíz
  * Cumplimiento de SLA
- Configuración del sistema SLA automático
- Tiempos límite por prioridad
- Comando verificar_sla
- Programación automática (Windows/Linux)
- Acceso a métricas (solo administradores)
- Períodos disponibles
- Nuevos campos en el modelo Ticket
- Estados de ticket

---

## 🚀 Inicio Rápido

1. **Primera vez?** Lee el [README principal](../README.md) para instalación
2. **Desarrollador?** Comienza con [Arquitectura](01_ARQUITECTURA.md) y [Desarrollo](05_DESARROLLO.md)
3. **Administrador?** Revisa [Métricas y SLA](METRICAS_SLA_README.md)
4. **Frontend?** Consulta [Templates](04_TEMPLATES.md)
5. **Backend?** Estudia [Modelos](02_MODELOS.md), [Vistas](03_VISTAS.md) y [API](06_API_COMANDOS.md)

---

## 📊 Estadísticas del Proyecto

- **Lenguaje**: Python 3.13
- **Framework**: Django 5.2.6
- **Base de Datos**: PostgreSQL
- **Líneas de Código**: ~3,500+
- **Modelos**: 5 principales
- **Vistas**: 13 vistas principales
- **Templates**: 9 templates
- **Archivos CSS**: 7 hojas de estilo
- **Archivos JS**: 3 scripts
- **Métricas**: 12+ KPIs
- **Tests**: Estructura preparada

---

## 🔧 Tecnologías Documentadas

### Backend
- Django 5.2.6 (MVT Framework)
- PostgreSQL (Base de datos)
- psycopg2 (Adaptador BD)
- python-decouple (Variables de entorno)

### Frontend
- Bootstrap 4 (Framework CSS)
- django-crispy-forms (Formularios)
- JavaScript ES6 (Interactividad)
- CSS3 (Animaciones y estilos)

### Procesamiento
- Pandas 2.3.2 (Análisis de datos)
- NumPy 2.3.3 (Computación)
- Openpyxl 3.1.5 (Excel)

### Reportes
- ReportLab 4.4.3 (PDFs)
- Pillow 11.3.0 (Imágenes)

---

## 📝 Notas de Versión

**Versión Actual**: 1.0.0 (Noviembre 2025)

### Características Implementadas
- ✅ Sistema completo de gestión de tickets
- ✅ Control de acceso por roles (Admin, Técnico, Usuario)
- ✅ Dashboard de métricas con 12+ KPIs
- ✅ Sistema SLA automático
- ✅ Sistema de calificaciones (CSAT)
- ✅ Gestión de archivos adjuntos
- ✅ Historial de cambios completo
- ✅ Sistema de comentarios
- ✅ Filtros avanzados y búsqueda
- ✅ Paginación optimizada
- ✅ Diseño responsive
- ✅ Animaciones CSS3

### Próximas Mejoras Planificadas
- 🔄 API REST (Django REST Framework)
- 🔄 Notificaciones por email
- 🔄 Sistema de cache (Redis)
- 🔄 Procesamiento asíncrono (Celery)
- 🔄 Exportación avanzada de reportes
- 🔄 Dashboard en tiempo real
- 🔄 Integración con LDAP

---

## 📞 Soporte y Contacto

- **Desarrollador**: Nadiizz
- **Organización**: Grupo Coyahue
- **Repositorio**: https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets
- **Documentación**: `/doc/`

---

## 📄 Licencia

Proyecto privado - © 2025 Grupo Coyahue. Todos los derechos reservados.

---

**Última actualización**: Noviembre 2025
