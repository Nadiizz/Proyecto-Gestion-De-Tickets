from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
import re

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label='Nombre de usuario',
        help_text='Requerido. 150 caracteres o menos. Solo letras, números y @/./+/-/_'
    )
    email = forms.EmailField(
        required=True,
        label='Correo electrónico',
        help_text='Debe ser un correo de dominio @coyahue.com o @coyahue.cl'
    )
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput,
        help_text='Tu contraseña debe contener al menos 8 caracteres y no puede ser solo números.'
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput,
        help_text='Ingresa la misma contraseña para verificar.'
    )
    TIPO_USUARIO = [
        ('', 'Selecciona tu tipo de usuario'),
        ('usuario', 'Usuario Regular'),
        ('tecnico', 'Técnico'),
    ]
    tipo_usuario = forms.ChoiceField(
        choices=TIPO_USUARIO,
        widget=forms.Select(attrs={
            'class': 'custom-select',
            'style': 'background-color: #f8f9fa;'
        }),
        label='Tipo de Usuario'
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "tipo_usuario")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar si el dominio es válido usando expresiones regulares
            pattern = r'@coyahue\.(com|cl)$'
            if not re.search(pattern, email):
                raise ValidationError(
                    'El correo electrónico debe ser de dominio @coyahue.com o @coyahue.cl'
                )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        
        if commit:
            user.save()
            # Asignar el usuario al grupo correspondiente
            tipo_usuario = self.cleaned_data.get('tipo_usuario')
            if tipo_usuario == 'tecnico':
                grupo = Group.objects.get(name='Técnico')
            else:
                grupo = Group.objects.get(name='Usuario')
            user.groups.add(grupo)
            
        return user
