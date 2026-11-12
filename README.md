# FitLife — Plataforma de Control de Asistencia QR, Aforo en Tiempo Real y Reserva de Clases

**Asignatura:** Desarrollo Backend — Evaluación Parcial N°3  
**Docente:** Marcelo Alvarado Aravena  
**Caso Asignado:** Proyecto 2 — FitLife  

Sistema Fullstack desarrollado con **Django**, **Django REST Framework (DRF)** y **PostgreSQL** (`fitlife_db`) para solucionar la congestión en el acceso, el sobrecupo en clases grupales y el ingreso de usuarios con membresías vencidas.

---

## 🌐 Acceso al Despliegue en AWS EC2

- **URL / IP Pública AWS EC2:** http://50.19.184.225/
- **Panel de Administración Django:** http://50.19.184.225/admin/
- **API REST (DRF):** http://50.19.184.225/api/
- **Documentación de Apoyo IA:** Ver archivo [`prompts_ia.md`](./prompts_ia.md)

---

## 🚀 Cumplimiento de los 4 Requerimientos del Caso (Proyecto 2)

1. **CRUD y Administración de Planes, Pagos y Estados de Membresía (`ACTIVA`, `VENCIDA`, `CONGELADA`):**
   - Gestión integral de planes comerciales, padrón de alumnos/socios y registro de pagos.
   - Al registrar un pago (`PagoMembresia.save()`), la membresía del socio se activa automáticamente (`ACTIVA`) y extiende su `fecha_vencimiento` sumando `plan.duracion_dias`.
2. **Validación y Registro de Acceso mediante Código QR (`POST /api/accesos/validar-qr/`):**
   - Generación de credenciales QR únicas (`UUID` indexado + imagen PNG con `qrcode[pil]`).
   - Validación en milisegundos (`time.perf_counter()`) comprobando existencia del QR, vigencia automática por fecha (`verificar_vigencia()`), estado de la membresía y disponibilidad de aforo en sala.
3. **Reserva de Clases Grupales con Manejo Automático de Cupos y Lista de Espera (`transaction.atomic()`):**
   - Si hay cupos disponibles en la clase, el alumno queda en estado `CONFIRMADA`; si la sala está llena, ingresa automáticamente a `LISTA_ESPERA` con posición correlativa (`#1`, `#2`, ...).
   - Al cancelar o liberar un cupo confirmado, el sistema promueve automáticamente al alumno `#1` de la `LISTA_ESPERA` a `CONFIRMADA` y reordena la cola restante.
4. **Dashboard de Control de Aforo en Tiempo Real (`GET /api/dashboard/aforo/`):**
   - Monitoreo en vivo de alumnos dentro del gimnasio, barra de capacidad dinámica, nivel de alerta (`NORMAL`, `ADVERTENCIA`, `CRITICO`), últimos accesos QR y ocupación de clases grupales.

---

## 🛠️ Instrucciones de Ejecución Local

1. **Clonar el repositorio y crear el entorno virtual:**
   ```powershell
   git clone https://github.com/egonista/fitlife.git
   cd fitlife
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Configurar variables de entorno (`.env`):**
   Copiar `.env.example` a `.env` y verificar los parámetros de conexión a PostgreSQL (`fitlife_db` en puerto `5432`).

3. **Aplicar migraciones y cargar datos semilla:**
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   python manage.py seed_fitlife
   ```

4. **Ejecutar pruebas y levantar el servidor:**
   ```powershell
   python manage.py test
   python manage.py runserver
   ```

---

## ☁️ Despliegue en AWS Academy EC2 (Ubuntu Server)

En una instancia EC2 Ubuntu con los puertos **22 (SSH)** y **80 (HTTP)** habilitados en el *Security Group*, ejecutar:

```bash
git clone https://github.com/egonista/fitlife.git
cd fitlife
chmod +x deploy_ec2.sh
sudo ./deploy_ec2.sh
```

El script instala y configura automáticamente **PostgreSQL**, crea la base de datos `fitlife_db`, aplica migraciones, carga los datos iniciales (`seed_fitlife`) y deja corriendo **Gunicorn** + **Nginx** en el puerto `80` accesible desde la IP pública de la instancia EC2.

---

## 🔑 Credenciales de Acceso (`seed_fitlife`)

| Rol | Usuario | Contraseña | Permisos |
| :--- | :--- | :--- | :--- |
| **Administrador General** | `admin` | `Valorant-1` | Portal Web Completo + `/admin/` + API DRF |
| **Recepción / Operador** | `recepcion` | `Valorant-1` | Portal Web Completo + API DRF |
