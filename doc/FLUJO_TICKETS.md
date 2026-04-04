# 🔄 Flujo de Trabajo de Tickets

## Ciclo de Vida de un Ticket

```
┌─────────────────────────────────────────────────────────────────┐
│                     CICLO DE VIDA DEL TICKET                    │
└─────────────────────────────────────────────────────────────────┘

     Usuario                Admin/Sistema              Técnico
        │                        │                        │
        │  1. Crear ticket       │                        │
        ├───────────────────────►│                        │
        │                        │                        │
        │     [PENDIENTE] ◄──────┤                        │
        │                        │                        │
        │                        │  2. Asignar técnico    │
        │                        ├───────────────────────►│
        │                        │                        │
        │                        │      O bien...         │
        │                        │                        │
        │                        │  2b. Autoasignarse     │
        │                        │◄───────────────────────┤
        │                        │                        │
        │     [EN_PROGRESO] ◄────┼────────────────────────┤
        │                        │                        │
        │                        │  3. Trabajar ticket    │
        │                        │                        │
        │                        │  4. Resolver           │
        │     [RESUELTO] ◄───────┼────────────────────────┤
        │                        │                        │
        │  5. Calificar          │                        │
        ├───────────────────────►│                        │
        │                        │                        │
        │     [CERRADO] ◄────────┤                        │
        │                        │                        │
        └────────────────────────┴────────────────────────┘
```

---

## Estados del Ticket

### 1. Pendiente ⏳
- **Descripción**: Ticket recién creado, esperando asignación
- **Acciones disponibles**: Asignar, Autoasignar
- **Quién puede cambiar**: Admin, Técnico (autoasignación)

### 2. En Progreso 🟡
- **Descripción**: Técnico trabajando activamente
- **Acciones disponibles**: Resolver, Devolver a pendiente
- **Quién puede cambiar**: Técnico asignado, Admin

### 3. Resuelto 🟢
- **Descripción**: Solución aplicada, pendiente de confirmación
- **Acciones disponibles**: Cerrar, Reabrir (si no funcionó)
- **Quién puede cambiar**: Admin, Técnico, Usuario (reabrir)

### 4. Cerrado ⚫
- **Descripción**: Ticket finalizado completamente
- **Acciones disponibles**: Solo Admin puede reabrir
- **Quién puede cambiar**: Solo Admin

### 5. Tiempo Excedido ⚠️
- **Descripción**: SLA vencido sin resolución
- **Acciones disponibles**: Reabrir, Asignar nuevo técnico
- **Quién puede cambiar**: Admin, Sistema (automático)

---

## Transiciones de Estado

### Matriz de Transiciones

```python
TRANSICIONES_ESTADO_VALIDAS = {
    'pendiente':       ['en_progreso', 'asignado'],
    'asignado':        ['en_progreso', 'cerrado'],
    'en_progreso':     ['resuelto', 'pendiente', 'en_progreso'],
    'resuelto':        ['cerrado', 'pendiente'],
    'cerrado':         [],  # Solo admin puede reabrir
    'tiempo_excedido': ['pendiente', 'en_progreso'],
}
```

### Diagrama de Transiciones

```
                    ┌──────────────┐
                    │   PENDIENTE  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            │            ▼
       ┌──────────┐        │     ┌─────────────┐
       │ ASIGNADO │        │     │ EN_PROGRESO │◄─────┐
       └────┬─────┘        │     └──────┬──────┘      │
            │              │            │             │
            └──────────────┴─────┬──────┘             │
                                 │                    │
                                 ▼                    │
                          ┌──────────┐                │
                          │ RESUELTO │────────────────┘
                          └────┬─────┘    (reabrir)
                               │
                               ▼
                          ┌──────────┐
                          │ CERRADO  │
                          └──────────┘
                               
        ┌────────────────┐
        │ TIEMPO_EXCEDIDO│───► PENDIENTE / EN_PROGRESO
        └────────────────┘     (reapertura)
```

---

## Acciones por Rol

### Usuario Regular

| Acción | ¿Puede? | Condición |
|--------|---------|-----------|
| Crear ticket | ✅ | Siempre |
| Ver ticket | ✅ | Solo propios |
| Comentar | ✅ | En sus tickets |
| Calificar | ✅ | Solo resueltos/cerrados propios |
| Reabrir | ✅ | Solo si está resuelto |

### Técnico

| Acción | ¿Puede? | Condición |
|--------|---------|-----------|
| Ver tickets | ✅ | Todos |
| Autoasignarse | ✅ | No ser el creador |
| Cambiar estado | ✅ | Tickets asignados a él |
| Comentar | ✅ | Cualquier ticket |
| Reasignarse | ✅ | De otro técnico |

### Administrador

