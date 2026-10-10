<p align="center"><img src="app/static/assets/logo.png" alt="Logo de Faktu" width="120"></p>

# Faktu — Gestión de facturas y gastos para autónomos

Aplicación web (FastAPI) para crear, editar y gestionar **facturas** y
**gastos** de un autónomo, organizados por **trimestres**, con los datos
necesarios para presentar el modelo 303/130.

Diseño responsive (escritorio y móvil) y en español.

## Capturas

| | |
|---|---|
| ![Vista principal (login + dashboard)](docs/screenshots/01-portada.png) | ![Listado y edición de facturas](docs/screenshots/02-facturas.png) |
| *Vista principal (login + dashboard)* | *Listado y edición de facturas* |
| ![Trimestres con totales](docs/screenshots/03-trimestres.png) | ![Gestión de clientes](docs/screenshots/04-clientes.png) |
| *Trimestres con totales* | *Gestión de clientes* |

Las imágenes se generan a partir de la cuenta demo poblada por
`scripts/seed_demo.py` (`demo@faktu.app` / `demo1234`).

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
- 📚 **Libro de conceptos por trimestre**: agrupa ingresos y gastos por
  conceptos (independiente de facturas/gastos), con totales por trimestre y
  **exportación a Excel** (una hoja por trimestre, mismo formato que el libro
  de referencia).
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

## Token de API para IAs (Claude, GPT, etc.)

En **Ajustes → Token API / IA** puedes generar tokens personales de larga
duración que dan acceso a toda la API con permisos equivalentes a tu sesión.
Útil para que un asistente (Claude, Cursor, un script propio, Postman…)
gestione la app en tu nombre.

- Formato: `fkt_<8-chars>_<32-chars-secrets>` (≈256 bits de entropía).
- Se muestran **una sola vez** al crearlos; guárdalo en un gestor de
  contraseñas.
- Puedes tener varios a la vez (uno por IA / dispositivo) y revocar
  individualmente.
- Uso:

  ```bash
  curl https://tu-dominio/api/v1/facturas \
       -H "Authorization: Bearer fkt_<prefijo>_<secreto>"
  ```

- Endpoints:
  - `GET /api/v1/api-tokens` — lista tus tokens activos y revocados (sin
    secretos).
  - `POST /api/v1/api-tokens {"name": "Claude Desktop"}` — crea uno y
    devuelve el secreto una sola vez.
  - `DELETE /api/v1/api-tokens/{id}` — revoca un token.

## Versión

La versión se gestiona desde el archivo `VERSION` en la raíz (semver
`MAJOR.MINOR.PATCH`). Se expone automáticamente en:

- `GET /api/v1/version` → `{"name": "Faktu", "version": "1.0.0"}`
- Footer del login y del sidebar de la SPA.

Para publicar una nueva versión basta con editar `VERSION` y reiniciar el
servidor (o redeploy). No hace falta tocar otros archivos.

[Reportlab]: https://www.reportlab.com/