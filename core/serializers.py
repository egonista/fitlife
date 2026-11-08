from rest_framework import serializers
from .models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    ConfiguracionAforo,
    RegistroAcceso,
    ClaseGrupal,
    ReservaClase,
)


class PlanMembresiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanMembresia
        fields = '__all__'


class SocioSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source='plan.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_membresia_display', read_only=True)

    class Meta:
        model = Socio
        fields = [
            'id',
            'user',
            'rut',
            'nombre_completo',
            'email',
            'telefono',
            'plan',
            'plan_nombre',
            'estado_membresia',
            'estado_display',
            'fecha_inicio',
            'fecha_vencimiento',
            'token_qr',
        ]
        read_only_fields = ['token_qr']


class PagoMembresiaSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source='socio.nombre_completo', read_only=True)
    plan_nombre = serializers.CharField(source='plan.nombre', read_only=True)

    class Meta:
        model = PagoMembresia
        fields = [
            'id',
            'socio',
            'socio_nombre',
            'plan',
            'plan_nombre',
            'monto',
            'fecha_pago',
            'metodo_pago',
            'comprobante_referencia',
        ]


class ConfiguracionAforoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionAforo
        fields = '__all__'


class RegistroAccesoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.SerializerMethodField()
    socio_rut = serializers.SerializerMethodField()
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)

    class Meta:
        model = RegistroAcceso
        fields = [
            'id',
            'socio',
            'socio_nombre',
            'socio_rut',
            'codigo_qr_leido',
            'tipo_movimiento',
            'resultado',
            'resultado_display',
            'motivo_detalle',
            'fecha_hora',
            'tiempo_respuesta_ms',
        ]

    def get_socio_nombre(self, obj):
        return obj.socio.nombre_completo if obj.socio else "QR No Reconocido"

    def get_socio_rut(self, obj):
        return obj.socio.rut if obj.socio else "—"


class ClaseGrupalSerializer(serializers.ModelSerializer):
    cupos_ocupados = serializers.IntegerField(read_only=True)
    cupos_disponibles = serializers.IntegerField(read_only=True)
    cantidad_lista_espera = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClaseGrupal
        fields = [
            'id',
            'nombre',
            'instructor',
            'sala',
            'fecha_hora_inicio',
            'duracion_minutos',
            'cupo_maximo',
            'cupos_ocupados',
            'cupos_disponibles',
            'cantidad_lista_espera',
            'activa',
        ]


class ReservaClaseSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source='socio.nombre_completo', read_only=True)
    socio_rut = serializers.CharField(source='socio.rut', read_only=True)
    clase_nombre = serializers.CharField(source='clase.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = ReservaClase
        fields = [
            'id',
            'clase',
            'clase_nombre',
            'socio',
            'socio_nombre',
            'socio_rut',
            'estado',
            'estado_display',
            'posicion_espera',
            'fecha_reserva',
        ]
        read_only_fields = ['posicion_espera', 'fecha_reserva']
