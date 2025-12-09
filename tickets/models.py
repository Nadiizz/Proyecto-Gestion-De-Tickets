from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta
import os

# Constantes para validación de archivos
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.xlsx', '.xls', '.zip']

# Transiciones de estado permitidas en el flujo de trabajo
# Flujo principal: Pendiente → En Progreso → Resuelto → Cerrado
# 
# PENDIENTE: Ticket nuevo, esperando que un técnico lo tome
# EN_PROGRESO: Técnico está trabajando en el ticket
# RESUELTO: Técnico terminó, esperando confirmación del usuario
# CERRADO: Usuario confirmó solución o se cerró automáticamente
# TIEMPO_EXCEDIDO: SLA superado (puede reabrirse)
#
TRANSICIONES_ESTADO_VALIDAS = {
    'pendiente': ['en_progreso'],  # Técnico toma el ticket
    'en_progreso': ['resuelto', 'pendiente'],  # Resuelve o devuelve a pendiente si necesita más info
    'resuelto': ['cerrado', 'en_progreso'],  # Usuario confirma o técnico retoma si no quedó bien
    'cerrado': ['pendiente'],  # Solo admin puede reabrir un ticket cerrado
    'tiempo_excedido': ['pendiente', 'en_progreso'],  # Puede reabrirse
}


def validar_tamano_archivo(archivo):
    """Valida que el archivo no exceda el tamaño máximo"""
    if archivo.size > MAX_FILE_SIZE:
        raise ValidationError(f'El archivo no debe exceder {MAX_FILE_SIZE / (1024*1024):.0f} MB')


def validar_extension_archivo(archivo):
    """Valida que la extensión del archivo sea permitida"""
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'Extensión no permitida. Solo se permiten: {", ".join(ALLOWED_EXTENSIONS)}'
        )


