# 📊 Sistema de SLA y Métricas

## ¿Qué es SLA?

**Service Level Agreement (SLA)** define los tiempos máximos de respuesta y resolución para los tickets según su prioridad.

---

## 1. Tiempos de SLA por Prioridad

| Prioridad | Tiempo Límite | Casos de Uso |
|-----------|---------------|--------------|
| 🔴 **Crítica** | 4 horas | Sistema caído, pérdida de datos, afecta a toda la empresa |
| 🟠 **Alta** | 8 horas | Afecta operaciones importantes, varios usuarios afectados |
| 🟡 **Media** | 24 horas | Problemas normales, un usuario afectado |
| 🟢 **Baja** | 48 horas | Consultas, mejoras, no urgente |

---

## 2. Cálculo Automático de SLA

### Método en el Modelo Ticket

```python
def calcular_tiempo_limite_sla(self, horas_personalizadas=None):
    """
    Calcula el deadline del SLA basado en la prioridad.
    Permite SLA personalizado por ticket.
    """
    if horas_personalizadas:
        # SLA personalizado (ej: cliente VIP)
        return self.fecha_creacion + timedelta(hours=int(horas_personalizadas))
    
    # SLA estándar por prioridad
    horas_por_prioridad = {
        'critica': 4,
        'alta': 8,
        'media': 24,
        'baja': 48,
    }
    horas = horas_por_prioridad.get(self.prioridad, 24)
    return self.fecha_creacion + timedelta(hours=horas)
```

### Asignación Automática al Crear Ticket

```python
# En ticket_create view
ticket.save()  # Primero guardar para tener fecha_creacion

# Calcular y guardar SLA
ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
ticket.save()
```

### SLA Personalizado al Asignar

```python
# Al asignar ticket, el admin puede especificar horas SLA
horas_sla = request.POST.get('horas_sla')  # Ej: "12"
ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla(
    horas_sla if horas_sla else None
)
```

---

## 3. Detección Automática de Prioridad

El sistema detecta automáticamente la prioridad de tickets basándose en palabras clave encontradas en el título y descripción.

### Funcionamiento

1. **Cuando se crea un ticket** (por usuario no-admin), se analiza el texto
2. **Se buscan palabras clave** categorizadas por nivel de urgencia
3. **Se asigna prioridad automáticamente** según las coincidencias
4. **Si es alta/crítica**, se notifica a supervisores para validación

### Palabras Clave Detectadas

| Prioridad | Palabras Clave |
|-----------|----------------|
| 🔴 **Crítica** | urgente, emergencia, crítico, sistema caído, perdida de datos, hackeo, virus, producción detenida, bloqueo total, servidor caído |
| 🟠 **Alta** | importante, prioritario, varios usuarios, deadline, cuanto antes, rápido, cliente importante, auditoría |
| 🟢 **Baja** | cuando pueda, no urgente, sin prisa, mejora, sugerencia, cosmético, puede esperar |

### Ejemplo de Detección

```python
def detectar_prioridad_automatica(titulo, descripcion):
    """
    Retorna: (prioridad, confianza, palabras_encontradas)
    """
    texto = f"{titulo} {descripcion}".lower()
    
    # Si encuentra "urgente" + "sistema caído" = CRÍTICA (alta confianza)
    # Si encuentra solo "importante" = ALTA (media confianza)
    # Sin palabras clave = MEDIA (baja confianza)
```

### Flujo de Validación

```
Usuario crea ticket → Sistema detecta prioridad → 
    ├── Si CRÍTICA/ALTA → Notifica supervisores → Supervisor valida/modifica
    └── Si MEDIA/BAJA → Se aplica directamente
```

### Campos en el Modelo Ticket

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `prioridad_auto_detectada` | CharField | Prioridad detectada por el sistema |
| `prioridad_validada` | BooleanField | Si un supervisor validó la prioridad |
| `validado_por` | ForeignKey(User) | Supervisor que validó |
| `fecha_validacion` | DateTimeField | Cuándo se validó |

### Acceso a Validación

