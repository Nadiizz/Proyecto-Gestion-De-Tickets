from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('', views.ticket_list, name='ticket_list'),
    path('nuevo/', views.ticket_create, name='ticket_create'),
    path('asignar/<int:ticket_id>/', views.asignar_ticket, name='asignar_ticket'),
    path('estado/<int:ticket_id>/', views.cambiar_estado, name='cambiar_estado'),
    path('ticket/<int:ticket_id>/', views.ticket_detalle, name='ticket_detalle'),
]