# Categorías y Subcategorías
class Categoria(models.Model):
    """Modelo para categorías generales de tickets (Finanzas, RRHH, etc.)"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
    
    def __str__(self):
        return self.nombre


class Subcategoria(models.Model):
    """Modelo para subcategorías específicas dentro de cada categoría"""
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = 'Subcategoría'
        verbose_name_plural = 'Subcategorías'
        unique_together = ('categoria', 'nombre')
    
    def __str__(self):
        return f"{self.categoria.nombre} - {self.nombre}"


# Create your models here.

# Define la estructura principal de datos del sistema de tickets
# Modelo Ticket almacena la información central de cada solicitud
# Modelo Comentario gestiona la comunicación alrededor de cada ticket
# Modelo HistorialEstado registra todos los cambios de estado del ticket

# Tickets
class Ticket(models.Model):
    # Define los estados posibles que puede tener un ticket
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En progreso'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
        ('tiempo_excedido', 'Tiempo Excedido'),
    ]
    # Define los niveles de prioridad para los tickets
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    # Tipos de ticket para métricas
    TIPOS = [
        ('incidencia', 'Incidencia'),
        ('solicitud', 'Solicitud'),
        ('problema', 'Problema'),
        ('cambio', 'Cambio'),
    ]
    
    # Campo para el título breve del ticket
    titulo = models.CharField(max_length=200)
    # Campo para la descripción detallada del problema
    descripcion = models.TextField()
    # Estado actual del ticket con valor por defecto 'pendiente'
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    # Prioridad del ticket con valor por defecto 'media'
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='media')
    # Tipo de ticket para categorización
    tipo = models.CharField(max_length=20, choices=TIPOS, default='incidencia')
    # Categoría del ticket (Finanzas, RRHH, etc.)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    # Subcategoría del ticket (más específica)
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    # Usuario que creó el ticket (relación muchos a uno)
    creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_creados')
    # Técnico asignado al ticket (puede ser nulo si no está asignado)
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_asignados')
    # Fecha automática de creación del ticket
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Fecha de cierre del ticket (se llena cuando se resuelve)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    
    # Campos para SLA y métricas
    fecha_primera_respuesta = models.DateTimeField(null=True, blank=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    tiempo_limite_resolucion = models.DateTimeField(null=True, blank=True)  # SLA deadline
    fue_reabierto = models.BooleanField(default=False)
    numero_escalamientos = models.IntegerField(default=0)
    
    # Campos para detección y validación automática de prioridad
    prioridad_auto_detectada = models.CharField(max_length=10, choices=PRIORIDADES, null=True, blank=True)
    prioridad_validada = models.BooleanField(default=False)  # True si un supervisor validó la prioridad
    validado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_validados')
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    
    # Satisfacción del cliente (1-5)
    calificacion_satisfaccion = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        indexes = [
            models.Index(fields=['estado', 'fecha_creacion']),
            models.Index(fields=['asignado_a', 'estado']),
            models.Index(fields=['creador']),
        ]
    
    def __str__(self):
        return f"{self.titulo} ({self.estado})"
    
    def calcular_tiempo_primera_respuesta(self):
        """Calcula el tiempo entre creación y primera respuesta en horas"""
        if self.fecha_primera_respuesta:
            delta = self.fecha_primera_respuesta - self.fecha_creacion
            return delta.total_seconds() / 3600  # Retorna en horas
        return None
    
    def calcular_tiempo_resolucion(self):
        """Calcula el tiempo total de resolución en horas"""
        if self.fecha_cierre:
            delta = self.fecha_cierre - self.fecha_creacion
            return delta.total_seconds() / 3600  # Retorna en horas
        return None
    
    def verificar_sla_excedido(self):
        """Verifica si el SLA ha sido excedido"""
        if self.tiempo_limite_resolucion and self.estado not in ['resuelto', 'cerrado', 'tiempo_excedido']:
            return timezone.now() > self.tiempo_limite_resolucion
        return False
    
    def calcular_tiempo_limite_sla(self, horas_personalizadas=None):
        """Calcula el tiempo límite SLA basado en la prioridad o valor personalizado"""
        if horas_personalizadas:
            # SLA personalizado: usar las horas especificadas
            return self.fecha_creacion + timedelta(hours=int(horas_personalizadas))
        
        # SLA por defecto: basado en la prioridad
        horas_por_prioridad = {
            'critica': 4,   # 4 horas
            'alta': 8,      # 8 horas
            'media': 24,    # 24 horas
            'baja': 48,     # 48 horas
        }
        horas = horas_por_prioridad.get(self.prioridad, 24)
        return self.fecha_creacion + timedelta(hours=horas)
    
    def puede_cambiar_estado_a(self, nuevo_estado):
        """Valida si la transición de estado es permitida"""
        estado_actual = self.estado
        
        # Casos especiales: transiciones permitidas siempre por admin
        if estado_actual == nuevo_estado:
            return True  # Cambio a mismo estado (no-op)
        
        # Verificar si la transición está permitida
        transiciones_permitidas = TRANSICIONES_ESTADO_VALIDAS.get(estado_actual, [])
        
        if nuevo_estado not in transiciones_permitidas:
            return False
        
        return True
    
    def obtener_transiciones_permitidas(self):
        """Retorna la lista de transiciones permitidas desde el estado actual"""
        return TRANSICIONES_ESTADO_VALIDAS.get(self.estado, [])

# Comentarios
class Comentario(models.Model):
    # Ticket al que pertenece el comentario (relación muchos a uno)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comentarios')
    # Usuario que escribió el comentario
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    # Contenido del comentario
    mensaje = models.TextField()
    # Fecha automática de creación del comentario
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['fecha']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'

    def __str__(self):
        return f"Comentario de {self.autor.username} en {self.ticket.titulo}"
    

# Historial de estado
class HistorialEstado(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='historial_estados')
    cambiado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    estado_nuevo = models.CharField(max_length=50)  # Campo mínimo necesario
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Campos opcionales (agrega si los necesitas)
    estado_anterior = models.CharField(max_length=50, blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['fecha']
        verbose_name = 'Historial de Estado'
        verbose_name_plural = 'Historiales de Estado'
    
    def __str__(self):
        if self.estado_anterior:
            return f"{self.ticket.id} - {self.estado_anterior} → {self.estado_nuevo}"
        return f"{self.ticket.id} - {self.estado_nuevo}"


# Archivos adjuntos para tickets
class ArchivoTicket(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(
        upload_to='tickets/archivos/%Y/%m/%d/',
        validators=[validar_tamano_archivo, validar_extension_archivo]
    )
    nombre_archivo = models.CharField(max_length=255)
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Archivo de Ticket'
        verbose_name_plural = 'Archivos de Tickets'
    
    def __str__(self):
        return f"{self.nombre_archivo} - Ticket #{self.ticket.id}"
    
    def extension(self):
        """Retorna la extensión del archivo"""
        return os.path.splitext(self.nombre_archivo)[1].lower()
    
    def es_imagen(self):
        """Verifica si el archivo es una imagen"""
        extensiones_imagen = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.extension() in extensiones_imagen


# Archivos adjuntos para comentarios
class ArchivoComentario(models.Model):
    comentario = models.ForeignKey(Comentario, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(
        upload_to='comentarios/archivos/%Y/%m/%d/',
        validators=[validar_tamano_archivo, validar_extension_archivo]
    )
    nombre_archivo = models.CharField(max_length=255)
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Archivo de Comentario'
        verbose_name_plural = 'Archivos de Comentarios'
    
    def __str__(self):
        return f"{self.nombre_archivo} - Comentario #{self.comentario.id}"
    
    def extension(self):
        """Retorna la extensión del archivo"""
        return os.path.splitext(self.nombre_archivo)[1].lower()
    
    def es_imagen(self):
        """Verifica si el archivo es una imagen"""
        extensiones_imagen = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.extension() in extensiones_imagen



# ============================================
# MODELOS PARA GESTIÓN AVANZADA DE USUARIOS
# ============================================

class RolPersonalizado(models.Model):
    """Roles personalizados con permisos granulares"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3498db')
    
    # Permisos específicos
    puede_ver_metricas = models.BooleanField(default=False)
    puede_ver_todos_tickets = models.BooleanField(default=False)
    puede_asignar_tickets = models.BooleanField(default=False)
    puede_cambiar_estado = models.BooleanField(default=False)
    puede_gestionar_usuarios = models.BooleanField(default=False)
    puede_crear_roles = models.BooleanField(default=False)
    puede_validar_prioridad = models.BooleanField(default=False)  # Permiso para validar prioridades auto-detectadas
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='roles_creados')
    
    class Meta:
        verbose_name = 'Rol Personalizado'
        verbose_name_plural = 'Roles Personalizados'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class PerfilUsuario(models.Model):
    """Perfil extendido de usuario con información adicional"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfilusuario')
    telefono = models.CharField(max_length=20, blank=True)
    departamento = models.CharField(max_length=100, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    ubicacion = models.CharField(max_length=200, blank=True)
    foto_perfil = models.ImageField(upload_to='fotos_perfil/', null=True, blank=True)
    
    rol_personalizado = models.ForeignKey(
        RolPersonalizado, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='usuarios'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='perfiles_creados'
    )
    
    # Preferencias de notificaciones
    notificaciones_email = models.BooleanField(default=True)
    notificaciones_whatsapp = models.BooleanField(default=False)
    numero_whatsapp = models.CharField(max_length=20, blank=True, help_text="Formato: +57301234567")
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"


# ==================== SISTEMA DE NOTIFICACIONES ====================

class Notificacion(models.Model):
    """Modelo para notificaciones a usuarios"""
    TIPOS_NOTIFICACION = [
        ('ticket_creado', 'Ticket Creado'),
        ('ticket_asignado', 'Ticket Asignado'),  # Para el técnico: "Te asignaron un ticket"
        ('tu_ticket_asignado', 'Tu Ticket Fue Asignado'),  # Para el creador: "Tu ticket fue asignado a X"
        ('ticket_reasignado', 'Ticket Reasignado'),  # Cuando se reasigna de un técnico a otro
        ('ticket_comentario', 'Nuevo Comentario'),
        ('estado_cambio', 'Cambio de Estado'),
        ('ticket_en_progreso', 'Ticket En Progreso'),  # Cuando el técnico empieza a trabajar
        ('ticket_resuelto', 'Ticket Resuelto'),
        ('ticket_cerrado', 'Ticket Cerrado'),
        ('ticket_cerrado_exito', 'Ticket Cerrado Exitosamente'),  # Para el técnico: el usuario confirmó la solución
        ('solucion_rechazada', 'Solución Rechazada'),  # Para el técnico: el usuario dice que no funcionó
        ('ticket_reabierto', 'Ticket Reabierto'),  # Cuando se reabre un ticket cerrado
        ('ticket_requiere_validacion', 'Ticket Requiere Validación'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True, related_name='notificaciones')
    
    tipo = models.CharField(max_length=50, choices=TIPOS_NOTIFICACION)
    prioridad = models.CharField(max_length=20, choices=Ticket.PRIORIDADES, default='media')  # Reutiliza PRIORIDADES de Ticket
    
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    
    # Estados de envío
    email_enviado = models.BooleanField(default=False)
    email_fecha = models.DateTimeField(null=True, blank=True)
    
    whatsapp_enviado = models.BooleanField(default=False)
    whatsapp_fecha = models.DateTimeField(null=True, blank=True)
    
    # Estado de visualización en web
    leida = models.BooleanField(default=False)
    fecha_leida = models.DateTimeField(null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enlace = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        indexes = [
            models.Index(fields=['usuario', '-fecha_creacion']),
            models.Index(fields=['usuario', 'leida']),
        ]
    
    def __str__(self):
        return f"{self.titulo} → {self.usuario.username}"


# ==================== SISTEMA DE FAQs DINÁMICO ====================

class CategoriaFAQ(models.Model):
    """Categorías para organizar las preguntas frecuentes"""
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=10, default='❓', help_text="Emoji para la categoría")
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0, help_text="Orden de visualización")
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='categorias_faq_creadas')
    
    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría de FAQ'
        verbose_name_plural = 'Categorías de FAQs'
    
    def __str__(self):
        return f"{self.icono} {self.nombre}"
    
    def preguntas_activas(self):
        """Retorna solo las preguntas activas de esta categoría"""
        return self.preguntas.filter(activa=True)


class PreguntaFAQ(models.Model):
    """Preguntas frecuentes con sus respuestas"""
    categoria = models.ForeignKey(CategoriaFAQ, on_delete=models.CASCADE, related_name='preguntas')
    pregunta = models.CharField(max_length=300)
    respuesta = models.TextField(help_text="Puedes usar HTML básico para formato (ul, li, strong, etc.)")
    imagen = models.ImageField(upload_to='faqs/imagenes/', blank=True, null=True, help_text="Imagen ilustrativa opcional")
    orden = models.PositiveIntegerField(default=0, help_text="Orden dentro de la categoría")
    activa = models.BooleanField(default=True)
    vistas = models.PositiveIntegerField(default=0, help_text="Cantidad de veces que se ha visto esta pregunta")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='preguntas_faq_creadas')
    
    class Meta:
        ordering = ['categoria', 'orden', 'pregunta']
        verbose_name = 'Pregunta FAQ'
        verbose_name_plural = 'Preguntas FAQs'
    
    def __str__(self):
        return self.pregunta[:80]
    
    def incrementar_vistas(self):
        """Incrementa el contador de vistas"""
        self.vistas += 1
        self.save(update_fields=['vistas'])


class BusquedaFAQ(models.Model):
    """Registro de búsquedas de usuarios en FAQs para análisis"""
    termino = models.CharField(max_length=200)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='busquedas_faq')
    encontro_resultados = models.BooleanField(default=False)
    cantidad_resultados = models.PositiveIntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Búsqueda de FAQ'
        verbose_name_plural = 'Búsquedas de FAQs'
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['termino']),
        ]
    
    def __str__(self):
        estado = "✅" if self.encontro_resultados else "❌"
        return f"{estado} '{self.termino}' - {self.fecha.strftime('%d/%m/%Y %H:%M')}"


def imagen_faq_path(instance, filename):
    """Genera la ruta para guardar imágenes de FAQs"""
    import uuid
    ext = filename.split('.')[-1]
    nuevo_nombre = f"{uuid.uuid4().hex[:12]}.{ext}"
    return f"faqs/imagenes/{nuevo_nombre}"


class ImagenFAQ(models.Model):
    """Imágenes que pueden ser usadas en las respuestas de FAQs"""
    imagen = models.ImageField(upload_to=imagen_faq_path, verbose_name="Imagen")
    nombre_original = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=200, blank=True, help_text="Texto alternativo para accesibilidad")
    subida_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='imagenes_faq')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Imagen FAQ'
        verbose_name_plural = 'Imágenes FAQs'
    
    def __str__(self):
        return self.nombre_original or f"Imagen {self.id}"
    
    @property
    def url(self):
        return self.imagen.url if self.imagen else ''
