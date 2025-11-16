from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import os

# Constantes para validación de archivos
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.xlsx', '.xls', '.zip']


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
    # Área o departamento afectado por el problema
    area_afectada = models.CharField(max_length=100)
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
    
    def calcular_tiempo_limite_sla(self):
        """Calcula el tiempo límite SLA basado en la prioridad"""
        horas_por_prioridad = {
            'critica': 4,   # 4 horas
            'alta': 8,      # 8 horas
            'media': 24,    # 24 horas
            'baja': 48,     # 48 horas
        }
        horas = horas_por_prioridad.get(self.prioridad, 24)
        from datetime import timedelta
        return self.fecha_creacion + timedelta(hours=horas)

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
