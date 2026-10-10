# Faktu — Gestión de facturas y gastos para autónomos

Aplicación web (FastAPI) para crear, editar y gestionar **facturas** y
**gastos** de un autónomo, organizados por **trimestres**, con los datos
necesarios para presentar el modelo 303/130.

Diseño responsive (escritorio y móvil) y en español.

## Funcionalidades

- 🔐 **Autenticación**: registro/login con JWT (7 días de sesión). Cada cuenta
  ve solo sus datos.
- 🧾 **Facturas**: alta/edición con líneas, IVA e IRPF configurables, cálculo
  automático de base imponible, cuotas y total en vivo.
- 🔢 **Numeración automática** por año: `01/2026`, `02/2026`…
- 📄 **PDF** de cada factura, generado al vuelo con [Reportlab].
- 💸 **Gastos**: con categorías, proveedor y adjunto (foto del ticket,
  descarga protegida por autenticación).
- 🗓️ **Vista por trimestres**: el trimestre actual primero, pasados a
  continuación (más reciente primero) y futuros al final. Totales por
  trimestre: facturado, gastos y neto.
- 📊 **Dashboard** anual: KPIs, gráfico por trimestres y actividad reciente.
- 👥 **Clientes** con total facturado acumulado y vínculo directo a la factura.
- ⚙️ **Configuración del emisor** para rellenar los datos de la factura.

## Stack

- **Backend**: FastAPI · SQLAlchemy 2 (async) · Pydantic v2 · Alembic ·
  PyJWT + bcrypt
- **Base de datos**: SQLite por defecto (cambiable con `DATABASE_URL`)
- **Frontend**: SPA estática servida por FastAPI, Tailwind CSS compilado,
  sin paso de build en el navegador

## Puesta en marcha (desarrollo)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # y ajusta SECRET_KEY, etc.
alembic upgrade head
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000`, crea una cuenta y empieza a facturar.
En desarrollo las tablas se crean automáticamente (`AUTO_CREATE_TABLES=true`).

## Puesta en marcha (Docker)

```bash
docker compose up --build
```

La app queda en `http://localhost:8000`, con la base de datos y los archivos
subidos en un volumen persistente (`faktu-data`).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Estructura

```
app/
  main.py            # creación de la app, routers, estáticos, SPA fallback
  core/              # config, db, seguridad, dependencias
  models/            # ORM (User, Cliente, Factura, Linea, Gasto, Config)
  schemas/           # Pydantic (validación y serialización)
  api/routes/        # auth, clientes, facturas, gastos, trimestres, dashboard
  services/          # numeración automática y generación de PDF
  static/            # SPA (HTML/CSS/JS + Tailwind compilado)
alembic/             # migraciones
tests/               # pytest + httpx (ASGI)
```

## API

La API REST vive bajo `/api/v1` y está documentada en `/docs` (Swagger) y
`/redoc`.

[Reportlab]: https://www.reportlab.com/