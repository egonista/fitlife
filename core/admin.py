from django.contrib import admin, messages
from django.utils.html import format_html
from .models import (
    PlanMembresia,
    Socio,
    PagoMembresia,
    ConfiguracionAforo,
    RegistroAcceso,
    ClaseGrupal,
    ReservaClase,
)

# Personalización global del Administrador de Django
admin.site.site_header = "FitLife — Administración Central"
admin.site.site_title = "FitLife Admin"
admin.site.index_title = "Panel de Control Operativo y Membresías"


# ==========================================
# INLINES
# ==========================================

class PagoMembresiaInline(admin.TabularInline):
    model = PagoMembresia
    extra = 0
    fields = ('plan', 'monto', 'metodo_pago', 'fecha_pago', 'comprobante_referencia')
    readonly_fields = ('fecha_pago',)
    show_change_link = True


class ReservaClaseInline(admin.TabularInline):
    model = ReservaClase
    extra = 0
    fields = ('clase', 'socio', 'estado', 'posicion_espera', 'fecha_reserva')
    readonly_fields = ('posicion_espera', 'fecha_reserva')
    show_change_link = True


# ==========================================
# MODEL ADMINS
# ==========================================

@admin.register(PlanMembresia)
class PlanMembresiaAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'precio_formateado',
        'duracion_dias',
        'acceso_clases_grupales',
        'activo',
    )
    list_filter = ('acceso_clases_grupales', 'activo')
    search_fields = ('nombre', 'descripcion')
    list_editable = ('acceso_clases_grupales', 'activo')

    @admin.display(description="Precio", ordering="precio")
    def precio_formateado(self, obj):
        return format_html(
            '<span style="font-weight: 600; color: #10b981;">${}</span>',
            f"{obj.precio:,.0f}".replace(",", "."),
        )


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = (
        'rut',
        'nombre_completo',
        'plan',
        'badge_estado_membresia',
        'fecha_vencimiento',
        'token_qr',
    )
    list_filter = ('estado_membresia', 'plan')
    search_fields = ('rut', 'nombre_completo', 'email', 'token_qr')
    readonly_fields = ('token_qr',)
    inlines = [PagoMembresiaInline, ReservaClaseInline]
    actions = [
        'activar_membresias',
        'congelar_membresias',
        'marcar_como_vencidas',
    ]
    fieldsets = (
        ('Identificación del Socio', {
            'fields': ('user', 'rut', 'nombre_completo', 'email', 'telefono')
        }),
        ('Membresía y Acceso QR', {
            'fields': ('plan', 'estado_membresia', 'fecha_inicio', 'fecha_vencimiento', 'token_qr')
        }),
    )

    @admin.display(description="Estado Membresía", ordering="estado_membresia")
    def badge_estado_membresia(self, obj):
        estilos = {
            'ACTIVA': ('#10b981', '#ecfdf5', '#065f46', 'ACTIVA'),
            'VENCIDA': ('#ef4444', '#fef2f2', '#991b1b', 'VENCIDA'),
            'CONGELADA': ('#3b82f6', '#eff6ff', '#1e40af', 'CONGELADA'),
        }
        borde, fondo, texto, etiqueta = estilos.get(
            obj.estado_membresia,
            ('#6b7280', '#f3f4f6', '#374151', obj.estado_membresia)
        )
        return format_html(
            '<span style="display:inline-block; padding:3px 10px; border-radius:9999px; '
            'font-size:11px; font-weight:700; letter-spacing:0.4px; '
            'background-color:{}; color:{}; border:1px solid {};">{}</span>',
            fondo,
            texto,
            borde,
            etiqueta,
        )

    @admin.display(description="Token QR", ordering="token_qr")
    def token_qr_corto(self, obj):
        return format_html(
            '<code style="background:#1e293b; color:#38bdf8; padding:2px 6px; '
            'border-radius:4px; font-size:11px;">{}</code>',
            str(obj.token_qr),
        )

    @admin.action(description="Activar membresías seleccionadas")
    def activar_membresias(self, request, queryset):
        actualizados = queryset.update(estado_membresia='ACTIVA')
        self.message_user(
            request,
            f"Se activaron exitosamente {actualizados} membresía(s).",
            messages.SUCCESS,
        )

    @admin.action(description="Congelar membresías seleccionadas")
    def congelar_membresias(self, request, queryset):
        actualizados = queryset.update(estado_membresia='CONGELADA')
        self.message_user(
            request,
            f"Se congelaron {actualizados} membresía(s).",
            messages.WARNING,
        )

    @admin.action(description="Marcar como vencidas")
    def marcar_como_vencidas(self, request, queryset):
        actualizados = queryset.update(estado_membresia='VENCIDA')
        self.message_user(
            request,
            f"Se marcaron como vencidas {actualizados} membresía(s).",
            messages.ERROR,
        )


