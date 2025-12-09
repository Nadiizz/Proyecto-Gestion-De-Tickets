# 🔌 API Reference - Endpoints del Sistema

## Índice

1. [Autenticación](#autenticación)
2. [Tickets](#tickets)
3. [Notificaciones API](#notificaciones-api)
4. [Subcategorías API](#subcategorías-api)
5. [Panel de Administración](#panel-de-administración)
6. [FAQs](#faqs)

---

## Autenticación

El sistema usa autenticación basada en sesiones de Django.

### Login

```
POST /login/
```

**Parámetros:**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| username | string | ✅ |
| password | string | ✅ |

**Respuesta:** Redirect a `/` (ticket_list)

### Logout

```
GET/POST /logout/
```

**Respuesta:** Redirect a `/login/?logout=success`

---

## Tickets

### Listar Tickets

```
GET /
```

**Parámetros de Query:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| busqueda | string | Búsqueda en título/descripción |
| estado | string | Filtrar por estado |
| prioridad | string | Filtrar por prioridad |
| categoria | string | Filtrar por categoría |
| asignado_a | int | ID del técnico |
| dias_atras | int | Tickets de los últimos N días |
| page | int | Página de resultados |

**Ejemplo:**
```
GET /?estado=pendiente&prioridad=alta&page=2
```

### Crear Ticket

```
GET/POST /nuevo/
```

**Campos del formulario (POST):**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| titulo | string | ✅ |
| descripcion | text | ✅ |
| tipo | string | ✅ (incidencia, solicitud, problema, cambio) |
| categoria | int | ❌ |
| subcategoria | int | ❌ |
| archivos | file[] | ❌ (múltiples) |
| prioridad | string | ❌ (solo admin) |
| asignar_a | int | ❌ (solo admin) |

**Respuesta exitosa:** Redirect a `/`

### Ver Ticket

```
GET /ticket/<ticket_id>/
```

**Permisos:** Admin, Técnico, Creador del ticket, Técnico asignado

**Respuesta:** Página de detalle con comentarios e historial

### Agregar Comentario

```
POST /ticket/<ticket_id>/
```

**Campos:**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| mensaje | text | ✅ |
| archivos_comentario | file[] | ❌ |

### Asignar Ticket

```
GET/POST /asignar/<ticket_id>/
```

**Permisos:** Admin o usuario con `puede_asignar_tickets`

**Campos (POST):**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| tecnico | int | ✅ (ID del técnico) |
| prioridad | string | ❌ |
| horas_sla | int | ❌ (SLA personalizado) |

### Autoasignar Ticket

```
GET/POST /autoasignar/<ticket_id>/
```

**Permisos:** Solo técnicos

**Restricciones:**
- No puede ser el creador del ticket
- No puede estar ya asignado a él mismo

### Cambiar Estado

```
GET/POST /estado/<ticket_id>/
```

**Permisos:** Técnico asignado, Admin, o usuario con `puede_cambiar_estado`

**Campos (POST):**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| estado | string | ✅ |
| comentario | text | ❌ |

**Estados válidos:** pendiente, en_progreso, resuelto, cerrado, tiempo_excedido

### Calificar Ticket

```
POST /calificar/<ticket_id>/
```

**Permisos:** Solo el creador del ticket

**Restricciones:**
- Ticket debe estar resuelto o cerrado
- Solo se puede calificar una vez

**Campos:**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| calificacion | int | ✅ (1-5) |

---

## Notificaciones API

### Obtener Todas las Notificaciones

```
GET /api/notificaciones/
```

**Respuesta (JSON):**
```json
{
    "notificaciones": [
        {
            "id": 1,
            "titulo": "🆕 Nuevo Ticket Creado",
            "mensaje": "Se creó un nuevo ticket: Problema con impresora",
            "tipo": "ticket_creado",
            "prioridad": "media",
            "leida": false,
            "fecha": "2024-12-08T10:30:00Z",
            "enlace": "/ticket/123/",
            "ticket_id": 123,
            "ticket_titulo": "Problema con impresora"
        }
    ],
    "total_no_leidas": 5
}
```

### Obtener Notificaciones Nuevas

```
GET /api/notificaciones/nuevas/
```

**Respuesta (JSON):**
```json
{
    "notificaciones": [...],
    "total_no_leidas": 3
}
```

### Marcar Notificación como Leída

```
POST /api/notificaciones/<notificacion_id>/marcar-leida/
```

**Respuesta (JSON):**
```json
{
    "success": true,
    "total_no_leidas": 2
}
```

### Marcar Todas como Leídas

```
POST /api/notificaciones/marcar-todas-leidas/
```

**Respuesta (JSON):**
```json
{
    "success": true,
    "total_no_leidas": 0
}
```

---

## Subcategorías API

### Obtener Subcategorías por Categoría

```
GET /api/subcategorias/<categoria_id>/
```

**Respuesta (JSON):**
```json
{
    "subcategorias": [
        {"id": 1, "nombre": "Hardware"},
        {"id": 2, "nombre": "Software"},
        {"id": 3, "nombre": "Redes"}
    ]
}
```

**Uso:** Poblar select dinámico en formulario de tickets

---

## Panel de Administración

### Dashboard Principal

```
GET /admin-panel/
```

**Permisos:** Admin o usuario con permisos de gestión

### Gestión de Usuarios

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/admin-panel/usuarios/` | Listar usuarios |
| GET/POST | `/admin-panel/usuarios/crear/` | Crear usuario |
| GET/POST | `/admin-panel/usuarios/editar/<user_id>/` | Editar usuario |
| POST | `/admin-panel/usuarios/toggle/<user_id>/` | Activar/Desactivar |
| POST | `/admin-panel/usuarios/eliminar/<user_id>/` | Eliminar usuario |

### Gestión de Roles

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/admin-panel/roles/` | Listar roles |
| GET/POST | `/admin-panel/roles/crear/` | Crear rol |
| GET/POST | `/admin-panel/roles/editar/<rol_id>/` | Editar rol |
| POST | `/admin-panel/roles/toggle/<rol_id>/` | Activar/Desactivar |
| POST | `/admin-panel/roles/eliminar/<rol_id>/` | Eliminar rol |

### Gestión de Categorías

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/admin-panel/categorias/` | Listar categorías |
| GET/POST | `/admin-panel/categorias/crear/` | Crear categoría |
| GET/POST | `/admin-panel/categorias/editar/<id>/` | Editar categoría |
| POST | `/admin-panel/categorias/eliminar/<id>/` | Eliminar |

### Gestión de Subcategorías

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/admin-panel/subcategorias/` | Listar subcategorías |
| GET/POST | `/admin-panel/subcategorias/crear/` | Crear subcategoría |
| GET/POST | `/admin-panel/subcategorias/editar/<id>/` | Editar |
| POST | `/admin-panel/subcategorias/eliminar/<id>/` | Eliminar |

---

## FAQs

### Ver FAQs Públicas

```
GET /faqs/
```

**Parámetros de Query:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| q | string | Búsqueda en preguntas/respuestas |
| categoria | int | Filtrar por categoría |

### Gestión de FAQs (Admin)

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/admin-panel/faqs/` | Dashboard FAQs |
| GET/POST | `/admin-panel/faqs/categoria/crear/` | Crear categoría FAQ |
| GET/POST | `/admin-panel/faqs/categoria/editar/<id>/` | Editar categoría |
| POST | `/admin-panel/faqs/categoria/eliminar/<id>/` | Eliminar categoría |
| GET | `/admin-panel/faqs/categoria/<id>/preguntas/` | Preguntas de categoría |
| GET/POST | `/admin-panel/faqs/pregunta/crear/` | Crear pregunta |
| GET/POST | `/admin-panel/faqs/pregunta/editar/<id>/` | Editar pregunta |
| POST | `/admin-panel/faqs/pregunta/eliminar/<id>/` | Eliminar pregunta |
| POST | `/admin-panel/faqs/pregunta/toggle/<id>/` | Activar/Desactivar |
| GET | `/admin-panel/faqs/busquedas/` | Ver búsquedas de usuarios |

### Subir Imagen para FAQ

```
POST /admin-panel/faqs/subir-imagen/
```

**Content-Type:** `multipart/form-data`

**Campos:**
| Campo | Tipo | Requerido |
|-------|------|-----------|
| imagen | file | ✅ |

**Respuesta (JSON):**
```json
{
    "success": true,
    "url": "/media/faqs/imagenes/abc123.jpg"
}
```

---

## Otras URLs

### Perfil de Usuario

```
GET/POST /perfil/
```

**Campos editables:**
- first_name, last_name
- telefono, departamento, cargo, ubicacion
- foto_perfil
- notificaciones_email, notificaciones_whatsapp
- numero_whatsapp

### Mis Tickets

```
GET /mis-tickets/
```

**Parámetros de Query:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| estado | string | Filtrar por estado |

### Mis Asignaciones (Técnicos)

```
GET /mis-asignaciones/
```

**Permisos:** Solo técnicos y admins

**Parámetros de Query:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| estado | string | Filtrar por estado |
| prioridad | string | Filtrar por prioridad |

### Métricas

```
GET /metricas/
```

**Permisos:** Admin o usuario con `puede_ver_metricas`

**Parámetros de Query:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| dias | int | Período (7, 30, 90, 365, 0=todo) |

### Lista de Notificaciones (HTML)

```
GET /notificaciones/
```

**Respuesta:** Página HTML con todas las notificaciones

---

## Códigos de Estado HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK |
| 302 | Redirect (después de POST exitoso) |
| 400 | Bad Request |
| 403 | Forbidden (sin permisos) |
| 404 | Not Found |
| 500 | Server Error |

---

## Headers Requeridos

### Para Requests AJAX/API

```javascript
headers: {
    'X-CSRFToken': getCookie('csrftoken'),
    'Content-Type': 'application/json'
}
```

### Obtener CSRF Token

```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
```
