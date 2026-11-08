import base64
import io
import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .api_views import obtener_estado_aforo
from .forms import (
    PlanMembresiaForm,
    SocioForm,
    PagoMembresiaForm,
    ClaseGrupalForm,
    ReservaClaseForm,
    ConfiguracionAforoForm,
)
from .models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    RegistroAcceso,
    ClaseGrupal,
    ReservaClase,
)


def generar_qr_base64(contenido: str) -> str:
    """Genera una imagen QR en formato PNG codificada en Base64 usando qrcode[pil]."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(str(contenido))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ==========================================
# 1. DASHBOARD EN TIEMPO REAL
# ==========================================

@login_required
def dashboard_view(request):
    estado_aforo = obtener_estado_aforo()
    ultimos_accesos = (
        RegistroAcceso.objects.select_related('socio')
        .order_by('-fecha_hora')[:10]
    )
    clases_grupales = (
        ClaseGrupal.objects.filter(activa=True)
        .order_by('fecha_hora_inicio')
    )
    resumen_socios = {
        "total": Socio.objects.count(),
        "activos": Socio.objects.filter(estado_membresia='ACTIVA').count(),
        "vencidos": Socio.objects.filter(estado_membresia='VENCIDA').count(),
        "congelados": Socio.objects.filter(estado_membresia='CONGELADA').count(),
    }
    aforo_form = ConfiguracionAforoForm(instance=estado_aforo["config"])

    return render(
        request,
        "core/dashboard.html",
        {
            "estado_aforo": estado_aforo,
            "ultimos_accesos": ultimos_accesos,
            "clases_grupales": clases_grupales,
            "resumen_socios": resumen_socios,
            "aforo_form": aforo_form,
        },
    )


@login_required
def actualizar_aforo_view(request):
    if request.method == "POST":
        estado_aforo = obtener_estado_aforo()
        form = ConfiguracionAforoForm(request.POST, instance=estado_aforo["config"])
        if form.is_valid():
            config = form.save()
            messages.success(
                request,
                f"Configuración de aforo actualizada: {config.nombre_sede} (Máximo: {config.aforo_maximo} personas).",
            )
        else:
            messages.error(request, "No se pudo actualizar la configuración de aforo.")
    return redirect("dashboard")


# ==========================================
# 2. SIMULADOR DE ACCESO QR EN MILISEGUNDOS
# ==========================================

@login_required
def simulador_qr_view(request):
    socios = list(Socio.objects.select_related('plan').order_by('estado_membresia', 'nombre_completo'))
    for socio in socios:
        socio.qr_base64 = generar_qr_base64(str(socio.token_qr))

    estado_aforo = obtener_estado_aforo()
    ultimos_accesos = (
        RegistroAcceso.objects.select_related('socio')
        .order_by('-fecha_hora')[:8]
    )

    return render(
        request,
        "core/simulador_qr.html",
        {
            "socios": socios,
            "estado_aforo": estado_aforo,
            "ultimos_accesos": ultimos_accesos,
        },
    )


@login_required
def socio_qr_png_view(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(str(socio.token_qr))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


# ==========================================
# 3. CRUD DE PLANES, SOCIOS Y PAGOS
# ==========================================

@login_required
def gestion_membresias_view(request):
    planes = PlanMembresia.objects.all().order_by('precio')
    socios = list(Socio.objects.select_related('plan').order_by('nombre_completo'))
    for socio in socios:
        socio.qr_base64 = generar_qr_base64(str(socio.token_qr))

    pagos = PagoMembresia.objects.select_related('socio', 'plan').order_by('-fecha_pago')[:15]

    return render(
        request,
        "core/membresias.html",
        {
            "planes": planes,
            "socios": socios,
            "pagos": pagos,
            "plan_form": PlanMembresiaForm(),
            "socio_form": SocioForm(),
            "pago_form": PagoMembresiaForm(),
        },
    )


@login_required
def plan_crear_view(request):
    if request.method == "POST":
        form = PlanMembresiaForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Plan '{plan.nombre}' creado exitosamente.")
        else:
            messages.error(request, f"Error al crear el plan: {form.errors.as_text()}")
    return redirect("gestion_membresias")


@login_required
def plan_editar_view(request, pk):
    plan = get_object_or_404(PlanMembresia, pk=pk)
    if request.method == "POST":
        form = PlanMembresiaForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Plan '{plan.nombre}' actualizado correctamente.")
            return redirect("gestion_membresias")
        messages.error(request, "Corrija los errores del formulario del plan.")
    else:
        form = PlanMembresiaForm(instance=plan)

    return render(
        request,
        "core/form_editar.html",
        {
            "titulo": f"Editar Plan: {plan.nombre}",
            "subtitulo": "Modifique los parámetros comerciales y de duración del plan de membresía.",
            "form": form,
            "url_volver": "gestion_membresias",
        },
    )


@login_required
def plan_eliminar_view(request, pk):
    plan = get_object_or_404(PlanMembresia, pk=pk)
    if request.method == "POST":
        nombre = plan.nombre
        try:
            plan.delete()
            messages.success(request, f"Plan '{nombre}' eliminado correctamente.")
        except Exception:
            messages.error(
                request,
                f"No se puede eliminar el plan '{nombre}' porque tiene socios o pagos asociados.",
            )
    return redirect("gestion_membresias")


@login_required
def socio_crear_view(request):
    if request.method == "POST":
        form = SocioForm(request.POST)
        if form.is_valid():
            socio = form.save()
            messages.success(
                request,
                f"Socio '{socio.nombre_completo}' registrado con código QR único: {socio.token_qr}",
            )
        else:
            messages.error(request, f"Error al registrar socio: {form.errors.as_text()}")
    return redirect("gestion_membresias")


@login_required
def socio_editar_view(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    if request.method == "POST":
        form = SocioForm(request.POST, instance=socio)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ficha del socio '{socio.nombre_completo}' actualizada.")
            return redirect("gestion_membresias")
        messages.error(request, "Por favor corrija los errores en el formulario del socio.")
    else:
        form = SocioForm(instance=socio)

    return render(
        request,
        "core/form_editar.html",
        {
            "titulo": f"Editar Socio: {socio.nombre_completo}",
            "subtitulo": f"RUT: {socio.rut} | Token QR: {socio.token_qr}",
            "form": form,
            "url_volver": "gestion_membresias",
        },
    )


@login_required
def socio_eliminar_view(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    if request.method == "POST":
        nombre = socio.nombre_completo
        socio.delete()
        messages.warning(request, f"Socio '{nombre}' eliminado del sistema.")
    return redirect("gestion_membresias")


@login_required
def socio_cambiar_estado_view(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado_membresia", "").upper()
        if nuevo_estado in ("ACTIVA", "VENCIDA", "CONGELADA"):
            socio.estado_membresia = nuevo_estado
            socio.save(update_fields=["estado_membresia"])
            messages.info(
                request,
                f"Estado de membresía de '{socio.nombre_completo}' actualizado a {nuevo_estado}.",
            )
    return redirect("gestion_membresias")


@login_required
def pago_registrar_view(request):
    if request.method == "POST":
        form = PagoMembresiaForm(request.POST)
        if form.is_valid():
            pago = form.save()
            socio = pago.socio
            socio.refresh_from_db()
            messages.success(
                request,
                f"Pago registrado por ${pago.monto:,.0f}. Membresía de '{socio.nombre_completo}' "
                f"activada automáticamente (ACTIVA) y extendida hasta el {socio.fecha_vencimiento:%d/%m/%Y}.",
            )
        else:
            messages.error(request, f"Error al registrar el pago: {form.errors.as_text()}")
    return redirect("gestion_membresias")


# ==========================================
# 4. CLASES GRUPALES Y LISTA DE ESPERA
# ==========================================

@login_required
def gestion_clases_view(request):
    clases = list(
        ClaseGrupal.objects.prefetch_related('reservas__socio__plan')
        .order_by('fecha_hora_inicio')
    )
    for clase in clases:
        clase.reservas_confirmadas = [
            r for r in clase.reservas.all() if r.estado in ('CONFIRMADA', 'ASISTIO')
        ]
        clase.reservas_espera = sorted(
            [r for r in clase.reservas.all() if r.estado == 'LISTA_ESPERA'],
            key=lambda x: (x.posicion_espera or 999, x.fecha_reserva),
        )
        clase.reservas_canceladas = [
            r for r in clase.reservas.all() if r.estado == 'CANCELADA'
        ]

    socios_activos = Socio.objects.select_related('plan').order_by('estado_membresia', 'nombre_completo')

    return render(
        request,
        "core/clases.html",
        {
            "clases": clases,
            "socios": socios_activos,
            "clase_form": ClaseGrupalForm(),
            "reserva_form": ReservaClaseForm(),
        },
    )


@login_required
def clase_crear_view(request):
    if request.method == "POST":
        form = ClaseGrupalForm(request.POST)
        if form.is_valid():
            clase = form.save()
            messages.success(
                request,
                f"Clase grupal '{clase.nombre}' creada con cupo máximo de {clase.cupo_maximo} personas.",
            )
        else:
            messages.error(request, f"Error al crear la clase grupal: {form.errors.as_text()}")
    return redirect("gestion_clases")


@login_required
def clase_editar_view(request, pk):
    clase = get_object_or_404(ClaseGrupal, pk=pk)
    if request.method == "POST":
        form = ClaseGrupalForm(request.POST, instance=clase)
        if form.is_valid():
            form.save()
            messages.success(request, f"Clase grupal '{clase.nombre}' actualizada.")
            return redirect("gestion_clases")
        messages.error(request, "Revise los campos del formulario de la clase.")
    else:
        form = ClaseGrupalForm(instance=clase)

    return render(
        request,
        "core/form_editar.html",
        {
            "titulo": f"Editar Clase: {clase.nombre}",
            "subtitulo": f"Instructor: {clase.instructor} | Sala: {clase.sala}",
            "form": form,
            "url_volver": "gestion_clases",
        },
    )


@login_required
def clase_eliminar_view(request, pk):
    clase = get_object_or_404(ClaseGrupal, pk=pk)
    if request.method == "POST":
        nombre = clase.nombre
        clase.delete()
        messages.warning(request, f"Clase grupal '{nombre}' eliminada.")
    return redirect("gestion_clases")


@login_required
def reserva_crear_view(request):
    if request.method == "POST":
        clase_id = request.POST.get("clase")
        socio_id = request.POST.get("socio")
        clase = get_object_or_404(ClaseGrupal, pk=clase_id)
        socio = get_object_or_404(Socio, pk=socio_id)

        try:
            with transaction.atomic():
                # Si existía una reserva CANCELADA previa para el mismo (clase, socio), eliminarla para re-inscribir
                ReservaClase.objects.filter(clase=clase, socio=socio, estado='CANCELADA').delete()
                reserva = ReservaClase.objects.create(clase=clase, socio=socio)

            if reserva.estado == 'CONFIRMADA':
                messages.success(
                    request,
                    f"¡Reserva CONFIRMADA! '{socio.nombre_completo}' tiene su cupo asegurado en '{clase.nombre}'.",
                )
            else:
                messages.warning(
                    request,
                    f"Cupos completos en '{clase.nombre}'. '{socio.nombre_completo}' quedó inscrito "
                    f"automáticamente en LISTA DE ESPERA (Posición #{reserva.posicion_espera}).",
                )
        except ValidationError as exc:
            msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            messages.error(request, f"Reserva rechazada: {msg}")
        except IntegrityError:
            messages.error(
                request,
                f"El socio '{socio.nombre_completo}' ya posee una reserva activa o en espera para '{clase.nombre}'.",
            )

    return redirect("gestion_clases")


@login_required
def reserva_cancelar_view(request, pk):
    reserva = get_object_or_404(ReservaClase.objects.select_related('clase', 'socio'), pk=pk)
    if request.method == "POST":
        clase = reserva.clase
        socio_cancelado = reserva.socio.nombre_completo
        estaba_confirmada = reserva.estado == 'CONFIRMADA'

        # Identificar al #1 en lista de espera antes de cancelar para informar en la alerta
        candidato_promocion = None
        if estaba_confirmada:
            primero_espera = (
                ReservaClase.objects.select_related('socio')
                .filter(clase=clase, estado='LISTA_ESPERA')
                .order_by('posicion_espera', 'fecha_reserva', 'id')
                .first()
            )
            if primero_espera:
                candidato_promocion = primero_espera.socio.nombre_completo

        reserva.cancelar()

        if estaba_confirmada and candidato_promocion:
            messages.success(
                request,
                f"Reserva de '{socio_cancelado}' en '{clase.nombre}' CANCELADA. "
                f"⚡ PROMOCIÓN AUTOMÁTICA: '{candidato_promocion}' (Lista de Espera #1) "
                f"pasó automáticamente a estado CONFIRMADA y se reordenaron las posiciones restantes.",
            )
        else:
            messages.info(
                request,
                f"Reserva de '{socio_cancelado}' en '{clase.nombre}' cancelada correctamente.",
            )

    return redirect("gestion_clases")
