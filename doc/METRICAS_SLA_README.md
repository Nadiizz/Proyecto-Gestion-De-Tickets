# Sistema de Métricas y SLA - Gestión de Tickets Coyahue

## 📊 Descripción del Sistema

El sistema incluye un módulo completo de métricas y SLA (Service Level Agreement) que permite monitorear y analizar el desempeño del centro de ayuda.

## 🚀 Nuevas Funcionalidades Implementadas

### 1. Métricas de Rendimiento
- **Volumen de Tickets**: Total de tickets recibidos y resueltos por período
- **Tiempo de Primera Respuesta**: Tiempo promedio que tardan los técnicos en responder
- **Tiempo de Resolución**: Tiempo promedio desde apertura hasta cierre

### 2. Métricas de Calidad
- **CSAT (Satisfacción del Cliente)**: Calificación de 1-5 estrellas
- **Tasa de Reapertura**: Porcentaje de tickets reabiertos
- **NPS (Net Promoter Score)**: Índice de lealtad del cliente

### 3. Métricas de Eficiencia
- **Tickets por Técnico**: Rendimiento individual de cada técnico
- **Tasa de Escalamiento**: Frecuencia de escalamiento a niveles superiores

### 4. Análisis de Causas Raíz
- **Tickets por Tipo**: Incidencia, Solicitud, Problema, Cambio
- **Tickets por Área**: Identificación de departamentos con más problemas
- **Tickets por Prioridad**: Distribución de urgencia

### 5. Sistema SLA Automático
- **Tiempos límite por prioridad**:
  - Crítica: 4 horas
  - Alta: 8 horas
  - Media: 24 horas
  - Baja: 48 horas
- **Cierre automático** de tickets que exceden el tiempo límite
- **Nuevo estado**: "Tiempo Excedido" para tickets no resueltos a tiempo

## 🔧 Configuración del Sistema SLA

### Verificación Manual
Puedes verificar y cerrar tickets con SLA excedido manualmente ejecutando:

```bash
python manage.py verificar_sla
```

### Verificación Automática (Recomendado)

#### En Windows (Task Scheduler):

1. Abre el "Programador de tareas" (Task Scheduler)
2. Click en "Crear tarea básica"
3. Nombre: "Verificar SLA Tickets"
4. Desencadenador: "Diariamente" o "Cuando se inicie el equipo"
5. Acción: "Iniciar un programa"
6. Programa: `C:\Phyton\Proyectos\Tercer semestre\Proyecto Gestion de tickets\Proyecto-Gestion-De-Tickets\env\Scripts\python.exe`
7. Argumentos: `manage.py verificar_sla`
8. Directorio: `C:\Phyton\Proyectos\Tercer semestre\Proyecto Gestion de tickets\Proyecto-Gestion-De-Tickets`

**Configuración recomendada**: Ejecutar cada hora

#### En Linux/Mac (Cron):

Edita el crontab:
```bash
crontab -e
```

Agrega esta línea para ejecutar cada hora:
```
0 * * * * cd /ruta/a/tu/proyecto && /ruta/a/tu/venv/bin/python manage.py verificar_sla
```

## 📈 Acceso a Métricas

### Requisitos
- Solo los usuarios con rol **Administrador** pueden acceder a las métricas
- El enlace aparece en el menú lateral izquierdo: "📈 Métricas"

### Períodos Disponibles
- Últimos 7 días
- Últimos 30 días (por defecto)
- Últimos 90 días
- Último año

## 🎯 Nuevos Campos en el Modelo Ticket