| Acción | ¿Puede? | Condición |
|--------|---------|-----------|
| Todo lo anterior | ✅ | Sin restricciones |
| Asignar tickets | ✅ | A cualquier técnico |
| Reabrir cerrados | ✅ | Único que puede |
| Establecer SLA | ✅ | Personalizado por ticket |
| Cambiar prioridad | ✅ | En cualquier momento |

---

## Eventos y Notificaciones

### Cuándo se Notifica

| Evento | Notificación | Destinatario |
|--------|--------------|--------------|
| Ticket creado | ✅ | Administradores |
| Ticket asignado | ✅ | Técnico asignado |
| Nuevo comentario | ✅ | Creador o Técnico |
| Estado cambiado | ✅ | Creador (si resuelto) |
| Ticket cerrado | ✅ | Creador |
| SLA por vencer | ⚠️ | Técnico (futuro) |

### Registro en Historial

Cada cambio de estado se registra:

```python
HistorialEstado.objects.create(
    ticket=ticket,
    cambiado_por=request.user,
    estado_anterior='pendiente',
    estado_nuevo='en_progreso',
    comentario='Iniciando trabajo en el ticket'
)
```

---

## Flujos Especiales

### 1. Autoasignación de Técnico

```python
# Técnico puede tomar tickets sin asignar
# O reasignarse tickets de otros técnicos

@login_required
def autoasignar_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Verificaciones
    if not es_tecnico(request.user):
        return error("Solo técnicos")
    
    if ticket.creador == request.user:
        return error("No puedes autoasignarte tu propio ticket")
    
    if ticket.asignado_a == request.user:
        return error("Ya está asignado a ti")
    
    # Guardar técnico anterior para historial
    tecnico_anterior = ticket.asignado_a
    
    # Autoasignar
    ticket.asignado_a = request.user
    ticket.fecha_asignacion = timezone.now()
    ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
    ticket.save()
```

### 2. Reapertura de Ticket

```python
# Un ticket resuelto puede reabrirse si la solución no funcionó

if estado_anterior in ['resuelto', 'cerrado', 'tiempo_excedido']:
    if nuevo_estado in ['pendiente', 'en_progreso']:
        ticket.fue_reabierto = True
        ticket.fecha_cierre = None  # Limpiar fecha de cierre
        logger.warning(f'Ticket #{ticket.id} reabierto')
```

### 3. Cierre Automático por SLA

```python
# El sistema verifica cada hora los tickets vencidos

def verificar_y_actualizar_sla():
    tickets_vencidos = Ticket.objects.filter(
        estado__in=['pendiente', 'en_progreso'],
        tiempo_limite_resolucion__lt=timezone.now()
    )
    
    for ticket in tickets_vencidos:
        ticket.estado = 'tiempo_excedido'
        ticket.fecha_cierre = timezone.now()
        ticket.save()
        
        # Registrar cambio automático
        HistorialEstado.objects.create(
            ticket=ticket,
            cambiado_por=ticket.asignado_a or ticket.creador,
            estado_anterior=ticket.estado,
            estado_nuevo='tiempo_excedido',
            comentario='Cerrado automáticamente por SLA excedido'
        )
```

---

## Validación de Transiciones

### En el Modelo

```python
def puede_cambiar_estado_a(self, nuevo_estado):
    """Valida si la transición está permitida"""
    if self.estado == nuevo_estado:
        return True  # No-op
    
    transiciones_permitidas = TRANSICIONES_ESTADO_VALIDAS.get(
        self.estado, []
    )
    
    return nuevo_estado in transiciones_permitidas
```

### En la Vista

```python
@login_required
def cambiar_estado(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    nuevo_estado = request.POST.get('estado')
    
    # Validar transición
    if not ticket.puede_cambiar_estado_a(nuevo_estado):
        transiciones = ticket.obtener_transiciones_permitidas()
        messages.error(
            request,
            f'No se puede cambiar de "{ticket.estado}" a "{nuevo_estado}". '
            f'Transiciones permitidas: {", ".join(transiciones)}'
        )
        return redirect('cambiar_estado', ticket_id=ticket.id)
    
    # Proceder con el cambio...
```

---

## Campos de Seguimiento

### Fechas Importantes

| Campo | Cuándo se Establece |
|-------|---------------------|
| `fecha_creacion` | Automático al crear |
| `fecha_asignacion` | Al asignar técnico |
| `fecha_primera_respuesta` | Primer comentario de técnico/admin |
| `fecha_cierre` | Al resolver o cerrar |
| `tiempo_limite_resolucion` | Calculado según SLA |

### Flags de Estado

| Campo | Significado |
|-------|-------------|
| `fue_reabierto` | El ticket fue reabierto al menos una vez |
| `numero_escalamientos` | Veces que se escaló (futuro) |
| `calificacion_satisfaccion` | Rating del usuario (1-5) |
