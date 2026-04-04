# 🔐 Sistema de Roles y Permisos - Guía Completa

## Arquitectura de Permisos

El sistema implementa un modelo híbrido de permisos que combina:
1. **Grupos tradicionales de Django** (Administrador, Técnico, Usuario)
2. **Roles personalizados** con permisos granulares

---

## 1. Grupos Tradicionales

### Administrador
```python
Permisos:
├── Gestionar todos los tickets
├── Asignar tickets a técnicos
├── Cambiar cualquier estado (incluso reabrir cerrados)
├── Ver métricas completas
├── Gestionar usuarios (crear, editar, eliminar)
├── Crear y gestionar roles personalizados
├── Gestionar categorías y subcategorías
├── Gestionar FAQs
└── Acceso total al panel de administración
```

### Técnico
```python
Permisos:
├── Ver TODOS los tickets del sistema
├── Autoasignarse tickets (incluso de otros técnicos)
├── Cambiar estado de tickets asignados
├── Agregar comentarios
├── Ver métricas (si tiene permiso adicional)
└── NO puede gestionar usuarios ni roles
```

### Usuario
```python
Permisos:
├── Crear tickets propios
├── Ver SOLO sus propios tickets
├── Agregar comentarios en sus tickets
├── Calificar tickets resueltos
└── NO puede ver tickets de otros usuarios
```

---

## 2. Roles Personalizados (RolPersonalizado)

Permiten crear roles híbridos que extienden los permisos base.

### Permisos Disponibles

| Permiso | Descripción | Por defecto |
|---------|-------------|-------------|
| `puede_ver_metricas` | Acceso a dashboard de métricas | ❌ |
| `puede_ver_todos_tickets` | Ver tickets de todos los usuarios | ❌ |
| `puede_asignar_tickets` | Asignar tickets a técnicos | ❌ |
| `puede_cambiar_estado` | Cambiar estado de cualquier ticket | ❌ |
| `puede_gestionar_usuarios` | CRUD de usuarios | ❌ |
| `puede_crear_roles` | CRUD de roles personalizados | ❌ |
| `puede_validar_prioridad` | Validar prioridades auto-detectadas | ❌ |

### Ejemplo: Rol "Supervisor"

```python
RolPersonalizado.objects.create(
    nombre="Supervisor",
    descripcion="Puede ver métricas, validar prioridades y ver todos los tickets",
    color="#9b59b6",
    puede_ver_metricas=True,
    puede_ver_todos_tickets=True,
    puede_asignar_tickets=False,
    puede_cambiar_estado=False,
    puede_gestionar_usuarios=False,
    puede_crear_roles=False,
    puede_validar_prioridad=True,  # NUEVO: Puede validar prioridades críticas
)
```

### Ejemplo: Rol "Técnico Senior"

```python
RolPersonalizado.objects.create(
    nombre="Técnico Senior",
    descripcion="Técnico con capacidad de asignar tickets y validar prioridades",
    color="#e74c3c",
    puede_ver_metricas=True,
    puede_ver_todos_tickets=True,
    puede_asignar_tickets=True,
    puede_cambiar_estado=True,
    puede_gestionar_usuarios=False,
    puede_crear_roles=False,
    puede_validar_prioridad=True,
)
```

---

## 3. Funciones de Verificación (views.py)

### Verificación de Grupo

```python
def es_admin(user):
    """Verifica si el usuario es administrador"""
    if user.groups.filter(name='Administrador').exists():
        return True
    # También verifica rol personalizado con permisos de admin
    rol = obtener_permisos_rol_personalizado(user)
    if rol:
        return rol.puede_gestionar_usuarios and rol.puede_crear_roles
    return False

def es_tecnico(user):
    """Verifica si el usuario es técnico"""
    if user.groups.filter(name='Técnico').exists():
        return True
    rol = obtener_permisos_rol_personalizado(user)
    if rol:
        return rol.puede_cambiar_estado or rol.puede_asignar_tickets
    return False
```

### Verificación de Permisos Específicos

```python
def puede_ver_metricas(user):
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_ver_metricas')

def puede_asignar_tickets(user):
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_asignar_tickets')

def puede_cambiar_estado(user):
    if es_admin(user) or es_tecnico(user):
        return True
    return tiene_permiso_rol(user, 'puede_cambiar_estado')
```

---

## 4. Context Processor (context_processors.py)

Los permisos se inyectan automáticamente en todos los templates:

