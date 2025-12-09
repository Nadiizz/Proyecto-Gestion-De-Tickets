from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from .models import Ticket


class TimezoneAndTicketTests(TestCase):
	def test_project_timezone_is_local(self):
		"""Verifica que la zona horaria del proyecto esté configurada a America/Santiago."""
		self.assertIn(settings.TIME_ZONE, ['America/Santiago', 'Chile/Continental', 'America/Argentina/Buenos_Aires'])

	def test_ticket_fecha_creacion_is_timezone_aware_and_local(self):
		"""Crear un ticket y comprobar que fecha_creacion es timezone-aware y cercana a now."""
		# Crear un usuario simple
		user = User.objects.create_user(username='tztester', password='test')
		ticket = Ticket.objects.create(
			titulo='Prueba TZ',
			descripcion='Comprobando timezone en fecha_creacion',
			creador=user,
		)

		self.assertIsNotNone(ticket.fecha_creacion)
		# Debe ser timezone-aware
		self.assertIsNotNone(getattr(ticket.fecha_creacion, 'tzinfo', None))

		now_local = timezone.localtime(timezone.now())
		created_local = timezone.localtime(ticket.fecha_creacion)

		# La diferencia entre 'ahora' y la fecha de creación debe ser pequeña (<= 5s)
		diff = abs((now_local - created_local).total_seconds())
		self.assertLessEqual(diff, 5, f'La diferencia entre now y fecha_creacion es demasiado grande: {diff}s')
