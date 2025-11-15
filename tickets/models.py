from django.db import models
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

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
    ]
    # Define los niveles de prioridad para los tickets
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    # Campo para el título breve del ticket
    titulo = models.CharField(max_length=200)
    # Campo para la descripción detallada del problema
    descripcion = models.TextField()
    # Estado actual del ticket con valor por defecto 'pendiente'
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    # Prioridad del ticket con valor por defecto 'media'
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='media')
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
    
    def __str__(self):
        return f"{self.titulo} ({self.estado})"

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
    
    def __str__(self):
        if self.estado_anterior:
            return f"{self.ticket.id} - {self.estado_anterior} → {self.estado_nuevo}"
        return f"{self.ticket.id} - {self.estado_nuevo}"

