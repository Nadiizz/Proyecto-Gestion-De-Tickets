# Templates y Frontend - Sistema de Gestión de Tickets

## 🎨 Estructura de Templates

```
tickets/templates/
├── registration/
│   ├── login.html                # Página de inicio de sesión
│   └── registro.html             # Formulario de registro
└── tickets/
    ├── base_intranet.html        # Template base con sidebar
    ├── base_login.html           # Template base para auth
    ├── ticket_list.html          # Lista de tickets con filtros
    ├── ticket_form.html          # Formulario creación de ticket
    ├── ticket_detalle.html       # Vista detallada de ticket
    ├── asignar_ticket.html       # Asignación de tickets
    ├── cambiar_estado.html       # Cambio de estado
    ├── metricas.html             # Dashboard de métricas
    └── mis_tickets.html          # Vista personal de usuario
```

## 📄 Templates Base

### base_intranet.html
**Propósito**: Template base para todas las vistas autenticadas

**Estructura**:
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Sistema de Tickets{% endblock %}</title>
    
    <!-- Bootstrap 4 -->
    <link rel="stylesheet" href="...bootstrap.min.css">
    
    <!-- CSS Personalizado -->
    <link rel="stylesheet" href="{% static 'tickets/css/styles.css' %}">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <img src="{% static 'tickets/img/logo-grupocoyahue.png' %}"
             class="sidebar-logo" alt="Logo">
        
        <nav>
            <!-- Links de navegación según rol -->
            {% if user.is_authenticated %}
                <a href="{% url 'ticket_list' %}">🏠 Inicio</a>
                <a href="{% url 'crear_ticket' %}">➕ Nuevo Ticket</a>
                
                {% if user.groups.all.0.name == 'Usuario' %}
                    <a href="{% url 'mis_tickets' %}">📋 Mis Tickets</a>
                {% endif %}
                
                {% if user.groups.all.0.name == 'Administrador' %}
                    <a href="{% url 'metricas' %}">📈 Métricas</a>
                    <a href="{% url 'registro' %}">👤 Registrar Usuario</a>
                {% endif %}
                
                <a href="{% url 'logout' %}">🚪 Salir</a>
            {% endif %}
        </nav>
        
        <!-- Información del usuario -->
        <div class="user-info">
            <p><strong>{{ user.username }}</strong></p>
            <p class="user-role">
                {{ user.groups.all.0.name|default:"Usuario" }}
            </p>
        </div>
    </div>
    
    <!-- Contenido Principal -->
    <div class="main-content">
        <!-- Mensajes Flash -->
        {% if messages %}
            <div class="messages-container">
                {% for message in messages %}
                    <div class="alert alert-{{ message.tags }}">
                        {{ message }}
                    </div>
                {% endfor %}
            </div>
        {% endif %}
        
        <!-- Contenido específico de cada página -->
        {% block content %}{% endblock %}
    </div>
    
    <!-- JavaScript -->
    <script src="...jquery.min.js"></script>
    <script src="...bootstrap.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**Características**:
- ✅ Sidebar responsivo con navegación contextual
- ✅ Sistema de mensajes flash (success, error, warning)
- ✅ Información del usuario y rol
- ✅ Bloques para CSS y JavaScript personalizados

---

### base_login.html
**Propósito**: Template para páginas de autenticación

**Estructura**:
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Login{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'tickets/css/login.css' %}">
</head>
<body class="login-body">
    <div class="login-container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

---

## 📋 Templates de Tickets

### ticket_list.html
**Ruta**: `tickets/ticket_list.html`

**Componentes Principales**:

#### 1. Formulario de Búsqueda y Filtros
```html
<form method="GET" class="search-form">
    <!-- Campo de búsqueda de texto -->
    <input type="text" name="busqueda"
           placeholder="Buscar por título o descripción..."
           value="{{ request.GET.busqueda }}">
    
    <!-- Filtros -->
    <select name="estado">
        <option value="">Todos los estados</option>
        <option value="pendiente">Pendiente</option>
        <option value="en_progreso">En progreso</option>
        <option value="resuelto">Resuelto</option>
        <option value="cerrado">Cerrado</option>
        <option value="tiempo_excedido">Tiempo Excedido</option>
    </select>
    
    <select name="prioridad">
        <option value="">Todas las prioridades</option>
        <option value="baja">Baja</option>
        <option value="media">Media</option>
        <option value="alta">Alta</option>
        <option value="critica">Crítica</option>
    </select>
    
    <button type="submit">🔍 Buscar</button>
</form>
```

