import uuid
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone


class PlanMembresia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_dias = models.PositiveIntegerField(
        default=30,
        help_text="Duración del plan en días corridos."
    )
    acceso_clases_grupales = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plan de Membresía"
        verbose_name_plural = "Planes de Membresía"
        ordering = ['precio']

    def __str__(self):
        return f"{self.nombre} (${self.precio:,.0f} - {self.duracion_dias} días)"


class Socio(models.Model):
    ESTADOS_MEMBRESIA = [
        ('ACTIVA', 'Activa'),
        ('VENCIDA', 'Vencida'),
        ('CONGELADA', 'Congelada'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='socio'
    )
    rut = models.CharField(max_length=15, unique=True, db_index=True)
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField()
    telefono = models.CharField(max_length=25, blank=True)
    plan = models.ForeignKey(
        PlanMembresia,
        on_delete=models.PROTECT,
        related_name='socios'
    )
    estado_membresia = models.CharField(
        max_length=15,
        choices=ESTADOS_MEMBRESIA,
        default='ACTIVA',
        db_index=True
    )
    fecha_inicio = models.DateField(default=timezone.localdate)
    fecha_vencimiento = models.DateField()
    token_qr = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )

    class Meta:
        verbose_name = "Socio"
        verbose_name_plural = "Socios"
        ordering = ['nombre_completo']

    def __str__(self):
        return f"{self.nombre_completo} ({self.rut}) - {self.estado_membresia}"

    def save(self, *args, **kwargs):
        if not self.fecha_inicio:
            self.fecha_inicio = timezone.localdate()
        if not self.fecha_vencimiento and self.plan_id:
            self.fecha_vencimiento = self.fecha_inicio + timedelta(days=self.plan.duracion_dias)
        super().save(*args, **kwargs)

    def verificar_vigencia(self) -> bool:
        """
        Verifica si la membresía del socio se encuentra vigente.
        Si fecha_vencimiento < hoy, actualiza automáticamente el estado a VENCIDA
        (salvo que esté CONGELADA, o incluso si estaba ACTIVA) y retorna True solo
        si el socio tiene estado ACTIVA y fecha vigente.
        """
        hoy = timezone.localdate()
        if self.fecha_vencimiento and self.fecha_vencimiento < hoy:
            if self.estado_membresia != 'VENCIDA' and self.estado_membresia != 'CONGELADA':
                self.estado_membresia = 'VENCIDA'
                if self.pk:
                    self.save(update_fields=['estado_membresia'])
            return False

        return self.estado_membresia == 'ACTIVA'


class PagoMembresia(models.Model):
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
    ]

    socio = models.ForeignKey(
        Socio,
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    plan = models.ForeignKey(
        PlanMembresia,
        on_delete=models.PROTECT,
        related_name='pagos'
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now)
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        default='TARJETA'
    )
    comprobante_referencia = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Pago de Membresía"
        verbose_name_plural = "Pagos de Membresía"
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Pago #{self.pk} - {self.socio.nombre_completo} - ${self.monto:,.0f}"

    def save(self, *args, **kwargs):
        es_nuevo = self._state.adding
        with transaction.atomic():
            if not self.monto and self.plan_id:
                self.monto = self.plan.precio
            super().save(*args, **kwargs)

            if es_nuevo:
                hoy = timezone.localdate()
                socio = self.socio
                socio.plan = self.plan
                socio.estado_membresia = 'ACTIVA'
                if socio.fecha_vencimiento and socio.fecha_vencimiento >= hoy:
                    socio.fecha_vencimiento = socio.fecha_vencimiento + timedelta(days=self.plan.duracion_dias)
                else:
                    socio.fecha_vencimiento = hoy + timedelta(days=self.plan.duracion_dias)
                socio.save(update_fields=['plan', 'estado_membresia', 'fecha_vencimiento'])


class ConfiguracionAforo(models.Model):
    nombre_sede = models.CharField(max_length=100, default='Sede Central FitLife')
    aforo_maximo = models.PositiveIntegerField(default=50)
    alerta_umbral_porcentaje = models.PositiveIntegerField(default=80)

    class Meta:
        verbose_name = "Configuración de Aforo"
        verbose_name_plural = "Configuraciones de Aforo"

    def __str__(self):
        return f"{self.nombre_sede} (Máx: {self.aforo_maximo} | Alerta: {self.alerta_umbral_porcentaje}%)"


