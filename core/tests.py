from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    ConfiguracionAforo,
    RegistroAcceso,
    ClaseGrupal,
    ReservaClase,
)


class FitLifeDomainModelTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.plan = PlanMembresia.objects.create(
            nombre="Plan Full Mensual",
            descripcion="Acceso total a sala de máquinas y clases grupales",
            precio=Decimal("35000.00"),
            duracion_dias=30,
            acceso_clases_grupales=True,
            activo=True,
        )
        self.clase = ClaseGrupal.objects.create(
            nombre="Spinning Pro",
            instructor="Carlos Muñoz",
            sala="Sala Ciclismo 1",
            fecha_hora_inicio=timezone.now() + timedelta(days=1),
            duracion_minutos=45,
            cupo_maximo=2,
            activa=True,
        )

    def _crear_socio(self, idx, estado="ACTIVA", dias_vencimiento=15):
        return Socio.objects.create(
            rut=f"1000000{idx}-{idx}",
            nombre_completo=f"Socio Prueba {idx}",
            email=f"socio{idx}@fitlife.cl",
            telefono=f"+5691234567{idx}",
            plan=self.plan,
            estado_membresia=estado,
            fecha_inicio=self.hoy - timedelta(days=15),
            fecha_vencimiento=self.hoy + timedelta(days=dias_vencimiento),
        )

    def test_verificar_vigencia_actualiza_a_vencida_y_pago_reactiva(self):
        socio = self._crear_socio(1, estado="ACTIVA", dias_vencimiento=-1)
        self.assertFalse(socio.verificar_vigencia())
        socio.refresh_from_db()
        self.assertEqual(socio.estado_membresia, "VENCIDA")

        # Registrar un pago debe activar y extender fecha_vencimiento por 30 días
        PagoMembresia.objects.create(
            socio=socio,
            plan=self.plan,
            monto=self.plan.precio,
            metodo_pago="TARJETA",
            comprobante_referencia="TRX-001",
        )
        socio.refresh_from_db()
        self.assertEqual(socio.estado_membresia, "ACTIVA")
        self.assertEqual(socio.fecha_vencimiento, self.hoy + timedelta(days=30))
        self.assertTrue(socio.verificar_vigencia())

    def test_bloqueo_reserva_socio_vencido_o_congelado(self):
        socio_vencido = self._crear_socio(2, estado="ACTIVA", dias_vencimiento=-2)
        with self.assertRaises(ValidationError):
            ReservaClase.objects.create(clase=self.clase, socio=socio_vencido)

        socio_congelado = self._crear_socio(3, estado="CONGELADA", dias_vencimiento=20)
        with self.assertRaises(ValidationError):
            ReservaClase.objects.create(clase=self.clase, socio=socio_congelado)

    def test_cupos_lista_espera_y_promocion_automatica_al_cancelar(self):
        s1 = self._crear_socio(4)
        s2 = self._crear_socio(5)
        s3 = self._crear_socio(6)
        s4 = self._crear_socio(7)

        # Cupo máximo = 2 -> Primeros 2 quedan CONFIRMADA
        r1 = ReservaClase.objects.create(clase=self.clase, socio=s1)
        r2 = ReservaClase.objects.create(clase=self.clase, socio=s2)
        self.assertEqual(r1.estado, "CONFIRMADA")
        self.assertEqual(r2.estado, "CONFIRMADA")
        self.assertEqual(self.clase.cupos_ocupados, 2)
        self.assertEqual(self.clase.cupos_disponibles, 0)

        # Los siguientes 2 entran a LISTA_ESPERA en posición 1 y 2
        r3 = ReservaClase.objects.create(clase=self.clase, socio=s3)
        r4 = ReservaClase.objects.create(clase=self.clase, socio=s4)
        self.assertEqual(r3.estado, "LISTA_ESPERA")
        self.assertEqual(r3.posicion_espera, 1)
        self.assertEqual(r4.estado, "LISTA_ESPERA")
        self.assertEqual(r4.posicion_espera, 2)
        self.assertEqual(self.clase.cantidad_lista_espera, 2)

        # Cancelar r1 (CONFIRMADA) promueve a r3 a CONFIRMADA y reordena r4 a posición 1
        r1.cancelar()
        r1.refresh_from_db()
        r3.refresh_from_db()
        r4.refresh_from_db()

        self.assertEqual(r1.estado, "CANCELADA")
        self.assertIsNone(r1.posicion_espera)
        self.assertEqual(r3.estado, "CONFIRMADA")
        self.assertIsNone(r3.posicion_espera)
        self.assertEqual(r4.estado, "LISTA_ESPERA")
        self.assertEqual(r4.posicion_espera, 1)
        self.assertEqual(self.clase.cupos_ocupados, 2)
        self.assertEqual(self.clase.cantidad_lista_espera, 1)

    def test_admin_panel_personalizado_y_acciones_masivas(self):
        admin_user = User.objects.create_superuser(
            username="admin_fitlife",
            email="admin@fitlife.cl",
            password="Password123!",
        )
        self.client.force_login(admin_user)

        s1 = self._crear_socio(8, estado="ACTIVA")
        s2 = self._crear_socio(9, estado="CONGELADA")
        r1 = ReservaClase.objects.create(clase=self.clase, socio=s1)
        RegistroAcceso.objects.create(
            socio=s1,
            codigo_qr_leido=str(s1.token_qr),
            tipo_movimiento="ENTRADA",
            resultado="PERMITIDO",
            tiempo_respuesta_ms=14.5,
        )
        ConfiguracionAforo.objects.create(nombre_sede="Sede Central", aforo_maximo=50)

        # Verificar renderizado de base_site.html e índice de administración
        resp_index = self.client.get(reverse("admin:index"))
        self.assertEqual(resp_index.status_code, 200)
        self.assertContains(resp_index, "FitLife — Administración Central")
        self.assertContains(resp_index, "Dashboard en Tiempo Real")
        self.assertContains(resp_index, "Simulador de Acceso QR")

        # Verificar changelists personalizados con format_html
        for model_name in ("socio", "clasegrupal", "reservaclase", "registroacceso", "planmembresia"):
            resp = self.client.get(reverse(f"admin:core_{model_name}_changelist"))
            self.assertEqual(resp.status_code, 200)

        # Probar acción masiva en SocioAdmin: Congelar membresías seleccionadas
        self.client.post(
            reverse("admin:core_socio_changelist"),
            {"action": "congelar_membresias", "_selected_action": [s1.pk]},
        )
        s1.refresh_from_db()
        self.assertEqual(s1.estado_membresia, "CONGELADA")

        # Probar acción masiva en SocioAdmin: Activar membresías seleccionadas
        self.client.post(
            reverse("admin:core_socio_changelist"),
            {"action": "activar_membresias", "_selected_action": [s1.pk, s2.pk]},
        )
        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertEqual(s1.estado_membresia, "ACTIVA")
        self.assertEqual(s2.estado_membresia, "ACTIVA")

        # Probar acción en ReservaClaseAdmin: Cancelar reservas seleccionadas y promover lista de espera
        s3 = self._crear_socio(10, estado="ACTIVA")
        r2 = ReservaClase.objects.create(clase=self.clase, socio=s2)
        r3 = ReservaClase.objects.create(clase=self.clase, socio=s3)
        self.assertEqual(r3.estado, "LISTA_ESPERA")

        self.client.post(
            reverse("admin:core_reservaclase_changelist"),
            {"action": "cancelar_reservas_y_promover_espera", "_selected_action": [r1.pk]},
        )
        r1.refresh_from_db()
        r3.refresh_from_db()
        self.assertEqual(r1.estado, "CANCELADA")
        self.assertEqual(r3.estado, "CONFIRMADA")

    def test_api_validar_qr_y_dashboard_aforo_tiempo_real(self):
        user = User.objects.create_user(username="operador", password="Valorant-1")
        self.client.force_login(user)

        ConfiguracionAforo.objects.create(nombre_sede="Sede Central", aforo_maximo=2, alerta_umbral_porcentaje=50)
        s_activo = self._crear_socio(11, estado="ACTIVA", dias_vencimiento=20)
        s_vencido = self._crear_socio(12, estado="ACTIVA", dias_vencimiento=-5)
        s_congelado = self._crear_socio(13, estado="CONGELADA", dias_vencimiento=15)

        # 1. Entrada permitida para socio activo
        resp_ok = self.client.post(
            reverse("api_validar_qr"),
            data={"token_qr": str(s_activo.token_qr), "tipo_movimiento": "ENTRADA"},
            content_type="application/json",
        )
        self.assertEqual(resp_ok.status_code, 200)
        body_ok = resp_ok.json()
        self.assertTrue(body_ok["permitido"])
        self.assertEqual(body_ok["resultado"], "PERMITIDO")
        self.assertEqual(body_ok["aforo_actual"], 1)
        self.assertGreaterEqual(body_ok["tiempo_respuesta_ms"], 0.0)

        # 2. Entrada denegada por membresía vencida (actualizada automáticamente por verificar_vigencia)
        resp_venc = self.client.post(
            reverse("api_validar_qr"),
            data={"token_qr": str(s_vencido.token_qr), "tipo_movimiento": "ENTRADA"},
            content_type="application/json",
        )
        self.assertEqual(resp_venc.status_code, 403)
        self.assertEqual(resp_venc.json()["resultado"], "DENEGADO_VENCIDA")

        # 3. Entrada denegada por membresía congelada
        resp_cong = self.client.post(
            reverse("api_validar_qr"),
            data={"token_qr": str(s_congelado.token_qr), "tipo_movimiento": "ENTRADA"},
            content_type="application/json",
        )
        self.assertEqual(resp_cong.status_code, 403)
        self.assertEqual(resp_cong.json()["resultado"], "DENEGADO_CONGELADA")

        # 4. QR inválido
        resp_inv = self.client.post(
            reverse("api_validar_qr"),
            data={"token_qr": "token-inexistente", "tipo_movimiento": "ENTRADA"},
            content_type="application/json",
        )
        self.assertEqual(resp_inv.status_code, 403)
        self.assertEqual(resp_inv.json()["resultado"], "DENEGADO_QR_INVALIDO")

        # 5. Consultar endpoint de dashboard en tiempo real
        resp_dash = self.client.get(reverse("api_dashboard_aforo"))
        self.assertEqual(resp_dash.status_code, 200)
        dash_data = resp_dash.json()
        self.assertEqual(dash_data["aforo_actual"], 1)
        self.assertEqual(dash_data["aforo_maximo"], 2)
        self.assertEqual(len(dash_data["ultimos_accesos"]), 4)

        # 6. Verificar vistas web principales protegidas por sesión
        for url_name in ("dashboard", "simulador_qr", "gestion_membresias", "gestion_clases"):
            r = self.client.get(reverse(url_name))
            self.assertEqual(r.status_code, 200)

        # 7. Verificar página personalizada de Error 404
        r_404 = self.client.get("/simulador-qr/404")
        self.assertEqual(r_404.status_code, 404)
        self.assertContains(r_404, "Página no disponible", status_code=404)
        self.assertContains(r_404, "Volver al Inicio", status_code=404)



