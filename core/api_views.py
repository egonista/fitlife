import time
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    ConfiguracionAforo,
    RegistroAcceso,
    ClaseGrupal,
    ReservaClase,
)
from .serializers import (
    PlanMembresiaSerializer,
    SocioSerializer,
    PagoMembresiaSerializer,
    RegistroAccesoSerializer,
    ClaseGrupalSerializer,
    ReservaClaseSerializer,
)


def obtener_estado_aforo():
    """
    Calcula en tiempo real el aforo actual en las instalaciones a partir de los
    movimientos de ENTRADA y SALIDA con resultado PERMITIDO del día en curso.
    """
    config = ConfiguracionAforo.objects.first()
    if not config:
        config = ConfiguracionAforo.objects.create(
            nombre_sede="Sede Central FitLife",
            aforo_maximo=50,
            alerta_umbral_porcentaje=80,
        )

    hoy = timezone.localdate()
    registros_hoy = RegistroAcceso.objects.filter(
        resultado='PERMITIDO',
        fecha_hora__date=hoy,
    )
    entradas = registros_hoy.filter(tipo_movimiento='ENTRADA').count()
    salidas = registros_hoy.filter(tipo_movimiento='SALIDA').count()
    aforo_actual = max(0, entradas - salidas)

    aforo_maximo = config.aforo_maximo or 1
    porcentaje_ocupacion = min(100, round((aforo_actual / aforo_maximo) * 100, 1))

    if aforo_actual >= config.aforo_maximo:
        nivel_alerta = "CRITICO"
    elif porcentaje_ocupacion >= config.alerta_umbral_porcentaje:
        nivel_alerta = "ADVERTENCIA"
    else:
        nivel_alerta = "NORMAL"

    return {
        "config": config,
        "nombre_sede": config.nombre_sede,
        "aforo_actual": aforo_actual,
        "aforo_maximo": config.aforo_maximo,
        "cupos_disponibles": max(0, config.aforo_maximo - aforo_actual),
        "porcentaje_ocupacion": porcentaje_ocupacion,
        "alerta_umbral_porcentaje": config.alerta_umbral_porcentaje,
        "nivel_alerta": nivel_alerta,
    }


# ==========================================
# MODEL VIEWSETS (DRF)
# ==========================================

class PlanMembresiaViewSet(viewsets.ModelViewSet):
    queryset = PlanMembresia.objects.all()
    serializer_class = PlanMembresiaSerializer
    permission_classes = [IsAuthenticated]


class SocioViewSet(viewsets.ModelViewSet):
    queryset = Socio.objects.select_related('plan').all()
    serializer_class = SocioSerializer
    permission_classes = [IsAuthenticated]


class PagoMembresiaViewSet(viewsets.ModelViewSet):
    queryset = PagoMembresia.objects.select_related('socio', 'plan').all()
    serializer_class = PagoMembresiaSerializer
    permission_classes = [IsAuthenticated]


class ClaseGrupalViewSet(viewsets.ModelViewSet):
    queryset = ClaseGrupal.objects.all()
    serializer_class = ClaseGrupalSerializer
    permission_classes = [IsAuthenticated]


class ReservaClaseViewSet(viewsets.ModelViewSet):
    queryset = ReservaClase.objects.select_related('clase', 'socio').all()
    serializer_class = ReservaClaseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages})

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        reserva = self.get_object()
        reserva.cancelar()
        return Response(
            {
                "mensaje": "Reserva cancelada y lista de espera actualizada automáticamente.",
                "reserva": ReservaClaseSerializer(reserva).data,
            },
            status=status.HTTP_200_OK,
        )


class RegistroAccesoViewSet(viewsets.ModelViewSet):
    queryset = RegistroAcceso.objects.select_related('socio').all()
    serializer_class = RegistroAccesoSerializer
    permission_classes = [IsAuthenticated]


# ==========================================
# ENDPOINTS OPERATIVOS EN TIEMPO REAL
# ==========================================