@admin.register(PagoMembresia)
class PagoMembresiaAdmin(admin.ModelAdmin):
    list_display = (
        'socio',
        'plan',
        'monto_formateado',
        'metodo_pago',
        'fecha_pago',
        'comprobante_referencia',
    )
    list_filter = ('metodo_pago', 'plan', 'fecha_pago')
    search_fields = ('socio__rut', 'socio__nombre_completo', 'comprobante_referencia')
    autocomplete_fields = ('socio',)

    @admin.display(description="Monto", ordering="monto")
    def monto_formateado(self, obj):
        return format_html(
            '<strong style="color:#059669;">${}</strong>',
            f"{obj.monto:,.0f}".replace(",", "."),
        )


@admin.register(ConfiguracionAforo)
class ConfiguracionAforoAdmin(admin.ModelAdmin):
    list_display = ('nombre_sede', 'aforo_maximo', 'alerta_umbral_porcentaje')


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    list_display = (
        'fecha_hora',
        'socio',
        'tipo_movimiento',
        'badge_resultado',
        'tiempo_respuesta_ms',
    )
    list_filter = ('resultado', 'tipo_movimiento', 'fecha_hora')
    search_fields = ('socio__rut', 'socio__nombre_completo', 'codigo_qr_leido', 'motivo_detalle')
    readonly_fields = ('fecha_hora',)

    @admin.display(description="Resultado", ordering="resultado")
    def badge_resultado(self, obj):
        estilos = {
            'PERMITIDO': ('#10b981', '#ecfdf5', '#065f46'),
            'DENEGADO_VENCIDA': ('#ef4444', '#fef2f2', '#991b1b'),
            'DENEGADO_CONGELADA': ('#3b82f6', '#eff6ff', '#1e40af'),
            'DENEGADO_AFORO_COMPLETO': ('#f59e0b', '#fffbeb', '#92400e'),
            'DENEGADO_QR_INVALIDO': ('#6b7280', '#f3f4f6', '#374151'),
        }
        borde, fondo, texto = estilos.get(obj.resultado, ('#6b7280', '#f3f4f6', '#374151'))
        return format_html(
            '<span style="display:inline-block; padding:3px 9px; border-radius:9999px; '
            'font-size:11px; font-weight:700; background-color:{}; color:{}; border:1px solid {};">'
            '{}</span>',
            fondo,
            texto,
            borde,
            obj.get_resultado_display(),
        )

    @admin.display(description="Tiempo Respuesta", ordering="tiempo_respuesta_ms")
    def tiempo_respuesta_formateado(self, obj):
        color = "#10b981" if obj.tiempo_respuesta_ms < 200 else "#f59e0b"
        return format_html(
            '<span style="font-family:monospace; font-weight:600; color:{};">{} ms</span>',
            color,
            f"{obj.tiempo_respuesta_ms:.2f}",
        )