#### 2. Lista de Tickets
```html
<div class="tickets-grid">
    {% for ticket in page_obj %}
        <div class="ticket-card {{ ticket.estado }}">
            <div class="ticket-header">
                <span class="ticket-id">#{{ ticket.id }}</span>
                <span class="badge badge-{{ ticket.prioridad }}">
                    {{ ticket.get_prioridad_display }}
                </span>
            </div>
            
            <h3>{{ ticket.titulo }}</h3>
            
            <p class="ticket-meta">
                📅 {{ ticket.fecha_creacion|date:"d/m/Y H:i" }}
            </p>
            
            <p class="ticket-meta">
                👤 Creado por: {{ ticket.creador.username }}
            </p>
            
            {% if ticket.asignado_a %}
                <p class="ticket-meta">
                    🔧 Asignado a: {{ ticket.asignado_a.username }}
                </p>
            {% endif %}
            
            <div class="ticket-footer">
                <a href="{% url 'ticket_detalle' ticket.id %}"
                   class="btn btn-primary">
                    Ver Detalles
                </a>
                
                {% if user.groups.all.0.name == 'Administrador' %}
                    {% if not ticket.asignado_a %}
                        <a href="{% url 'asignar_ticket' ticket.id %}"
                           class="btn btn-success">
                            Asignar
                        </a>
                    {% endif %}
                {% endif %}
            </div>
        </div>
    {% empty %}
        <p class="no-tickets">No hay tickets para mostrar</p>
    {% endfor %}
</div>
```

#### 3. Paginación
```html
{% if page_obj.has_other_pages %}
    <div class="pagination">
        {% if page_obj.has_previous %}
            <a href="?page=1">« Primera</a>
            <a href="?page={{ page_obj.previous_page_number }}">‹ Anterior</a>
        {% endif %}
        
        <span class="current-page">
            Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
        </span>
        
        {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}">Siguiente ›</a>
            <a href="?page={{ page_obj.paginator.num_pages }}">Última »</a>
        {% endif %}
    </div>
{% endif %}
```

---

### ticket_form.html
**Ruta**: `tickets/ticket_form.html`

**Formulario de Creación**:
```html
{% load crispy_forms_tags %}
{% load widget_tweaks %}

<div class="form-container">
    <h2>Crear Nuevo Ticket</h2>
    
    <form method="POST" enctype="multipart/form-data">
        {% csrf_token %}
        
        <!-- Título -->
        <div class="form-group">
            <label>Título *</label>
            {{ form.titulo|add_class:"form-input" }}
        </div>
        
        <!-- Tipo de Solicitud -->
        <div class="form-group">
            <label>Tipo de Solicitud *</label>
            {{ form.tipo|add_class:"form-select" }}
        </div>
        
        <!-- Descripción -->
        <div class="form-group">
            <label>Descripción *</label>
            {{ form.descripcion|add_class:"form-textarea" }}
        </div>
        
        <!-- Área Afectada -->
        <div class="form-group">
            <label>Área Afectada</label>
            {{ form.area_afectada|add_class:"form-input" }}
        </div>
        
        <!-- Archivos Adjuntos -->
        <div class="form-group">
            <label>Archivos Adjuntos</label>
            <input type="file" name="archivos" multiple
                   accept=".pdf,.jpg,.jpeg,.png,.docx">
            <small>Máximo 10MB por archivo</small>
        </div>
        
        <button type="submit" class="btn btn-primary">
            Crear Ticket
        </button>
    </form>
</div>
```

**JavaScript para Vista Previa**:
```html
{% block extra_js %}
<script src="{% static 'tickets/js/ticket_form.js' %}"></script>
{% endblock %}
```

---

### ticket_detalle.html
**Ruta**: `tickets/ticket_detalle.html`

**Secciones Principales**:

