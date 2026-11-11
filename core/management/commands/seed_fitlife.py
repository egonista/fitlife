from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    ConfiguracionAforo,
    RegistroAcceso,
    ClaseGrupal,
    ReservaClase,
)


class Command(BaseCommand):
    help = "Carga datos iniciales de demostración para FitLife en PostgreSQL."

    def handle(self, *args, **options):
        with transaction.atomic():
            hoy = timezone.localdate()
            ahora = timezone.now()

            # 1. Usuarios del sistema (admin y recepcion)
            admin_user, created_admin = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@fitlife.cl",
                    "first_name": "Administrador",
                    "last_name": "FitLife",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.set_password("Valorant-1")
            admin_user.save()

            recepcion_user, created_rec = User.objects.get_or_create(
                username="recepcion",
                defaults={
                    "email": "recepcion@fitlife.cl",
                    "first_name": "Operador",
                    "last_name": "Recepción",
                    "is_staff": True,
                    "is_superuser": False,
                },
            )
            recepcion_user.is_staff = True
            recepcion_user.set_password("Valorant-1")
            recepcion_user.save()

            # 2. Configuración de Aforo
            ConfiguracionAforo.objects.all().delete()
            ConfiguracionAforo.objects.create(
                nombre_sede="Sede Central FitLife",
                aforo_maximo=50,
                alerta_umbral_porcentaje=80,
            )

            # Limpiar datos previos del dominio para carga limpia y reproducible
            ReservaClase.objects.all().delete()
            RegistroAcceso.objects.all().delete()
            PagoMembresia.objects.all().delete()
            ClaseGrupal.objects.all().delete()
            Socio.objects.all().delete()
            PlanMembresia.objects.all().delete()

            # 3. Planes de Membresía
            plan_mensual = PlanMembresia.objects.create(
                nombre="Plan Mensual Full",
                descripcion="Acceso libre a sala de musculación, cardio y todas las clases grupales por 30 días.",
                precio=Decimal("35000.00"),
                duracion_dias=30,
                acceso_clases_grupales=True,
                activo=True,
            )
            plan_trimestral = PlanMembresia.objects.create(
                nombre="Plan Trimestral Pro",
                descripcion="90 días de acceso total, evaluación nutricional y reserva prioritaria en clases.",
                precio=Decimal("90000.00"),
                duracion_dias=90,
                acceso_clases_grupales=True,
                activo=True,
            )
            plan_anual = PlanMembresia.objects.create(
                nombre="Plan Anual VIP",
                descripcion="365 días de acceso ilimitado multisede, casillero personal y todas las disciplinas.",
                precio=Decimal("320000.00"),
                duracion_dias=365,
                acceso_clases_grupales=True,
                activo=True,
            )

            # 4. Socios de Prueba (con RUT chileno Módulo 11 válido)
            s_camila = Socio.objects.create(
                rut="18.234.567-9",
                nombre_completo="Camila Rojas",
                email="camila.rojas@fitlife.cl",
                telefono="+56 9 8111 2233",
                plan=plan_anual,
                estado_membresia="ACTIVA",
                fecha_inicio=hoy - timedelta(days=40),
                fecha_vencimiento=hoy + timedelta(days=325),
            )
            s_matias = Socio.objects.create(
                rut="19.876.543-0",
                nombre_completo="Matías Fernández",
                email="matias.fernandez@fitlife.cl",
                telefono="+56 9 8222 3344",
                plan=plan_trimestral,
                estado_membresia="ACTIVA",
                fecha_inicio=hoy - timedelta(days=15),
                fecha_vencimiento=hoy + timedelta(days=75),
            )
            s_valentina = Socio.objects.create(
                rut="20.456.789-1",
                nombre_completo="Valentina Soto",
                email="valentina.soto@fitlife.cl",
                telefono="+56 9 8333 4455",
                plan=plan_mensual,
                estado_membresia="ACTIVA",
                fecha_inicio=hoy - timedelta(days=5),
                fecha_vencimiento=hoy + timedelta(days=25),
            )
            s_diego = Socio.objects.create(
                rut="16.543.210-K",
                nombre_completo="Diego Morales",
                email="diego.morales@fitlife.cl",
                telefono="+56 9 8444 5566",
                plan=plan_mensual,
                estado_membresia="ACTIVA",
                fecha_inicio=hoy - timedelta(days=45),
                fecha_vencimiento=hoy + timedelta(days=5),
            )
            s_francisca = Socio.objects.create(
                rut="17.654.321-3",
                nombre_completo="Francisca Herrera",
                email="francisca.herrera@fitlife.cl",
                telefono="+56 9 8555 6677",
                plan=plan_trimestral,
                estado_membresia="ACTIVA",
                fecha_inicio=hoy - timedelta(days=100),
                fecha_vencimiento=hoy + timedelta(days=5),
            )
            s_sebastian = Socio.objects.create(
                rut="15.321.654-1",
                nombre_completo="Sebastián Vargas",
                email="sebastian.vargas@fitlife.cl",
                telefono="+56 9 8666 7788",
                plan=plan_trimestral,
                estado_membresia="CONGELADA",
                fecha_inicio=hoy - timedelta(days=20),
                fecha_vencimiento=hoy + timedelta(days=70),
            )

            # Registrar pagos históricos para los socios activos
            PagoMembresia.objects.create(
                socio=s_camila,
                plan=plan_anual,
                monto=plan_anual.precio,
                metodo_pago="TARJETA",
                comprobante_referencia="WEBPAY-900142",
            )
            PagoMembresia.objects.create(
                socio=s_matias,
                plan=plan_trimestral,
                monto=plan_trimestral.precio,
                metodo_pago="TRANSFERENCIA",
                comprobante_referencia="TRF-774120",
            )
            PagoMembresia.objects.create(
                socio=s_valentina,
                plan=plan_mensual,
                monto=plan_mensual.precio,
                metodo_pago="EFECTIVO",
                comprobante_referencia="BOL-10058",
            )

            # 5. Clases Grupales
            clase_spinning = ClaseGrupal.objects.create(
                nombre="Spinning Extremo",
                instructor="Coach Roberto Díaz",
                sala="Sala Ciclismo Indoor",
                fecha_hora_inicio=ahora + timedelta(hours=3),
                duracion_minutos=50,
                cupo_maximo=3,
                activa=True,
            )
            clase_yoga = ClaseGrupal.objects.create(
                nombre="Yoga Flow",
                instructor="Instructora Andrea Silva",
                sala="Estudio Mind & Body",
                fecha_hora_inicio=ahora + timedelta(hours=5),
                duracion_minutos=60,
                cupo_maximo=12,
                activa=True,
            )
            clase_crossfit = ClaseGrupal.objects.create(
                nombre="CrossFit WOD",
                instructor="Coach Nicolás Bravo",
                sala="Box Funcional Principal",
                fecha_hora_inicio=ahora + timedelta(hours=7),
                duracion_minutos=60,
                cupo_maximo=15,
                activa=True,
            )

            # Inscribir 5 socios en Spinning Extremo (cupo máximo = 3):
            # Los primeros 3 quedan en CONFIRMADA y los siguientes 2 quedan en LISTA_ESPERA (#1 y #2)
            ReservaClase.objects.create(clase=clase_spinning, socio=s_camila)     # CONFIRMADA (1/3)
            ReservaClase.objects.create(clase=clase_spinning, socio=s_diego)      # CONFIRMADA (2/3)
            ReservaClase.objects.create(clase=clase_spinning, socio=s_francisca)  # CONFIRMADA (3/3)
            ReservaClase.objects.create(clase=clase_spinning, socio=s_matias)     # LISTA_ESPERA #1
            ReservaClase.objects.create(clase=clase_spinning, socio=s_valentina)  # LISTA_ESPERA #2

            # Otras reservas en Yoga Flow y CrossFit WOD
            ReservaClase.objects.create(clase=clase_yoga, socio=s_camila)
            ReservaClase.objects.create(clase=clase_yoga, socio=s_valentina)
            ReservaClase.objects.create(clase=clase_crossfit, socio=s_matias)
            ReservaClase.objects.create(clase=clase_crossfit, socio=s_camila)

            # Ahora dejamos a Diego y Francisca con su membresía VENCIDA (cumpliendo 3 ACTIVA, 2 VENCIDA, 1 CONGELADA)
            Socio.objects.filter(pk=s_diego.pk).update(
                estado_membresia="VENCIDA",
                fecha_vencimiento=hoy - timedelta(days=10),
            )
            Socio.objects.filter(pk=s_francisca.pk).update(
                estado_membresia="VENCIDA",
                fecha_vencimiento=hoy - timedelta(days=4),
            )

            # 6. Registros de Acceso QR iniciales del día para el Dashboard en Tiempo Real
            RegistroAcceso.objects.create(
                socio=s_camila,
                codigo_qr_leido=str(s_camila.token_qr),
                tipo_movimiento="ENTRADA",
                resultado="PERMITIDO",
                motivo_detalle="Acceso autorizado. ¡Bienvenido/a a entrenar, Camila Rojas!",
                tiempo_respuesta_ms=2.41,
            )
            RegistroAcceso.objects.create(
                socio=s_matias,
                codigo_qr_leido=str(s_matias.token_qr),
                tipo_movimiento="ENTRADA",
                resultado="PERMITIDO",
                motivo_detalle="Acceso autorizado. ¡Bienvenido/a a entrenar, Matías Fernández!",
                tiempo_respuesta_ms=1.87,
            )
            RegistroAcceso.objects.create(
                socio=s_valentina,
                codigo_qr_leido=str(s_valentina.token_qr),
                tipo_movimiento="ENTRADA",
                resultado="PERMITIDO",
                motivo_detalle="Acceso autorizado. ¡Bienvenido/a a entrenar, Valentina Soto!",
                tiempo_respuesta_ms=1.95,
            )
            RegistroAcceso.objects.create(
                socio=s_diego,
                codigo_qr_leido=str(s_diego.token_qr),
                tipo_movimiento="ENTRADA",
                resultado="DENEGADO_VENCIDA",
                motivo_detalle="Membresía VENCIDA. Regularice su pago en recepción para habilitar el torniquete.",
                tiempo_respuesta_ms=2.12,
            )
            RegistroAcceso.objects.create(
                socio=s_sebastian,
                codigo_qr_leido=str(s_sebastian.token_qr),
                tipo_movimiento="ENTRADA",
                resultado="DENEGADO_CONGELADA",
                motivo_detalle="Membresía CONGELADA temporalmente. Solicite la reactivación de su plan.",
                tiempo_respuesta_ms=1.74,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de FitLife cargados exitosamente en PostgreSQL:\n"
                "  - Usuarios: admin / Valorant-1 (Superusuario), recepcion / Valorant-1 (Operador)\n"
                "  - Planes: 3 (Mensual Full, Trimestral Pro, Anual VIP)\n"
                "  - Socios: 6 (3 ACTIVA, 2 VENCIDA, 1 CONGELADA)\n"
                "  - Clases: Spinning Extremo (3/3 confirmados + 2 en Lista de Espera #1 y #2), Yoga Flow, CrossFit WOD"
            )
        )
