from django.contrib import admin
from .models import Ticket, Comentario, ArchivoTicket, ArchivoComentario, HistorialEstado, RolPersonalizado, PerfilUsuario, Categoria, Subcategoria, Notificacion


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'fecha_creacion')
    list_filter = ('activa', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('fecha_creacion',)


@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'activa', 'fecha_creacion')
    list_filter = ('categoria', 'activa', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion', 'categoria__nombre')
    readonly_fields = ('fecha_creacion',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'estado', 'prioridad', 'tipo', 'creador', 'asignado_a', 'fecha_creacion')
    list_filter = ('estado', 'prioridad', 'tipo', 'categoria', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion', 'creador__username', 'asignado_a__username')
    readonly_fields = ('fecha_creacion', 'fecha_cierre', 'fecha_primera_respuesta', 'fecha_asignacion')
    list_per_page = 25
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'descripcion', 'tipo', 'categoria', 'subcategoria')
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


@admin.register(RolPersonalizado)
class RolPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'color', 'activo', 'num_usuarios', 'fecha_creacion')
    list_filter = ('activo', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'creado_por')
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'color', 'activo')
        }),
        ('Permisos', {
            'fields': ('puede_ver_metricas', 'puede_ver_todos_tickets', 'puede_asignar_tickets',
                      'puede_cambiar_estado', 'puede_gestionar_usuarios', 'puede_crear_roles')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'creado_por')
        }),
    )
    
    def num_usuarios(self, obj):
        return obj.usuarios.count()
    num_usuarios.short_description = 'Usuarios'


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'departamento', 'cargo', 'rol_personalizado', 'fecha_creacion')
    list_filter = ('departamento', 'rol_personalizado', 'fecha_creacion')
    search_fields = ('user__username', 'user__email', 'departamento', 'cargo')
    readonly_fields = ('fecha_creacion', 'creado_por')
    list_per_page = 25
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información Laboral', {
            'fields': ('telefono', 'departamento', 'cargo', 'ubicacion')
        }),
        ('Rol y Permisos', {
            'fields': ('rol_personalizado',)
        }),
        ('Notificaciones', {
            'fields': ('notificaciones_email', 'notificaciones_whatsapp', 'numero_whatsapp')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'creado_por')
        }),
    )


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'tipo', 'prioridad', 'titulo', 'leida', 'email_enviado', 'whatsapp_enviado', 'fecha_creacion')
    list_filter = ('tipo', 'prioridad', 'leida', 'email_enviado', 'whatsapp_enviado', 'fecha_creacion')
    search_fields = ('titulo', 'mensaje', 'usuario__username', 'ticket__titulo')
    readonly_fields = ('fecha_creacion', 'email_fecha', 'whatsapp_fecha', 'fecha_leida')
    list_per_page = 50
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('usuario', 'ticket', 'tipo', 'prioridad')
        }),
        ('Contenido', {
            'fields': ('titulo', 'mensaje', 'enlace')
        }),
        ('Email', {
            'fields': ('email_enviado', 'email_fecha'),
            'classes': ('collapse',)
        }),
        ('WhatsApp', {
            'fields': ('whatsapp_enviado', 'whatsapp_fecha'),
            'classes': ('collapse',)
        }),
        ('Web', {
            'fields': ('leida', 'fecha_leida'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',)
        }),
    )

