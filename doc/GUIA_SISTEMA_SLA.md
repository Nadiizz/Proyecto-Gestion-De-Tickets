# 🚨 Guía de Verificación y Prueba del Sistema SLA

## 📋 Resumen del Sistema

El sistema SLA (Service Level Agreement) ahora funciona **automáticamente** sin necesidad de configuración adicional.

### ✅ Características Implementadas:

1. **Verificación Automática**: Se ejecuta cada vez que accedes al dashboard (`/`) o métricas (`/metricas/`)
2. **Actualización en Tiempo Real**: Los contadores se actualizan automáticamente
3. **Cambio de Estado Automático**: Tickets pendientes/en_progreso pasan a "tiempo_excedido" automáticamente
4. **Logging Completo**: Todas las acciones quedan registradas en `logs/ticket_coyahue.log`

---

## 🧪 Cómo Probar el Sistema SLA

### Opción 1: Verificación Manual (Recomendado)

1. **Ejecutar script de verificación rápida:**
   ```powershell
   python verificar_sla_rapido.py
   ```

   **Salida esperada:**
   ```
   === VERIFICACIÓN RÁPIDA DE SLA - 2025-11-16 08:30:00 ===
   
   Total tickets activos con SLA: 3
   ❌ Ticket #4 - "Problema impresora" - SLA EXCEDIDO hace 2.5 horas
      Límite: 2025-11-16 06:00:00
      Ahora:  2025-11-16 08:30:00
   ✅ Ticket #5 - "Solicitud acceso" - SLA OK (quedan 5.2 horas)
   
   Tickets ya marcados como "tiempo_excedido": 1
      Ticket #2 - "Error red"
   ```

2. **Ejecutar comando de gestión Django:**
   ```powershell
   python manage.py ver_sla
   ```

   **Salida esperada:**
   ```
   === VERIFICACIÓN DE SLA - 2025-11-16 08:30:00 ===
   
   Total de tickets activos con SLA: 3
   
   ❌ Ticket #4 - "Problema impresora" - SLA EXCEDIDO hace 2.5 horas
   ⚠️  Ticket #6 - "Actualización software" - SLA vence en 1.2 horas
   ✅ Ticket #5 - "Solicitud acceso" - SLA en 5.2 horas
   
   === RESUMEN ===
   Tickets con SLA excedido: 1
   Tickets por vencer (< 2hrs): 1
   Tickets en buen estado: 1
   
   Tickets ya marcados como "tiempo_excedido": 0
   ```

### Opción 2: Probar en la Aplicación Web

1. **Crear un ticket de prueba con SLA corto:**
   - Accede a `/nuevo/`
   - Crea un ticket normal
   - Como administrador, ve a `/admin/tickets/ticket/`
   - Edita el ticket y modifica `tiempo_limite_resolucion` a una fecha pasada (ej: hace 2 horas)
   - Guarda

2. **Verificar actualización automática:**
   - Accede al dashboard principal (`/`)
   - **Observa**: El contador "SLA Excedido" debe incrementarse
   - **Observa**: El ticket debe aparecer con estado "Tiempo Excedido"
   - Filtra por estado "tiempo_excedido" para ver solo esos tickets

3. **Verificar en métricas:**
   - Accede a `/metricas/`
   - **Observa**: La card "SLA Excedido" debe mostrar el número correcto
   - **Observa**: El porcentaje de cumplimiento de SLA debe ajustarse

### Opción 3: Revisar Logs

```powershell
# Ver últimas líneas del log
Get-Content logs\ticket_coyahue.log -Tail 20

# Buscar entradas relacionadas con SLA
Get-Content logs\ticket_coyahue.log | Select-String "SLA"
```

**Salida esperada:**
```
WARNING 2025-11-16 08:30:12 views Ticket #4 "Problema impresora" cerrado automáticamente por SLA excedido
INFO 2025-11-16 08:30:45 views Ticket #5 creado por admin: "Nueva solicitud"
```

---

## 🔧 Comandos de Gestión Disponibles

### 1. `ver_sla` - Verificación de Estado (Solo Lectura)
```powershell
python manage.py ver_sla
```
- ✅ Muestra estado actual de SLAs
- ✅ No modifica ningún ticket
- ✅ Útil para debugging

### 2. `verificar_sla` - Actualización Manual (Opcional)
```powershell
python manage.py verificar_sla
```
- ⚠️ Modifica tickets excedidos
- ⚠️ Cambia estados a "tiempo_excedido"
- ℹ️ **No necesario** si usas la app web (ya se ejecuta automáticamente)