```python
def permisos_usuario(request):
    if request.user.is_authenticated:
        return {
            'permisos': {
                'puede_asignar': puede_asignar_tickets(request.user),
                'puede_autoasignarse': puede_autoasignarse_tickets(request.user),
                'puede_cambiar_estado': puede_cambiar_estado(request.user),
                'puede_ver_metricas': puede_ver_metricas(request.user),
                'puede_gestionar_usuarios': puede_gestionar_usuarios(request.user),
                'puede_acceder_admin': puede_acceder_admin_panel(request.user),
                'es_admin': es_admin(request.user),
                'es_tecnico': es_tecnico(request.user),
            }
        }
    return {'permisos': {}}
```

### Uso en Templates

```html
{% if permisos.es_admin %}
    <a href="{% url 'admin_panel' %}">Panel Admin</a>
{% endif %}

{% if permisos.puede_ver_metricas %}
    <a href="{% url 'metricas' %}">Métricas</a>
{% endif %}

{% if permisos.puede_asignar %}
    <button>Asignar Ticket</button>
{% endif %}
```

---

## 5. Decoradores de Permisos

### Decorador Personalizado

```python
def ticket_permission_required(permission_type='view'):
    """
    Decorador para verificar permisos en vistas de tickets.
    permission_type: 'view', 'edit', 'admin', 'tecnico'
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            ticket_id = kwargs.get('ticket_id')
            ticket = get_object_or_404(Ticket, id=ticket_id)
            
            # Admin siempre tiene acceso
            if es_admin(request.user):
                return view_func(request, *args, **kwargs)
            
            if permission_type == 'view':
                # Técnico, creador o asignado pueden ver
                if es_tecnico(request.user) or \
                   ticket.creador == request.user or \
                   ticket.asignado_a == request.user:
                    return view_func(request, *args, **kwargs)
            
            # ... más validaciones
            
            messages.error(request, 'No tienes permiso.')
            return redirect('ticket_list')
        return wrapper
    return decorator
```

### Uso del Decorador

```python
@login_required
@ticket_permission_required('edit')
def editar_ticket(request, ticket_id):
    # Solo usuarios con permiso de edición pueden acceder
    pass
```

---

## 6. Matriz de Permisos por Acción

| Acción | Admin | Técnico | Usuario | Rol Custom |
|--------|-------|---------|---------|------------|
| Ver lista de tickets | Todos | Todos | Solo propios | Configurable |
| Crear ticket | ✅ | ✅ | ✅ | ✅ |
| Ver detalle ticket | Todos | Todos | Solo propios | Configurable |
| Asignar ticket | ✅ | ❌ | ❌ | Configurable |
| Autoasignarse | ❌ | ✅ | ❌ | ❌ |
| Cambiar estado | ✅ | Asignados | ❌ | Configurable |
| Agregar comentario | ✅ | ✅ | Propios | ✅ |
| Calificar ticket | ❌ | ❌ | Propios | ❌ |
| Ver métricas | ✅ | ❌ | ❌ | Configurable |
| Gestionar usuarios | ✅ | ❌ | ❌ | Configurable |
| Gestionar roles | ✅ | ❌ | ❌ | Configurable |
| Gestionar FAQs | ✅ | ❌ | ❌ | ❌ |

---

## 7. Asignación de Roles

### Crear Usuario con Rol

```python
# 1. Crear usuario
user = User.objects.create_user(
    username='nuevo_usuario',
    email='user@coyahue.com',
    password='password123'
)

# 2. Asignar grupo tradicional
grupo_tecnico = Group.objects.get(name='Técnico')
user.groups.add(grupo_tecnico)

# 3. Crear perfil con rol personalizado (opcional)
rol_senior = RolPersonalizado.objects.get(nombre='Técnico Senior')
PerfilUsuario.objects.create(
    user=user,
    rol_personalizado=rol_senior,
    departamento='TI',
    cargo='Técnico Senior'
)
```

### Cambiar Rol de Usuario Existente

```python
perfil = user.perfilusuario
perfil.rol_personalizado = nuevo_rol
perfil.save()
```

---

## 8. Seguridad y Buenas Prácticas

### Validación en Backend

**Nunca confiar solo en ocultar botones en el frontend.** Siempre validar en el backend:

```python
@login_required
def asignar_ticket(request, ticket_id):
    # SIEMPRE verificar permisos en el servidor
    if not puede_asignar_tickets(request.user):
        messages.error(request, 'No tienes permiso.')
        return redirect('ticket_list')
    
    # Continuar con la lógica...
```

### Logging de Acciones Sensibles

```python
import logging
logger = logging.getLogger('tickets')

def admin_eliminar_usuario(request, user_id):
    if not puede_gestionar_usuarios(request.user):
        logger.warning(
            f'Intento de acceso no autorizado: {request.user.username} '
            f'intentó eliminar usuario {user_id}'
        )
        return HttpResponseForbidden()
    
    # Logging de acción exitosa
    logger.info(f'Usuario {user_id} eliminado por {request.user.username}')
```
