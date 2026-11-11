from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views, views

router = DefaultRouter()
router.register(r'planes', api_views.PlanMembresiaViewSet, basename='api-planes')
router.register(r'socios', api_views.SocioViewSet, basename='api-socios')
router.register(r'pagos', api_views.PagoMembresiaViewSet, basename='api-pagos')
router.register(r'clases', api_views.ClaseGrupalViewSet, basename='api-clases')
router.register(r'reservas', api_views.ReservaClaseViewSet, basename='api-reservas')
router.register(r'accesos', api_views.RegistroAccesoViewSet, basename='api-accesos')

urlpatterns = [
    # Autenticación por sesiones
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='core/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout',
    ),

    # Dashboard en Tiempo Real y Configuración de Aforo
    path('', views.dashboard_view, name='dashboard'),
    path('aforo/actualizar/', views.actualizar_aforo_view, name='actualizar_aforo'),

    # Simulador de Acceso QR en milisegundos
    path('simulador-qr/', views.simulador_qr_view, name='simulador_qr'),
    path('socios/<int:pk>/qr.png', views.socio_qr_png_view, name='socio_qr_png'),
    path('socios/<int:pk>/credencial/', views.socio_credencial_view, name='socio_credencial'),

    # Exportación de Reportes Excel (CSV)
    path('reportes/accesos.csv', views.exportar_accesos_csv_view, name='exportar_accesos_csv'),
    path('reportes/pagos.csv', views.exportar_pagos_csv_view, name='exportar_pagos_csv'),

    # Gestión CRUD: Planes, Socios y Pagos
    path('membresias/', views.gestion_membresias_view, name='gestion_membresias'),
    path('planes/crear/', views.plan_crear_view, name='plan_crear'),
    path('planes/<int:pk>/editar/', views.plan_editar_view, name='plan_editar'),
    path('planes/<int:pk>/eliminar/', views.plan_eliminar_view, name='plan_eliminar'),
    path('socios/crear/', views.socio_crear_view, name='socio_crear'),
    path('socios/<int:pk>/editar/', views.socio_editar_view, name='socio_editar'),
    path('socios/<int:pk>/eliminar/', views.socio_eliminar_view, name='socio_eliminar'),
    path('socios/<int:pk>/estado/', views.socio_cambiar_estado_view, name='socio_cambiar_estado'),
    path('pagos/registrar/', views.pago_registrar_view, name='pago_registrar'),
    path('pagos/<int:pk>/editar/', views.pago_editar_view, name='pago_editar'),
    path('pagos/<int:pk>/eliminar/', views.pago_eliminar_view, name='pago_eliminar'),

    # Gestión CRUD: Clases Grupales y Reservas con Lista de Espera
    path('clases/', views.gestion_clases_view, name='gestion_clases'),
    path('clases/crear/', views.clase_crear_view, name='clase_crear'),
    path('clases/<int:pk>/editar/', views.clase_editar_view, name='clase_editar'),
    path('clases/<int:pk>/eliminar/', views.clase_eliminar_view, name='clase_eliminar'),
    path('reservas/crear/', views.reserva_crear_view, name='reserva_crear'),
    path('reservas/<int:pk>/cancelar/', views.reserva_cancelar_view, name='reserva_cancelar'),
    path('reservas/<int:pk>/asistencia/', views.reserva_asistencia_view, name='reserva_asistencia'),
    path('clases/nuevo-alumno/', views.socio_rapido_clase_view, name='socio_rapido_clase'),

    # Endpoints API REST (Django REST Framework)
    path('api/accesos/validar-qr/', api_views.ValidarAccesoQRAPIView.as_view(), name='api_validar_qr'),
    path('api/dashboard/aforo/', api_views.DashboardAforoAPIView.as_view(), name='api_dashboard_aforo'),
    path('api/', include(router.urls)),
]
