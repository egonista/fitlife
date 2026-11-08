# FitLife — Plataforma de Control de Asistencia QR, Aforo en Tiempo Real y Reserva de Clases

Sistema backend y plataforma web integral construida con **Django 6**, **Django REST Framework (DRF)** y **PostgreSQL** (`fitlife_db`) para la automatización operativa de gimnasios y centros deportivos.

---

## 🚀 Características Principales

1. **Control de Acceso QR en Milisegundos (`POST /api/accesos/validar-qr/`)**
   - Lectura indexada de tokens `UUID` (`db_index=True`) con medición exacta de latencia mediante `time.perf_counter()`.
   - Verificación automática de vigencia (`socio.verificar_vigencia()`), bloqueo inmediato de membresías `VENCIDA` o `CONGELADA`, y bloqueo preventivo cuando el gimnasio alcanza su `aforo_maximo`.
   - Generación dinámica de credenciales QR en formato PNG (`qrcode[pil]`).

2. **Dashboard de Aforo en Tiempo Real (`GET /api/dashboard/aforo/`)**
   - Monitoreo en vivo (polling automático cada 5 segundos vía `fetch`) de personas dentro de las instalaciones, porcentaje de ocupación, umbrales de alerta (`NORMAL`, `ADVERTENCIA`, `CRITICO`), últimos 10 accesos QR con su latencia en milisegundos y ocupación de clases grupales.

3. **Reservas de Clases Grupales y Lista de Espera Transaccional (`transaction.atomic()`)**
   - Bloqueo pesimista (`select_for_update()`) para evitar condiciones de carrera en clases de alta demanda.
   - Si una clase tiene cupos disponibles, la reserva queda en estado `CONFIRMADA`; si el cupo está lleno, el socio ingresa automáticamente a `LISTA_ESPERA` con posición correlativa (`#1`, `#2`, ...).
   - Al cancelar una reserva `CONFIRMADA`, el sistema promueve automáticamente al socio `#1` de la `LISTA_ESPERA` a estado `CONFIRMADA` y reordena las posiciones restantes.

4. **Renovación Automática de Membresías por Pago (`PagoMembresia.save()`)**
   - Al registrar un pago, la membresía del socio pasa automáticamente a estado `ACTIVA` y su `fecha_vencimiento` se calcula/extiende sumando `plan.duracion_dias`.

5. **Panel de Administración Django Avanzado (`/admin/`)**
   - Identidad visual FitLife (`templates/admin/base_site.html`), accesos rápidos al Dashboard y Simulador QR, badges HTML coloreados (`format_html`), barras de progreso de ocupación de clases, `inlines` y acciones masivas personalizadas.

---

## 🛠️ Requisitos y Configuración Local

1. **Crear y activar entorno virtual:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Configurar variables de entorno (`.env`):**
   Copiar `.env.example` a `.env` y ajustar las credenciales de PostgreSQL (`fitlife_db` en puerto `5432`).

3. **Ejecutar migraciones y poblar datos de demostración:**
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   python manage.py seed_fitlife
   ```

4. **Iniciar el servidor de desarrollo:**
   ```powershell
   python manage.py runserver
   ```

---

## 🔑 Credenciales de Prueba (`seed_fitlife`)

| Rol | Usuario | Contraseña | Acceso |
| :--- | :--- | :--- | :--- |
| **Superusuario / Admin** | `admin` | `Valorant-1` | Plataforma Web + `/admin/` + API DRF |
| **Operador Recepción** | `recepcion` | `Valorant-1` | Plataforma Web + API DRF |

---

## 🔌 Endpoints Principales (API REST y Web)

- `GET /` — Dashboard de Control de Aforo en Tiempo Real
- `GET /simulador-qr/` — Simulador y Validador de Acceso QR en Milisegundos
- `GET /membresias/` — Gestión CRUD de Planes, Socios y Pagos
- `GET /clases/` — Gestión CRUD de Clases Grupales y Cola de Lista de Espera
- `GET /admin/` — Panel de Administración Central de Django
- `POST /api/accesos/validar-qr/` — Validación de acceso QR con medición en milisegundos
- `GET /api/dashboard/aforo/` — Métricas en tiempo real de aforo, alertas, accesos y clases
- `GET|POST /api/planes/`, `/api/socios/`, `/api/pagos/`, `/api/clases/`, `/api/reservas/`, `/api/accesos/` — `ModelViewSet` DRF protegidos con `IsAuthenticated`