class RegistroAcceso(models.Model):
    TIPOS_MOVIMIENTO = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
    ]

    RESULTADOS_ACCESO = [
        ('PERMITIDO', 'Permitido'),
        ('DENEGADO_VENCIDA', 'Denegado - Membresía Vencida'),
        ('DENEGADO_CONGELADA', 'Denegado - Membresía Congelada'),
        ('DENEGADO_AFORO_COMPLETO', 'Denegado - Aforo Completo'),
        ('DENEGADO_QR_INVALIDO', 'Denegado - QR Inválido'),
    ]

    socio = models.ForeignKey(
        Socio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_acceso'
    )
    codigo_qr_leido = models.CharField(max_length=100, db_index=True)
    tipo_movimiento = models.CharField(
        max_length=10,
        choices=TIPOS_MOVIMIENTO,
        default='ENTRADA'
    )
    resultado = models.CharField(max_length=30, choices=RESULTADOS_ACCESO)
    motivo_detalle = models.CharField(max_length=255, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    tiempo_respuesta_ms = models.FloatField(default=0.0)

    class Meta:
        verbose_name = "Registro de Acceso"
        verbose_name_plural = "Registros de Acceso"
        ordering = ['-fecha_hora']

    def __str__(self):
        socio_str = self.socio.nombre_completo if self.socio else "Desconocido"
        return f"[{self.tipo_movimiento}] {socio_str} - {self.resultado} ({self.fecha_hora:%Y-%m-%d %H:%M:%S})"


class ClaseGrupal(models.Model):
    nombre = models.CharField(max_length=100)
    instructor = models.CharField(max_length=100)
    sala = models.CharField(max_length=80)
    fecha_hora_inicio = models.DateTimeField(db_index=True)
    duracion_minutos = models.PositiveIntegerField(default=60)
    cupo_maximo = models.PositiveIntegerField(default=20)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Clase Grupal"
        verbose_name_plural = "Clases Grupales"
        ordering = ['fecha_hora_inicio']

    def __str__(self):
        return f"{self.nombre} - {self.instructor} ({self.fecha_hora_inicio:%d/%m/%Y %H:%M})"

    @property
    def cupos_ocupados(self) -> int:
        return self.reservas.filter(estado__in=['CONFIRMADA', 'ASISTIO']).count()

    @property
    def cupos_disponibles(self) -> int:
        return max(0, self.cupo_maximo - self.cupos_ocupados)

    @property
    def cantidad_lista_espera(self) -> int:
        return self.reservas.filter(estado='LISTA_ESPERA').count()


class ReservaClase(models.Model):
    ESTADOS_RESERVA = [
        ('CONFIRMADA', 'Confirmada'),
        ('LISTA_ESPERA', 'Lista de Espera'),
        ('CANCELADA', 'Cancelada'),
        ('ASISTIO', 'Asistió'),
    ]

    clase = models.ForeignKey(
        ClaseGrupal,
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    socio = models.ForeignKey(
        Socio,
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_RESERVA,
        default='CONFIRMADA'
    )
    posicion_espera = models.PositiveIntegerField(null=True, blank=True)
    fecha_reserva = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reserva de Clase"
        verbose_name_plural = "Reservas de Clases"
        unique_together = ('clase', 'socio')
        ordering = ['fecha_reserva']

    def __str__(self):
        pos_info = f" (#{self.posicion_espera})" if self.posicion_espera else ""
        return f"{self.socio.nombre_completo} -> {self.clase.nombre} [{self.estado}{pos_info}]"

    def save(self, *args, **kwargs):
        es_nueva = self._state.adding

        with transaction.atomic():
            # Bloquear la fila de la clase para evitar condiciones de carrera en cupos y lista de espera
            clase_bloqueada = ClaseGrupal.objects.select_for_update().get(pk=self.clase_id)

            if es_nueva:
                # Validar que el socio tenga membresía ACTIVA tras verificar vigencia
                tiene_acceso = self.socio.verificar_vigencia()
                if not tiene_acceso or self.socio.estado_membresia != 'ACTIVA':
                    raise ValidationError(
                        f"El socio '{self.socio.nombre_completo}' no puede reservar clases porque su "
                        f"membresía se encuentra {self.socio.estado_membresia}."
                    )

                if self.estado != 'CANCELADA':
                    # Validar que el socio no tenga choque de horario con otra clase ese mismo día/hora
                    inicio_nueva = clase_bloqueada.fecha_hora_inicio
                    fin_nueva = inicio_nueva + timedelta(minutes=clase_bloqueada.duracion_minutos)

                    reservas_socio = (
                        ReservaClase.objects.select_related('clase')
                        .filter(
                            socio=self.socio,
                            estado__in=['CONFIRMADA', 'LISTA_ESPERA', 'ASISTIO'],
                        )
                        .exclude(clase=clase_bloqueada)
                    )
                    for res_actual in reservas_socio:
                        inicio_ext = res_actual.clase.fecha_hora_inicio
                        fin_ext = inicio_ext + timedelta(minutes=res_actual.clase.duracion_minutos)
                        if inicio_nueva < fin_ext and fin_nueva > inicio_ext:
                            inicio_local = timezone.localtime(inicio_ext)
                            fin_local = timezone.localtime(fin_ext)
                            raise ValidationError(
                                f"Choque de horario: '{self.socio.nombre_completo}' ya está inscrito en "
                                f"'{res_actual.clase.nombre}' ({inicio_local:%d/%m/%Y %H:%M} - {fin_local:%H:%M}), "
                                f"que se superpone con el horario de '{clase_bloqueada.nombre}'."
                            )

                    ocupados = ReservaClase.objects.filter(
                        clase=clase_bloqueada,
                        estado__in=['CONFIRMADA', 'ASISTIO']
                    ).count()

                    if ocupados < clase_bloqueada.cupo_maximo:
                        self.estado = 'CONFIRMADA'
                        self.posicion_espera = None
                    else:
                        self.estado = 'LISTA_ESPERA'
                        max_pos = (
                            ReservaClase.objects.filter(
                                clase=clase_bloqueada,
                                estado='LISTA_ESPERA'
                            ).aggregate(max_p=Max('posicion_espera'))['max_p']
                            or 0
                        )
                        self.posicion_espera = max_pos + 1

                super().save(*args, **kwargs)
            else:
                reserva_previa = (
                    ReservaClase.objects.select_for_update()
                    .filter(pk=self.pk)
                    .first()
                )
                estado_anterior = reserva_previa.estado if reserva_previa else None

                if self.estado == 'CANCELADA':
                    self.posicion_espera = None

                super().save(*args, **kwargs)

                if estado_anterior == 'CONFIRMADA' and self.estado == 'CANCELADA':
                    self._promover_y_reordenar_lista_espera(clase_bloqueada)
                elif estado_anterior == 'LISTA_ESPERA' and self.estado == 'CANCELADA':
                    self._reordenar_lista_espera(clase_bloqueada)

    def cancelar(self):
        """
        Cancela la reserva actual y, si estaba CONFIRMADA, promueve automáticamente
        al primer socio en LISTA_ESPERA y reordena las posiciones restantes.
        """
        with transaction.atomic():
            self.estado = 'CANCELADA'
            self.posicion_espera = None
            self.save()

    @staticmethod
    def _promover_y_reordenar_lista_espera(clase: ClaseGrupal):
        """
        Promueve al socio con menor posicion_espera en LISTA_ESPERA a estado CONFIRMADA
        y reordena correlativamente las posiciones restantes (1, 2, 3...).
        """
        en_espera = list(
            ReservaClase.objects.select_for_update()
            .filter(clase=clase, estado='LISTA_ESPERA')
            .order_by('posicion_espera', 'fecha_reserva', 'id')
        )
        if not en_espera:
            return

        # Promover al primero de la lista de espera
        primero = en_espera[0]
        primero.estado = 'CONFIRMADA'
        primero.posicion_espera = None
        ReservaClase.objects.filter(pk=primero.pk).update(
            estado='CONFIRMADA',
            posicion_espera=None
        )

        # Reordenar correlativamente a los restantes en lista de espera
        for nueva_posicion, reserva_restante in enumerate(en_espera[1:], start=1):
            if reserva_restante.posicion_espera != nueva_posicion:
                ReservaClase.objects.filter(pk=reserva_restante.pk).update(
                    posicion_espera=nueva_posicion
                )

    @staticmethod
    def _reordenar_lista_espera(clase: ClaseGrupal):
        """
        Reordena correlativamente las posiciones de la lista de espera (1, 2, 3...)
        cuando alguien que estaba en LISTA_ESPERA cancela su reserva.
        """
        en_espera = list(
            ReservaClase.objects.select_for_update()
            .filter(clase=clase, estado='LISTA_ESPERA')
            .order_by('posicion_espera', 'fecha_reserva', 'id')
        )
        for nueva_posicion, reserva_restante in enumerate(en_espera, start=1):
            if reserva_restante.posicion_espera != nueva_posicion:
                ReservaClase.objects.filter(pk=reserva_restante.pk).update(
                    posicion_espera=nueva_posicion
                )