#### 1. Información del Ticket
```html
<div class="ticket-detail">
    <div class="ticket-header">
        <h1>Ticket #{{ ticket.id }}: {{ ticket.titulo }}</h1>
        
        <div class="ticket-badges">
            <span class="badge estado-{{ ticket.estado }}">
                {{ ticket.get_estado_display }}
            </span>
            <span class="badge prioridad-{{ ticket.prioridad }}">
                {{ ticket.get_prioridad_display }}
            </span>
            <span class="badge tipo-{{ ticket.tipo }}">
                {{ ticket.get_tipo_display }}
            </span>
        </div>
    </div>
    
    <div class="ticket-info-grid">
        <div class="info-item">
            <strong>Creado por:</strong>
            {{ ticket.creador.username }}
        </div>
        
        <div class="info-item">
            <strong>Fecha de creación:</strong>
            {{ ticket.fecha_creacion|date:"d/m/Y H:i" }}
        </div>
        
        {% if ticket.asignado_a %}
            <div class="info-item">
                <strong>Asignado a:</strong>
                {{ ticket.asignado_a.username }}
            </div>
        {% else %}
            <div class="info-item">
                <strong>Asignado a:</strong>
                <span class="text-danger">Sin asignar</span>
            </div>
        {% endif %}
        
        {% if ticket.area_afectada %}
            <div class="info-item">
                <strong>Área afectada:</strong>
                {{ ticket.area_afectada }}
            </div>
        {% endif %}
    </div>
    
    <!-- Indicador de SLA -->
    {% if ticket.tiempo_limite_resolucion %}
        <div class="sla-indicator">
            <strong>SLA - Tiempo límite:</strong>
            {{ ticket.tiempo_limite_resolucion|date:"d/m/Y H:i" }}
            
            {% if now > ticket.tiempo_limite_resolucion %}
                <span class="sla-excedido">⚠️ EXCEDIDO</span>
            {% else %}
                <span class="sla-cumplido">✓ En tiempo</span>
            {% endif %}
        </div>
    {% endif %}
    
    <!-- Descripción -->
    <div class="ticket-description">
        <h3>Descripción</h3>
        <p>{{ ticket.descripcion }}</p>
    </div>
</div>
```

#### 2. Archivos Adjuntos
```html
{% if archivos_ticket %}
    <div class="archivos-section">
        <h3>📎 Archivos Adjuntos</h3>
        <div class="archivos-grid">
            {% for archivo in archivos_ticket %}
                <div class="archivo-item">
                    <span>{{ archivo.nombre_archivo }}</span>
                    <a href="{{ archivo.archivo.url }}" download>
                        Descargar
                    </a>
                </div>
            {% endfor %}
        </div>
    </div>
{% endif %}
```

#### 3. Historial de Estados
```html
<div class="historial-section">
    <h3>📜 Historial de Estados</h3>
    <div class="timeline">
        {% for cambio in historial %}
            <div class="timeline-item">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <p><strong>{{ cambio.estado_nuevo|title }}</strong></p>
                    <p>Por: {{ cambio.cambiado_por.username }}</p>
                    <p>{{ cambio.fecha|date:"d/m/Y H:i" }}</p>
                    {% if cambio.comentario %}
                        <p>{{ cambio.comentario }}</p>
                    {% endif %}
                </div>
            </div>
        {% endfor %}
    </div>
</div>
```

#### 4. Comentarios
```html
<div class="comentarios-section">
    <h3>💬 Comentarios</h3>
    
    {% for comentario in comentarios %}
        <div class="comentario">
            <div class="comentario-header">
                <strong>{{ comentario.autor.username }}</strong>
                <span>{{ comentario.fecha|date:"d/m/Y H:i" }}</span>
            </div>
            <p>{{ comentario.contenido }}</p>
            
            {% if comentario.archivos_comentario.all %}
                <div class="comentario-archivos">
                    {% for archivo in comentario.archivos_comentario.all %}
                        <a href="{{ archivo.archivo.url }}" download>
                            📎 {{ archivo.nombre_archivo }}
                        </a>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    {% endfor %}
    
    <!-- Formulario para Agregar Comentario -->
    <form method="POST" enctype="multipart/form-data"
          class="comentario-form">
        {% csrf_token %}
        <textarea name="comentario" placeholder="Escribe un comentario..."
                  required></textarea>
        <input type="file" name="archivos_comentario" multiple>
        <button type="submit">Enviar</button>
    </form>
</div>
```