El modelo `Ticket` ahora incluye:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tipo` | CharField | Tipo de ticket (incidencia, solicitud, problema, cambio) |
| `fecha_primera_respuesta` | DateTimeField | Cuándo se dio la primera respuesta |
| `fecha_asignacion` | DateTimeField | Cuándo se asignó a un técnico |
| `tiempo_limite_resolucion` | DateTimeField | Deadline del SLA |
| `fue_reabierto` | BooleanField | Si el ticket fue reabierto |
| `numero_escalamientos` | IntegerField | Veces que fue escalado |
| `calificacion_satisfaccion` | IntegerField | Calificación de 1-5 |

## 🔄 Nuevos Estados de Ticket

Además de los estados existentes, se agregó:
- **Tiempo Excedido**: Para tickets que no fueron resueltos dentro del SLA

Acceso rápido desde el menú:
- ⚫ Cerrados
- ⚠️ SLA Excedido

## 📝 Funcionamiento Automático del SLA

### Al Crear un Ticket
1. El sistema calcula automáticamente el `tiempo_limite_resolucion` basado en la prioridad
2. Se registra la hora de creación

### Al Asignar un Ticket
1. Se registra `fecha_asignacion`
2. Se puede cambiar la prioridad y recalcular el SLA

### Al Agregar un Comentario
1. Si es la primera respuesta de un técnico/admin, se registra `fecha_primera_respuesta`
2. Esto permite calcular el tiempo de primera respuesta

### Al Cambiar Estado
1. Si se marca como "Resuelto" o "Cerrado", se registra `fecha_cierre`
2. Si se reabre, se marca `fue_reabierto = True`
3. El sistema calcula automáticamente los tiempos de resolución

### Verificación Periódica
1. El comando `verificar_sla` busca tickets activos con SLA vencido
2. Los cambia automáticamente a estado "Tiempo Excedido"
3. Registra el cambio en el historial

## 🎨 Visualización de Métricas

La página de métricas incluye:
- **Cards con números grandes** para métricas principales
- **Gráficos de barras** para comparaciones
- **Tablas** para detalles por técnico
- **Indicadores visuales** con emojis y colores
- **Diseño responsive** que se adapta a móviles

## ⚙️ Cálculo de Métricas Clave

### Tiempo de Primera Respuesta
```python
tiempo = (fecha_primera_respuesta - fecha_creacion).total_seconds() / 3600
```

### Tiempo de Resolución
```python
tiempo = (fecha_cierre - fecha_creacion).total_seconds() / 3600
```

### NPS (Net Promoter Score)
```python
nps = ((promotores - detractores) / total_calificaciones) * 100
# Promotores: calificación >= 4
# Detractores: calificación <= 2
```

### Tasa de Cumplimiento SLA
```python
cumplimiento = (tickets_resueltos_a_tiempo / tickets_con_sla) * 100
```

## 🔐 Seguridad

- Solo administradores pueden acceder a métricas
- El decorador `@user_passes_test(es_admin)` protege la vista
- Los técnicos y usuarios regulares no ven el enlace en el menú

## 📊 Próximas Mejoras Sugeridas

1. **Exportar métricas** a PDF/Excel
2. **Gráficos interactivos** con Chart.js
3. **Alertas por email** cuando un ticket está próximo a exceder SLA
4. **Dashboard de técnicos** con métricas individuales
5. **Comparación de períodos** (mes actual vs mes anterior)
6. **Integración con webhooks** para notificaciones automáticas

## 🐛 Troubleshooting

### El comando verificar_sla no encuentra tickets
- Verifica que existan tickets con `tiempo_limite_resolucion` configurado
- Revisa que la fecha límite sea anterior a ahora
- Confirma que el estado sea `pendiente` o `en_progreso`

### Las métricas muestran 0
- Asegúrate de tener tickets en el período seleccionado
- Verifica que los tickets tengan las fechas correspondientes registradas
- Prueba con un período más amplio (90 días o 1 año)

### Error "no module named tickets.management"
- Verifica que existan los archivos `__init__.py` en las carpetas `management` y `commands`
- Reinicia el servidor de Django

## 📞 Soporte

Para más información o reportar problemas, contacta al equipo de desarrollo.

---

**Versión:** 2.0  
**Última actualización:** Noviembre 2025  
**Sistema:** Gestión de Tickets - Grupo Coyahue
