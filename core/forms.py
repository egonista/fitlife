from django import forms
from .models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    ConfiguracionAforo,
    ClaseGrupal,
    ReservaClase,
)
from .validators import validar_y_formatear_rut


class BootstrapFormMixin:
    """Agrega automáticamente clases de Bootstrap 5 a los campos del formulario."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select bg-dark text-light border-secondary'
            else:
                widget.attrs['class'] = 'form-control bg-dark text-light border-secondary'


class PlanMembresiaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PlanMembresia
        fields = ['nombre', 'descripcion', 'precio', 'duracion_dias', 'acceso_clases_grupales', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Beneficios incluidos en el plan...'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej. Plan Mensual Full'}),
        }


class SocioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Socio
        fields = [
            'rut',
            'nombre_completo',
            'email',
            'telefono',
            'plan',
            'estado_membresia',
            'fecha_inicio',
            'fecha_vencimiento',
        ]
        widgets = {
            'rut': forms.TextInput(attrs={'placeholder': 'Ej. 18.234.567-9', 'class': 'input-rut-chileno'}),
            'nombre_completo': forms.TextInput(attrs={'placeholder': 'Nombre y Apellidos'}),
            'email': forms.EmailInput(attrs={'placeholder': 'socio@correo.cl'}),
            'telefono': forms.TextInput(attrs={'placeholder': '+56 9 1234 5678'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '')
        return validar_y_formatear_rut(rut)


class PagoMembresiaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PagoMembresia
        fields = ['socio', 'plan', 'monto', 'metodo_pago', 'comprobante_referencia']
        widgets = {
            'comprobante_referencia': forms.TextInput(attrs={'placeholder': 'Ej. TRANS-994821 / Boleta #104'}),
        }


class ClaseGrupalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ClaseGrupal
        fields = ['nombre', 'instructor', 'sala', 'fecha_hora_inicio', 'duracion_minutos', 'cupo_maximo', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej. Spinning Extremo'}),
            'instructor': forms.TextInput(attrs={'placeholder': 'Nombre del Coach'}),
            'sala': forms.TextInput(attrs={'placeholder': 'Ej. Sala Ciclismo 1'}),
            'fecha_hora_inicio': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_hora_inicio'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']


class ReservaClaseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ReservaClase
        fields = ['clase', 'socio']


class ConfiguracionAforoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracionAforo
        fields = ['nombre_sede', 'aforo_maximo', 'alerta_umbral_porcentaje']
