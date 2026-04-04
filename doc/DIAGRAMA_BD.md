# 🗄️ Diagrama de Base de Datos - DBML

Este archivo puede ser importado en [dbdiagram.io](https://dbdiagram.io) para visualizar el modelo de datos.

```dbml
// Sistema de Gestión de Tickets - Coyahue
// Generado: Diciembre 2024

// ==========================================
// USUARIOS Y AUTENTICACIÓN
// ==========================================

Table auth_user {
  id integer [pk, increment]
  username varchar(150) [unique, not null]
  email varchar(254) [not null]
  password varchar(128) [not null]
  first_name varchar(150)
  last_name varchar(150)
  is_active boolean [default: true]
  is_staff boolean [default: false]
  is_superuser boolean [default: false]
  date_joined datetime [not null]
  last_login datetime
}

Table auth_group {
  id integer [pk, increment]
  name varchar(150) [unique, not null]
  
  Note: 'Grupos: Administrador, Técnico, Usuario'
}

Table auth_user_groups {
  id integer [pk, increment]
  user_id integer [ref: > auth_user.id]
  group_id integer [ref: > auth_group.id]
}

// ==========================================
// PERFILES Y ROLES PERSONALIZADOS
// ==========================================

Table tickets_rolpersonalizado {
  id integer [pk, increment]
  nombre varchar(100) [unique, not null]
  descripcion text
  color varchar(7) [default: '#3498db']
  puede_ver_metricas boolean [default: false]
  puede_ver_todos_tickets boolean [default: false]
  puede_asignar_tickets boolean [default: false]
  puede_cambiar_estado boolean [default: false]
  puede_gestionar_usuarios boolean [default: false]
  puede_crear_roles boolean [default: false]
  activo boolean [default: true]
  fecha_creacion datetime [not null]
  creado_por_id integer [ref: > auth_user.id]
}

Table tickets_perfilusuario {
  id integer [pk, increment]
  user_id integer [unique, ref: - auth_user.id]
  telefono varchar(20)
  departamento varchar(100)
  cargo varchar(100)
  ubicacion varchar(200)
  foto_perfil varchar(255)
  rol_personalizado_id integer [ref: > tickets_rolpersonalizado.id]
  notificaciones_email boolean [default: true]
  notificaciones_whatsapp boolean [default: false]
  numero_whatsapp varchar(20)
  fecha_creacion datetime [not null]
  creado_por_id integer [ref: > auth_user.id]
}

// ==========================================
// CATEGORÍAS
// ==========================================

Table tickets_categoria {
  id integer [pk, increment]
  nombre varchar(100) [unique, not null]
  descripcion text
  activa boolean [default: true]
  fecha_creacion datetime [not null]
}

Table tickets_subcategoria {
  id integer [pk, increment]
  categoria_id integer [ref: > tickets_categoria.id, not null]
  nombre varchar(100) [not null]
  descripcion text
  activa boolean [default: true]
  fecha_creacion datetime [not null]
  
  indexes {
    (categoria_id, nombre) [unique]
  }
}

// ==========================================
// TICKETS (ENTIDAD PRINCIPAL)
// ==========================================

Table tickets_ticket {
  id integer [pk, increment]
  titulo varchar(200) [not null]
  descripcion text [not null]
  estado varchar(20) [not null, default: 'pendiente', note: 'pendiente, en_progreso, resuelto, cerrado, tiempo_excedido']
  prioridad varchar(10) [not null, default: 'media', note: 'baja, media, alta, critica']
  tipo varchar(20) [not null, default: 'incidencia', note: 'incidencia, solicitud, problema, cambio']
  categoria_id integer [ref: > tickets_categoria.id]
  subcategoria_id integer [ref: > tickets_subcategoria.id]
  creador_id integer [ref: > auth_user.id, not null]
  asignado_a_id integer [ref: > auth_user.id]
  fecha_creacion datetime [not null]
  fecha_cierre datetime
  fecha_primera_respuesta datetime
  fecha_asignacion datetime
  tiempo_limite_resolucion datetime [note: 'SLA deadline']
  fue_reabierto boolean [default: false]
  numero_escalamientos integer [default: 0]
  calificacion_satisfaccion integer [note: '1-5 estrellas']
  
  indexes {
    (estado, fecha_creacion)
    (asignado_a_id, estado)
    creador_id
  }
}

// ==========================================
// COMENTARIOS Y ARCHIVOS
// ==========================================

Table tickets_comentario {
  id integer [pk, increment]
  ticket_id integer [ref: > tickets_ticket.id, not null]
  autor_id integer [ref: > auth_user.id, not null]
  mensaje text [not null]
  fecha datetime [not null]
}

Table tickets_historialestado {
  id integer [pk, increment]
  ticket_id integer [ref: > tickets_ticket.id, not null]
  cambiado_por_id integer [ref: > auth_user.id, not null]
  estado_anterior varchar(50)
  estado_nuevo varchar(50) [not null]
  comentario text
  fecha datetime [not null]
}

Table tickets_archivoticket {
  id integer [pk, increment]
  ticket_id integer [ref: > tickets_ticket.id, not null]
  archivo varchar(255) [not null]
  nombre_archivo varchar(255) [not null]
  subido_por_id integer [ref: > auth_user.id, not null]
  fecha_subida datetime [not null]
}

Table tickets_archivocomentario {
  id integer [pk, increment]
  comentario_id integer [ref: > tickets_comentario.id, not null]
  archivo varchar(255) [not null]
  nombre_archivo varchar(255) [not null]
  subido_por_id integer [ref: > auth_user.id, not null]
  fecha_subida datetime [not null]
}

// ==========================================
// NOTIFICACIONES
// ==========================================

Table tickets_notificacion {
  id integer [pk, increment]
  usuario_id integer [ref: > auth_user.id, not null]
  ticket_id integer [ref: > tickets_ticket.id]
  tipo varchar(50) [not null, note: 'ticket_creado, ticket_asignado, ticket_comentario, estado_cambio, ticket_resuelto, ticket_cerrado']
  prioridad varchar(20) [default: 'media']
  titulo varchar(200) [not null]
  mensaje text [not null]
  email_enviado boolean [default: false]
  email_fecha datetime
  whatsapp_enviado boolean [default: false]
  whatsapp_fecha datetime
  leida boolean [default: false]
  fecha_leida datetime
  fecha_creacion datetime [not null]
  enlace varchar(500)
  
  indexes {
    (usuario_id, fecha_creacion)
    (usuario_id, leida)
  }
}

// ==========================================
// SISTEMA DE FAQs
// ==========================================

Table tickets_categoriafaq {
  id integer [pk, increment]
  nombre varchar(100) [not null]
  icono varchar(10) [default: '❓']
  descripcion text
  orden integer [default: 0]
  activa boolean [default: true]
  fecha_creacion datetime [not null]
  creado_por_id integer [ref: > auth_user.id]
}

Table tickets_preguntafaq {
  id integer [pk, increment]
  categoria_id integer [ref: > tickets_categoriafaq.id, not null]
  pregunta varchar(300) [not null]
  respuesta text [not null, note: 'Soporta HTML básico y embeds de video']
  imagen varchar(255)
  orden integer [default: 0]
  activa boolean [default: true]
  vistas integer [default: 0]
  fecha_creacion datetime [not null]
  fecha_actualizacion datetime [not null]
  creado_por_id integer [ref: > auth_user.id]
}

Table tickets_busquedafaq {
  id integer [pk, increment]
  termino varchar(200) [not null]
  usuario_id integer [ref: > auth_user.id]
  encontro_resultados boolean [default: false]
  cantidad_resultados integer [default: 0]
  fecha datetime [not null]
  
  indexes {
    fecha
    termino
  }
}

Table tickets_imagenfaq {
  id integer [pk, increment]
  imagen varchar(255) [not null]
  nombre_original varchar(255)
  alt_text varchar(200)
  subida_por_id integer [ref: > auth_user.id]
  fecha_subida datetime [not null]
}
```

## Vista del Diagrama

Para visualizar este diagrama:

1. Ve a [dbdiagram.io](https://dbdiagram.io)
2. Crea un nuevo diagrama
3. Copia el código DBML de arriba (sin los backticks)
4. Pégalo en el editor

## Relaciones Principales

```
User ─────────────────┬──────────────────┐
  │                   │                  │
  ├─► PerfilUsuario   │                  │
  │        │          │                  │
  │        ▼          │                  │
  │   RolPersonalizado│                  │
  │                   │                  │
  └─► Ticket ◄────────┘                  │
       │  │                              │
       │  ├─► Comentario ─► ArchivoComentario
       │  │
       │  ├─► HistorialEstado
       │  │
       │  ├─► ArchivoTicket
       │  │
       │  └─► Notificacion
       │
       ├─► Categoria
       │        │
       │        └─► Subcategoria
       │
       └─► CategoriaFAQ
                │
                └─► PreguntaFAQ
```
