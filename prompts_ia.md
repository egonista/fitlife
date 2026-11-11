# Registro de Apoyo de Herramientas de Inteligencia Artificial (`prompts_ia.md`)

**Asignatura:** Desarrollo Backend — Evaluación Parcial N°3  
**Docente:** Marcelo Alvarado Aravena  
**Proyecto Asignado:** Proyecto 2 — FitLife: Plataforma de Control de Asistencia y Reserva de Clases  
**Stack Tecnológico:** Python 3, Django, Django REST Framework (DRF), PostgreSQL, Bootstrap 5, Gunicorn, WhiteNoise  

---

## 1. Propósito del Documento

De acuerdo con los lineamientos de la **Evaluación Parcial N°3 (Criterio 4: Seguridad, Sesiones y Apoyo de IA)**, este documento registra de forma estructurada las consultas (prompts), decisiones arquitectónicas y validaciones realizadas con el apoyo de herramientas de Inteligencia Artificial durante la construcción de **FitLife**.

---

## 2. Bitácora de Prompts y Soluciones Implementadas

### Prompt 1 — Arquitectura de Base de Datos Relacional y Lógica Transaccional en PostgreSQL
> **Prompt utilizado:**  
> *"Actúa como un arquitecto de software experto en Django, Django REST Framework y PostgreSQL. Necesito modelar el dominio relacional para el Proyecto 2 (FitLife) incluyendo `PlanMembresia`, `Socio` (con token UUID indexado para lectura QR y verificación automática de vigencia), `PagoMembresia` (que al guardar active automáticamente la membresía y extienda `fecha_vencimiento`), `ConfiguracionAforo`, `RegistroAcceso`, `ClaseGrupal` y `ReservaClase` con manejo transaccional (`transaction.atomic()`) de cupos y promoción automática de lista de espera al cancelar."*

- **Aporte de la IA:**
  - Diseño de los 7 modelos relacionales en `core/models.py` conectados a PostgreSQL (`fitlife_db`).
  - Indexación del campo `token_qr` (`models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)`) para garantizar lecturas en milisegundos en el torniquete.
  - Implementación de `ClaseGrupal.objects.select_for_update()` dentro de bloques `with transaction.atomic():` en `ReservaClase.save()` y `ReservaClase.cancelar()`, evitando condiciones de carrera y promoviendo automáticamente al socio en posición `#1` de `LISTA_ESPERA` a `CONFIRMADA` mientras reordena correlativamente el resto de la cola.

---

### Prompt 2 — Personalización Avanzada del Administrador de Django (Criterio 2)
> **Prompt utilizado:**  
> *"Personaliza `core/admin.py` registrando todos los modelos del dominio FitLife con clases `ModelAdmin` avanzadas: badges HTML coloreados con `format_html` para el estado de membresía y resultados de acceso, barra de progreso visual de ocupación de clases grupales, `TabularInline` para pagos y reservas, acciones masivas para activar/congelar/vencer membresías y acción para cancelar reservas promoviendo la lista de espera. Además, diseña `templates/admin/base_site.html` con la identidad visual de FitLife."*

- **Aporte de la IA:**
  - Implementación de `SocioAdmin`, `ClaseGrupalAdmin`, `ReservaClaseAdmin`, `RegistroAccesoAdmin`, `PlanMembresiaAdmin`, `PagoMembresiaAdmin` y `ConfiguracionAforoAdmin` en `core/admin.py`.
  - Uso seguro de `format_html` compatible con Django 6 para indicadores visuales de estado (`ACTIVA`, `VENCIDA`, `CONGELADA`) y barras de capacidad.
  - Creación de `templates/admin/base_site.html` con accesos directos hacia el Panel de Sede en Tiempo Real y el módulo de Recepción QR.

---

### Prompt 3 — API REST con DRF, Torniquete QR y Dashboard de Aforo en Tiempo Real (Criterios 3 y 4)
> **Prompt utilizado:**  
> *"Implementa en `core/serializers.py` y `core/api_views.py` los `ModelViewSet` protegidos con `IsAuthenticated`, el endpoint `POST /api/accesos/validar-qr/` que mida la latencia con `time.perf_counter()`, verifique vigencia de la membresía y controle que no se supere el `aforo_maximo` en entradas, y el endpoint `GET /api/dashboard/aforo/` para alimentar en tiempo real el dashboard web con Bootstrap 5."*

- **Aporte de la IA:**
  - Construcción de los serializadores y `ViewSets` en DRF protegidos por sesión y autenticación.
  - Desarrollo de `ValidarAccesoQRAPIView` y `DashboardAforoAPIView` con cálculo en vivo del aforo en sala, porcentaje de ocupación, niveles de alerta (`NORMAL`, `ADVERTENCIA`, `CRITICO`) y generación de códigos QR en formato PNG mediante `qrcode[pil]`.
  - Construcción de las vistas y plantillas responsivas en `templates/core/` (`dashboard.html`, `simulador_qr.html`, `membresias.html`, `clases.html`, `login.html`) y página de error `templates/404.html`.

---

### Prompt 4 — Automatización de Datos de Prueba y Despliegue en AWS EC2 (Criterio 5)
> **Prompt utilizado:**  
> *"Crea un comando `python manage.py seed_fitlife` para poblar PostgreSQL con planes, alumnos de prueba en estados Activa/Vencida/Congelada y clases grupales con lista de espera activa, además de un script de aprovisionamiento `deploy_ec2.sh` para desplegar Django + PostgreSQL + Gunicorn + Nginx en una instancia Ubuntu de AWS Academy EC2."*

- **Aporte de la IA:**
  - Creación del comando `core/management/commands/seed_fitlife.py` para inicializar datos reproducibles para la defensa en vivo.
  - Elaboración del script `deploy_ec2.sh` y documentación técnica en `README.md` para puesta en marcha en AWS EC2.

---

## 3. Verificación y Control de Calidad Realizado por el Estudiante

1. **Pruebas Automatizadas (`core/tests.py`):** Se verificó con `python manage.py test` el cumplimiento de las reglas de negocio (bloqueo de reservas para membresías vencidas o congeladas, paso automático de `LISTA_ESPERA` `#1` a `CONFIRMADA`, activación de membresía al registrar pago y bloqueo de torniquete por aforo máximo).
2. **Seguridad y Variables de Entorno:** Se validó la separación de credenciales en `.env` (excluido en `.gitignore`), plantilla `.env.example`, protección de rutas mediante `@login_required` e `IsAuthenticated`, y manejo de errores HTTP `404` sin exponer rutas internas.
