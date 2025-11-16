from django.contrib import admin
from .models import Ticket, Comentario, ArchivoTicket, ArchivoComentario, HistorialEstado


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'estado', 'prioridad', 'tipo', 'creador', 'asignado_a', 'fecha_creacion')
    list_filter = ('estado', 'prioridad', 'tipo', 'area_afectada', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion', 'creador__username', 'asignado_a__username')
    readonly_fields = ('fecha_creacion', 'fecha_cierre', 'fecha_primera_respuesta', 'fecha_asignacion')
    list_per_page = 25
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'descripcion', 'tipo', 'area_afectada')
        }),
        ('Estado y Prioridad', {
            'fields': ('estado', 'prioridad')
        }),
        ('Asignación', {
            'fields': ('creador', 'asignado_a')
        }),
        ('SLA y Métricas', {
            'fields': ('fecha_creacion', 'fecha_asignacion', 'fecha_primera_respuesta', 
                      'fecha_cierre', 'tiempo_limite_resolucion', 'fue_reabierto', 'numero_escalamientos')
        }),
        ('Satisfacción', {
            'fields': ('calificacion_satisfaccion',)
        }),
    )


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'autor', 'fecha', 'mensaje_preview')
    list_filter = ('fecha',)
    search_fields = ('mensaje', 'autor__username', 'ticket__titulo')
    readonly_fields = ('fecha',)
    list_per_page = 50
    
    def mensaje_preview(self, obj):
        return obj.mensaje[:50] + '...' if len(obj.mensaje) > 50 else obj.mensaje
    mensaje_preview.short_description = 'Vista Previa'


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'estado_anterior', 'estado_nuevo', 'cambiado_por', 'fecha')
    list_filter = ('estado_nuevo', 'fecha')
    search_fields = ('ticket__titulo', 'cambiado_por__username', 'comentario')
    readonly_fields = ('fecha',)
    list_per_page = 50
    date_hierarchy = 'fecha'


@admin.register(ArchivoTicket)
class ArchivoTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_archivo', 'ticket', 'subido_por', 'fecha_subida', 'extension')
    list_filter = ('fecha_subida',)
    search_fields = ('nombre_archivo', 'ticket__titulo', 'subido_por__username')
    readonly_fields = ('fecha_subida',)
    list_per_page = 50


@admin.register(ArchivoComentario)
class ArchivoComentarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_archivo', 'comentario', 'subido_por', 'fecha_subida', 'extension')
    list_filter = ('fecha_subida',)
    search_fields = ('nombre_archivo', 'subido_por__username')
    readonly_fields = ('fecha_subida',)
    list_per_page = 50