- **URL**: `/tickets/validacion/` - Lista de tickets pendientes
- **URL**: `/tickets/validar/<id>/` - Validar ticket específico
- **Permiso requerido**: `puede_validar_prioridad` (Administrador o rol personalizado)

---

## 4. Verificación Automática de SLA Excedido

### Función de Verificación

```python
def verificar_y_actualizar_sla():
    """
    Verifica tickets que excedieron el SLA y los marca.
    Se ejecuta automáticamente cada hora (con cache).
    """
    cache_key = 'ultimo_check_sla'
    
    # Evitar ejecutar muy seguido
    if cache.get(cache_key):
        return
    
    # Buscar tickets vencidos
    tickets_excedidos = Ticket.objects.filter(
        estado__in=['pendiente', 'en_progreso'],
        tiempo_limite_resolucion__isnull=False,
        tiempo_limite_resolucion__lt=timezone.now()
    )
    
    for ticket in tickets_excedidos:
        estado_anterior = ticket.estado
        ticket.estado = 'tiempo_excedido'
        ticket.fecha_cierre = timezone.now()
        ticket.save()
        
        # Registrar en historial
        HistorialEstado.objects.create(
            ticket=ticket,
            cambiado_por=ticket.asignado_a or ticket.creador,
            estado_anterior=estado_anterior,
            estado_nuevo='tiempo_excedido',
            comentario='Cerrado automáticamente por SLA excedido'
        )
        
        logger.warning(f'Ticket #{ticket.id} - SLA excedido')
    
    # Cache por 1 hora
    cache.set(cache_key, True, 3600)
```

### Cuándo se Ejecuta

```python
@login_required
def ticket_list(request):
    # Se verifica automáticamente al ver la lista de tickets
    verificar_y_actualizar_sla()
    # ... resto de la vista
```

---

## 5. Métricas Disponibles

### Vista de Métricas (`/metricas/`)

Solo accesible para usuarios con `puede_ver_metricas = True`.

### Métricas de Volumen

```python
# Total de tickets en el período
tickets_totales = tickets_periodo.count()

# Por estado
tickets_resueltos = tickets_periodo.filter(
    estado__in=['resuelto', 'cerrado']
).count()

tickets_pendientes = Ticket.objects.filter(
    estado__in=['pendiente', 'en_progreso']
).count()

tickets_tiempo_excedido = Ticket.objects.filter(
    estado='tiempo_excedido'
).count()
```

### Métricas de Tiempo

```python
# Tiempo promedio de primera respuesta
def calcular_tiempo_primera_respuesta(self):
    if self.fecha_primera_respuesta:
        delta = self.fecha_primera_respuesta - self.fecha_creacion
        return delta.total_seconds() / 3600  # En horas
    return None

# Tiempo promedio de resolución
def calcular_tiempo_resolucion(self):
    if self.fecha_cierre:
        delta = self.fecha_cierre - self.fecha_creacion
        return delta.total_seconds() / 3600  # En horas
    return None
```

### Métricas de Calidad

```python
# Satisfacción promedio (CSAT)
satisfaccion_promedio = tickets_con_calificacion.aggregate(
    promedio=Avg('calificacion_satisfaccion')
)['promedio'] or 0

# Escala: 1-5 estrellas
```

### Métricas de Eficiencia

```python
# Tickets por técnico
tickets_por_tecnico = tickets_periodo.filter(
    asignado_a__isnull=False
).values('asignado_a__username').annotate(
    total=Count('id'),
    resueltos=Count('id', filter=Q(estado__in=['resuelto', 'cerrado'])),
    calificacion_promedio=Avg('calificacion_satisfaccion')
).order_by('-total')
```

### Métricas de Cumplimiento

```python
# Tasa de cumplimiento de SLA
tickets_con_sla = tickets_periodo.filter(
    tiempo_limite_resolucion__isnull=False
).count()

tickets_sla_cumplido = tickets_periodo.filter(
    tiempo_limite_resolucion__isnull=False,
    fecha_cierre__isnull=False,
    fecha_cierre__lte=F('tiempo_limite_resolucion')
).exclude(estado='tiempo_excedido').count()

tasa_cumplimiento = (tickets_sla_cumplido / tickets_con_sla * 100)
```