---

## 📊 Tiempos SLA por Prioridad

| Prioridad | Tiempo Límite | Ejemplo |
|-----------|--------------|---------|
| **Crítica** | 4 horas | Servidor caído |
| **Alta** | 8 horas | Sistema lento |
| **Media** | 24 horas | Solicitud acceso |
| **Baja** | 48 horas | Consulta general |

---

## 🎯 Flujo del Sistema SLA

```
┌─────────────────────────────────────────────────────┐
│ 1. Usuario crea ticket                              │
│    - Estado: "pendiente"                            │
│    - Se calcula tiempo_limite_resolucion            │
│    - Basado en prioridad (4h, 8h, 24h, 48h)        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 2. Admin asigna ticket a técnico                    │
│    - Estado: sigue "pendiente" o cambia a           │
│      "en_progreso"                                  │
│    - Puede modificar SLA personalizado              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 3. Sistema verifica SLA automáticamente             │
│    - Cuando: Al acceder a dashboard o métricas      │
│    - Condición: tiempo_limite < ahora               │
│    - Acción: Cambia estado a "tiempo_excedido"      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 4. Contador actualizado                             │
│    - Dashboard: card "SLA Excedido" incrementa      │
│    - Métricas: card "SLA Excedido" muestra total    │
│    - Logs: Registro de cambio automático            │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ Solución de Problemas

### Problema: "El contador SLA Excedido no aumenta"

**Causa:** La verificación automática solo se ejecuta al acceder al dashboard/métricas.

**Solución:**
1. Accede a la página principal (`/`) o métricas (`/metricas/`)
2. Refresca la página (F5)
3. El contador debe actualizarse

**Alternativa:** Ejecuta manualmente:
```powershell
python manage.py verificar_sla
```

### Problema: "Los tickets no cambian a 'tiempo_excedido'"

**Verificar:**
1. El ticket tiene `tiempo_limite_resolucion` definido:
   ```powershell
   python verificar_sla_rapido.py
   ```

2. El estado es `pendiente` o `en_progreso` (no `resuelto` ni `cerrado`)

3. La fecha límite está en el pasado

**Corrección manual:**
```powershell
# En shell de Django
python manage.py shell

from django.utils import timezone
from tickets.models import Ticket

# Ver tickets problemáticos
tickets = Ticket.objects.filter(
    estado__in=['pendiente', 'en_progreso'],
    tiempo_limite_resolucion__isnull=True
)
print(f"Tickets sin SLA: {tickets.count()}")

# Asignar SLA a un ticket específico
ticket = Ticket.objects.get(id=4)
ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
ticket.save()
```

### Problema: "No veo los logs de SLA"

**Verificar:**
1. La carpeta `logs/` existe:
   ```powershell
   Test-Path logs
   ```

2. Revisar permisos de escritura:
   ```powershell
   Get-Acl logs
   ```

3. Ver contenido del log:
   ```powershell
   Get-Content logs\ticket_coyahue.log -Tail 50
   ```

---

## 📝 Notas Importantes

1. **Verificación Automática**: Se ejecuta **cada vez** que accedes al dashboard o métricas. No requiere configuración adicional.

2. **Rendimiento**: La verificación es eficiente (solo busca tickets activos con SLA vencido). No afecta el rendimiento.

3. **Tickets Resueltos/Cerrados**: No se verifican. El SLA solo aplica a tickets activos.

4. **SLA Personalizado**: Los administradores pueden asignar SLA personalizado al asignar tickets.

5. **Historial Completo**: Todos los cambios de estado por SLA quedan registrados en `HistorialEstado`.

---

## 🚀 Próximos Pasos (Opcional)

Si deseas verificación SLA más frecuente sin acceso a la web:

### Windows (Task Scheduler)
```powershell
# Crear tarea que ejecute cada hora
$action = New-ScheduledTaskAction -Execute "python" -Argument "manage.py verificar_sla" -WorkingDirectory "C:\Phyton\Proyectos\Tercer semestre\Proyecto Gestion de tickets\Proyecto-Gestion-De-Tickets"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "VerificarSLA" -Description "Verificación automática de SLA cada hora"
```

### Linux/Mac (Crontab)
```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar cada hora)
0 * * * * cd /ruta/proyecto && python manage.py verificar_sla >> logs/cron_sla.log 2>&1
```

---

**Última actualización:** 16 de Noviembre de 2025  
**Versión:** 1.1.0
