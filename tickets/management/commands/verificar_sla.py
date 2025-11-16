"""
Comando de Django para verificar y actualizar tickets que excedieron el SLA.
Este comando debe ejecutarse periódicamente (cada hora recomendado) usando cron/task scheduler.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from tickets.models import Ticket, HistorialEstado


class Command(BaseCommand):
    help = 'Verifica tickets que excedieron el tiempo SLA y los cierra automáticamente'

    def handle(self, *args, **options):
        # Buscar tickets activos que excedieron el SLA
        tickets_excedidos = Ticket.objects.filter(
            estado__in=['pendiente', 'en_progreso'],
            tiempo_limite_resolucion__lt=timezone.now()
        )

        count = 0
        for ticket in tickets_excedidos:
            estado_anterior = ticket.estado
            ticket.estado = 'tiempo_excedido'
            ticket.fecha_cierre = timezone.now()
            ticket.save()

            # Registrar en el historial
            HistorialEstado.objects.create(
                ticket=ticket,
                cambiado_por=ticket.asignado_a if ticket.asignado_a else ticket.creador,
                estado_anterior=estado_anterior,
                estado_nuevo='tiempo_excedido',
                comentario='Ticket cerrado automáticamente por exceder el tiempo límite SLA'
            )

            count += 1
            self.stdout.write(
                self.style.WARNING(
                    f'Ticket #{ticket.id} "{ticket.titulo}" cerrado por SLA excedido'
                )
            )

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No se encontraron tickets con SLA excedido')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Se cerraron {count} ticket(s) por SLA excedido')
            )