@admin.register(ClaseGrupal)
class ClaseGrupalAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'instructor',
        'sala',
        'fecha_hora_inicio',
        'barra_ocupacion',
        'badge_lista_espera',
        'activa',
    )
    list_filter = ('activa', 'sala', 'instructor', 'fecha_hora_inicio')
    search_fields = ('nombre', 'instructor', 'sala')
    inlines = [ReservaClaseInline]

    @admin.display(description="Ocupación (Ocupados / Máximo)")
    def barra_ocupacion(self, obj):
        ocupados = obj.cupos_ocupados
        maximo = obj.cupo_maximo or 1
        porcentaje = min(100, int((ocupados / maximo) * 100))

        if porcentaje >= 100:
            color = "#ef4444"
        elif porcentaje >= 80:
            color = "#f59e0b"
        else:
            color = "#10b981"

        return format_html(
            '<div style="min-width:140px;">'
            '<div style="display:flex; justify-content:space-between; font-size:11px; font-weight:600; margin-bottom:3px;">'
            '<span>{} / {} cupos</span>'
            '<span>{}%</span>'
            '</div>'
            '<div style="width:100%; background:#e5e7eb; height:8px; border-radius:9999px; overflow:hidden;">'
            '<div style="width:{}%; background:{}; height:100%; border-radius:9999px;"></div>'
            '</div>'
            '</div>',
            ocupados,
             obj.cupo_maximo,
            porcentaje,
            porcentaje,
            color,
        )

    @admin.display(description="Lista de Espera")
    def badge_lista_espera(self, obj):
        en_espera = obj.cantidad_lista_espera
        if en_espera > 0:
            return format_html(
                '<span style="display:inline-block; padding:2px 9px; border-radius:9999px; '
                'font-size:11px; font-weight:700; background:#fffbeb; color:#92400e; border:1px solid #f59e0b;">'
                '{} en espera</span>',
                en_espera,
            )
        return format_html(
            '<span style="color:#9ca3af; font-size:11px;">{}</span>',
            "Sin espera",
        )


@admin.register(ReservaClase)
class ReservaClaseAdmin(admin.ModelAdmin):
    list_display = (
        'clase',
        'socio',
        'badge_estado',
        'posicion_espera',
        'fecha_reserva',
    )
    list_filter = ('estado', 'clase')
    search_fields = ('socio__rut', 'socio__nombre_completo', 'clase__nombre')
    readonly_fields = ('posicion_espera', 'fecha_reserva')
    actions = ['cancelar_reservas_y_promover_espera']

    @admin.display(description="Estado", ordering="estado")
    def badge_estado(self, obj):
        estilos = {
            'CONFIRMADA': ('#10b981', '#ecfdf5', '#065f46'),
            'LISTA_ESPERA': ('#f59e0b', '#fffbeb', '#92400e'),
            'CANCELADA': ('#ef4444', '#fef2f2', '#991b1b'),
            'ASISTIO': ('#3b82f6', '#eff6ff', '#1e40af'),
        }
        borde, fondo, texto = estilos.get(obj.estado, ('#6b7280', '#f3f4f6', '#374151'))
        return format_html(
            '<span style="display:inline-block; padding:3px 10px; border-radius:9999px; '
            'font-size:11px; font-weight:700; background-color:{}; color:{}; border:1px solid {};">'
            '{}</span>',
            fondo,
            texto,
            borde,
            obj.get_estado_display(),
        )

    @admin.action(description="Cancelar reservas seleccionadas y promover lista de espera")
    def cancelar_reservas_y_promover_espera(self, request, queryset):
        canceladas = 0
        # Ordenar para procesar de forma determinista y ejecutar cancelar() con transaction.atomic()
        for reserva in queryset.exclude(estado='CANCELADA').order_by('fecha_reserva', 'id'):
            reserva.cancelar()
            canceladas += 1

        self.message_user(
            request,
            f"Se cancelaron {canceladas} reserva(s) y se promovió automáticamente la lista de espera.",
            messages.SUCCESS,
        )