---

## 6. Filtros de Período

```python
# Parámetro GET: ?dias=30
dias = int(request.GET.get('dias', 30))

if dias == 0:
    # Todo el historial
    fecha_inicio = datetime(2000, 1, 1, tzinfo=timezone.utc)
else:
    fecha_inicio = timezone.now() - timedelta(days=dias)

tickets_periodo = Ticket.objects.filter(
    fecha_creacion__gte=fecha_inicio
)
```

### Opciones de Período

| Valor | Período |
|-------|---------|
| `7` | Última semana |
| `30` | Último mes |
| `90` | Últimos 3 meses |
| `365` | Último año |
| `0` | Todo el historial |

---

## 7. Tickets Próximos a Vencer

```python
# Tickets que vencen en las próximas 2 horas
tiempo_limite = timezone.now() + timedelta(hours=2)

tickets_por_vencer = Ticket.objects.filter(
    estado__in=['pendiente', 'en_progreso'],
    tiempo_limite_resolucion__isnull=False,
    tiempo_limite_resolucion__lte=tiempo_limite,
    tiempo_limite_resolucion__gt=timezone.now()
)
```

---

## 8. Indicadores Visuales en Templates

### Badge de Tiempo Restante

```html
{% if ticket.tiempo_limite_resolucion %}
    {% if ticket.tiempo_limite_resolucion < now %}
        <span class="badge badge-danger">⚠️ SLA EXCEDIDO</span>
    {% elif ticket.tiempo_limite_resolucion|timeuntil < "2 hours" %}
        <span class="badge badge-warning">⏰ Por vencer</span>
    {% else %}
        <span class="badge badge-success">✅ En tiempo</span>
    {% endif %}
{% endif %}
```

### Colores por Estado SLA

```css
.sla-ok { background: #27ae60; }        /* Verde - En tiempo */
.sla-warning { background: #f39c12; }   /* Naranja - Por vencer */
.sla-exceeded { background: #e74c3c; }  /* Rojo - Excedido */
```

---

## 9. Reportes y Exportación

### Datos para Gráficos

```python
# Tickets por día (para gráfico de líneas)
tickets_por_dia = tickets_periodo.annotate(
    dia=TruncDate('fecha_creacion')
).values('dia').annotate(
    total=Count('id')
).order_by('dia')

# Resultado: [{'dia': date, 'total': int}, ...]
```

### Tickets por Categoría

```python
tickets_por_area = tickets_periodo.filter(
    categoria__isnull=False
).values('categoria__nombre').annotate(
    total=Count('id')
).order_by('-total')[:10]
```

### Tickets por Tipo

```python
tickets_por_tipo = tickets_periodo.values('tipo').annotate(
    total=Count('id'),
    porcentaje=Count('id') * 100.0 / tickets_totales
).order_by('-total')
```

---

## 10. Calificación de Tickets (CSAT)

### Quién Puede Calificar

```python
@login_required
def calificar_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Solo el creador puede calificar
    if request.user != ticket.creador:
        messages.error(request, 'No puedes calificar este ticket.')
        return redirect('ticket_detalle', ticket_id=ticket_id)
    
    # Solo tickets resueltos/cerrados
    if ticket.estado not in ['resuelto', 'cerrado']:
        messages.error(request, 'Solo puedes calificar tickets resueltos.')
        return redirect('ticket_detalle', ticket_id=ticket_id)
    
    # Solo una vez
    if ticket.calificacion_satisfaccion:
        messages.warning(request, 'Ya calificaste este ticket.')
        return redirect('ticket_detalle', ticket_id=ticket_id)
```

### Escala de Calificación

| Estrellas | Significado |
|-----------|-------------|
| ⭐ | Muy insatisfecho |
| ⭐⭐ | Insatisfecho |
| ⭐⭐⭐ | Neutral |
| ⭐⭐⭐⭐ | Satisfecho |
| ⭐⭐⭐⭐⭐ | Muy satisfecho |