class ValidarAccesoQRAPIView(APIView):
    """
    POST /api/accesos/validar-qr/
    Valida un código QR en milisegundos verificando existencia del token,
    vigencia y estado de la membresía, y disponibilidad de aforo en tiempo real.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        inicio_perf = time.perf_counter()

        token_raw = str(
            request.data.get('token_qr')
            or request.data.get('codigo_qr')
            or ''
        ).strip()
        tipo_movimiento = str(
            request.data.get('tipo_movimiento', 'ENTRADA')
        ).strip().upper()

        if tipo_movimiento not in ('ENTRADA', 'SALIDA'):
            tipo_movimiento = 'ENTRADA'

        estado_aforo = obtener_estado_aforo()
        aforo_actual = estado_aforo['aforo_actual']
        aforo_maximo = estado_aforo['aforo_maximo']

        socio = None
        if token_raw:
            try:
                uuid_valido = uuid.UUID(token_raw)
                socio = Socio.objects.select_related('plan').filter(token_qr=uuid_valido).first()
            except (ValueError, TypeError):
                # Permitir también lectura de QR que contenga el RUT o nombre del socio
                socio = (
                    Socio.objects.select_related('plan').filter(rut__iexact=token_raw).first()
                    or Socio.objects.select_related('plan').filter(nombre_completo__iexact=token_raw).first()
                )

        if not socio:
            permitido = False
            resultado = 'DENEGADO_QR_INVALIDO'
            motivo = "El código QR escaneado no corresponde a ningún socio registrado en FitLife."
        else:
            # Ejecutar verificación automática de vigencia por fecha
            socio.verificar_vigencia()

            if socio.estado_membresia == 'VENCIDA':
                permitido = False
                resultado = 'DENEGADO_VENCIDA'
                motivo = (
                    f"Membresía VENCIDA el {socio.fecha_vencimiento:%d/%m/%Y}. "
                    "Regularice su pago en recepción para habilitar el torniquete."
                )
            elif socio.estado_membresia == 'CONGELADA':
                permitido = False
                resultado = 'DENEGADO_CONGELADA'
                motivo = (
                    "Membresía CONGELADA temporalmente. "
                    "Solicite la reactivación de su plan para ingresar."
                )
            elif tipo_movimiento == 'ENTRADA' and aforo_actual >= aforo_maximo:
                permitido = False
                resultado = 'DENEGADO_AFORO_COMPLETO'
                motivo = (
                    f"Aforo máximo alcanzado ({aforo_actual}/{aforo_maximo} personas). "
                    "Ingreso bloqueado preventivamente por seguridad sanitaria."
                )
            else:
                permitido = True
                resultado = 'PERMITIDO'
                if tipo_movimiento == 'ENTRADA':
                    motivo = f"Acceso autorizado. ¡Bienvenido/a a entrenar, {socio.nombre_completo}!"
                else:
                    motivo = f"Salida registrada correctamente. ¡Hasta pronto, {socio.nombre_completo}!"

        tiempo_ms = round((time.perf_counter() - inicio_perf) * 1000, 2)

        registro = RegistroAcceso.objects.create(
            socio=socio,
            codigo_qr_leido=token_raw[:100] if token_raw else "QR_VACIO",
            tipo_movimiento=tipo_movimiento,
            resultado=resultado,
            motivo_detalle=motivo,
            tiempo_respuesta_ms=tiempo_ms,
        )

        # Recalcular aforo tras registrar el movimiento
        nuevo_estado_aforo = obtener_estado_aforo()

        socio_data = None
        if socio:
            socio_data = {
                "id": socio.id,
                "rut": socio.rut,
                "nombre_completo": socio.nombre_completo,
                "email": socio.email,
                "plan": socio.plan.nombre if socio.plan else "Sin Plan",
                "estado_membresia": socio.estado_membresia,
                "fecha_vencimiento": socio.fecha_vencimiento.strftime("%Y-%m-%d"),
                "token_qr": str(socio.token_qr),
            }

        http_status = status.HTTP_200_OK if permitido else status.HTTP_403_FORBIDDEN
        return Response(
            {
                "permitido": permitido,
                "resultado": resultado,
                "resultado_display": registro.get_resultado_display(),
                "tipo_movimiento": tipo_movimiento,
                "motivo": motivo,
                "socio": socio_data,
                "aforo_actual": nuevo_estado_aforo["aforo_actual"],
                "aforo_maximo": nuevo_estado_aforo["aforo_maximo"],
                "porcentaje_ocupacion": nuevo_estado_aforo["porcentaje_ocupacion"],
                "nivel_alerta": nuevo_estado_aforo["nivel_alerta"],
                "tiempo_respuesta_ms": tiempo_ms,
                "fecha_hora": timezone.localtime(registro.fecha_hora).strftime("%H:%M:%S"),
            },
            status=http_status,
        )


class DashboardAforoAPIView(APIView):
    """
    GET /api/dashboard/aforo/
    Devuelve en JSON el estado de aforo en tiempo real, nivel de alerta,
    últimos 10 accesos QR con su latencia en milisegundos y estado de clases grupales.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        estado_aforo = obtener_estado_aforo()

        ultimos_registros = (
            RegistroAcceso.objects.select_related('socio')
            .order_by('-fecha_hora')[:10]
        )
        ultimos_accesos_data = [
            {
                "id": reg.id,
                "socio_nombre": reg.socio.nombre_completo if reg.socio else "QR Inválido / Desconocido",
                "socio_rut": reg.socio.rut if reg.socio else "—",
                "codigo_qr_leido": reg.codigo_qr_leido,
                "tipo_movimiento": reg.tipo_movimiento,
                "permitido": reg.resultado == 'PERMITIDO',
                "resultado": reg.resultado,
                "resultado_display": reg.get_resultado_display(),
                "motivo_detalle": reg.motivo_detalle,
                "fecha_hora": timezone.localtime(reg.fecha_hora).strftime("%H:%M:%S"),
                "tiempo_respuesta_ms": round(reg.tiempo_respuesta_ms, 2),
            }
            for reg in ultimos_registros
        ]

        clases = ClaseGrupal.objects.filter(activa=True).order_by('fecha_hora_inicio')
        clases_data = []
        for clase in clases:
            ocupados = clase.cupos_ocupados
            maximo = clase.cupo_maximo or 1
            porcentaje_clase = min(100, round((ocupados / maximo) * 100, 1))
            clases_data.append(
                {
                    "id": clase.id,
                    "nombre": clase.nombre,
                    "instructor": clase.instructor,
                    "sala": clase.sala,
                    "fecha_hora_inicio": timezone.localtime(clase.fecha_hora_inicio).strftime("%d/%m/%Y %H:%M"),
                    "duracion_minutos": clase.duracion_minutos,
                    "cupo_maximo": clase.cupo_maximo,
                    "cupos_ocupados": ocupados,
                    "cupos_disponibles": clase.cupos_disponibles,
                    "cantidad_lista_espera": clase.cantidad_lista_espera,
                    "porcentaje_ocupacion": porcentaje_clase,
                }
            )

        resumen_socios = {
            "total": Socio.objects.count(),
            "activos": Socio.objects.filter(estado_membresia='ACTIVA').count(),
            "vencidos": Socio.objects.filter(estado_membresia='VENCIDA').count(),
            "congelados": Socio.objects.filter(estado_membresia='CONGELADA').count(),
        }

        return Response(
            {
                "nombre_sede": estado_aforo["nombre_sede"],
                "aforo_actual": estado_aforo["aforo_actual"],
                "aforo_maximo": estado_aforo["aforo_maximo"],
                "cupos_disponibles_gimnasio": estado_aforo["cupos_disponibles"],
                "porcentaje_ocupacion": estado_aforo["porcentaje_ocupacion"],
                "alerta_umbral_porcentaje": estado_aforo["alerta_umbral_porcentaje"],
                "nivel_alerta": estado_aforo["nivel_alerta"],
                "resumen_socios": resumen_socios,
                "ultimos_accesos": ultimos_accesos_data,
                "clases_grupales": clases_data,
                "timestamp_servidor": timezone.localtime(timezone.now()).strftime("%H:%M:%S"),
            },
            status=status.HTTP_200_OK,
        )