#### 5. Sistema de Calificación
```html
{% if ticket.estado in 'resuelto,cerrado' and user == ticket.creador %}
    {% if not ticket.calificacion_satisfaccion %}
        <div class="rating-section">
            <h3>⭐ Calificar Servicio</h3>
            <form method="POST" action="{% url 'calificar_ticket' ticket.id %}">
                {% csrf_token %}
                <div class="star-rating">
                    {% for i in '12345' %}
                        <input type="radio" name="calificacion" value="{{ i }}"
                               id="star{{ i }}">
                        <label for="star{{ i }}">★</label>
                    {% endfor %}
                </div>
                <button type="submit">Enviar Calificación</button>
            </form>
        </div>
    {% else %}
        <div class="rating-display">
            <h3>Calificación: 
                {% for i in '12345' %}
                    {% if i|add:'0' <= ticket.calificacion_satisfaccion %}
                        ★
                    {% else %}
                        ☆
                    {% endif %}
                {% endfor %}
            </h3>
        </div>
    {% endif %}
{% endif %}
```

---

### metricas.html
**Ruta**: `tickets/metricas.html`

**Estructura del Dashboard**:

#### 1. Selector de Período
```html
<div class="period-selector">
    <button onclick="cambiarPeriodo(7)"
            class="{% if dias == 7 %}active{% endif %}">
        7 días
    </button>
    <button onclick="cambiarPeriodo(30)"
            class="{% if dias == 30 %}active{% endif %}">
        30 días
    </button>
    <button onclick="cambiarPeriodo(90)"
            class="{% if dias == 90 %}active{% endif %}">
        90 días
    </button>
    <button onclick="cambiarPeriodo(365)"
            class="{% if dias == 365 %}active{% endif %}">
        Año
    </button>
    <button onclick="cambiarPeriodo(0)"
            class="{% if dias == 0 %}active{% endif %}">
        Todo el tiempo
    </button>
</div>
```

#### 2. Cards de Métricas
```html
<div class="metrics-grid">
    <!-- Tickets Totales -->
    <div class="metric-card total">
        <div class="metric-icon">📊</div>
        <div class="metric-content">
            <h3>{{ tickets_totales }}</h3>
            <p>Tickets Totales</p>
            <small>En el período seleccionado</small>
        </div>
    </div>
    
    <!-- Tickets Resueltos -->
    <div class="metric-card resueltos">
        <div class="metric-icon">✓</div>
        <div class="metric-content">
            <h3>{{ tickets_resueltos }}</h3>
            <p>Tickets Resueltos</p>
            <small>Cerrados o resueltos</small>
        </div>
    </div>
    
    <!-- Similar para otras métricas... -->
</div>
```

#### 3. Gráficos de Barras
```html
<div class="chart-section">
    <h4>📋 Tickets por Tipo</h4>
    <div class="chart-container">
        {% for tipo in tickets_por_tipo %}
            <div class="bar-chart-item">
                <div class="bar-label">{{ tipo.tipo|title }}</div>
                <div class="bar-wrapper">
                    <div class="bar-fill" data-width="{{ tipo.porcentaje }}">
                        <span class="bar-value">{{ tipo.total }}</span>
                    </div>
                </div>
            </div>
        {% endfor %}
    </div>
</div>
```

#### 4. Tabla de Eficiencia de Técnicos
```html
<table class="efficiency-table">
    <thead>
        <tr>
            <th>Técnico</th>
            <th>Total Asignados</th>
            <th>Resueltos</th>
            <th>Tasa de Resolución</th>
            <th>Calificación Promedio</th>
        </tr>
    </thead>
    <tbody>
        {% for tecnico in tickets_por_tecnico %}
            <tr>
                <td>{{ tecnico.asignado_a__username }}</td>
                <td>{{ tecnico.total }}</td>
                <td>{{ tecnico.resueltos }}</td>
                <td>
                    {% widthratio tecnico.resueltos tecnico.total 100 %}%
                </td>
                <td>
                    {% if tecnico.calificacion_promedio %}
                        {{ tecnico.calificacion_promedio|floatformat:1 }} ⭐
                    {% else %}
                        <span class="text-muted">Sin calificaciones</span>
                    {% endif %}
                </td>
            </tr>
        {% endfor %}
    </tbody>
</table>
```

**JavaScript para Gráficos**:
```html
{% block extra_js %}
<script>
function cambiarPeriodo(dias) {
    window.location.href = `?dias=${dias}`;
}

// Aplicar anchos dinámicos a las barras
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.bar-fill[data-width]').forEach(bar => {
        const width = bar.getAttribute('data-width');
        bar.style.width = width + '%';
    });
});
</script>
{% endblock %}
```

---

**Siguiente**: [Guía de Desarrollo →](05_DESARROLLO.md)
