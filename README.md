# Ondo State Intelligent Logistics Platform: Backend API

A FastAPI backend for logistics orders, route-based pricing, driver verification, and delivery tracking in Ondo State, Nigeria. The current model-training workflow uses the field-survey Excel workbook; it does not train on orders collected by the platform.

## Features

- Sender, driver, and admin roles with JWT bearer authentication.
- Driver OTP verification by email. Verified drivers are required to list available orders and send GPS updates.
- Route-backed quick quotes and system-priced orders.
- Order status transitions from pending through delivery, with cancellation before pickup.
- Driver GPS updates over REST, location updates over WebSocket, and order chat over a separate authenticated WebSocket.
- Admin endpoints for dashboard, order volume, and route activity.
- Alembic migrations for the PostgreSQL schema.

## Technology

| Area | Implementation |
|---|---|
| API | FastAPI, REST, WebSocket |
| Authentication | fastapi-users, JWT bearer tokens |
| Database | Async SQLAlchemy with PostgreSQL; provider configured by `DATABASE_URL` |
| Migrations | Alembic |
| OTP storage | Redis |
| Pricing | XGBoost/scikit-learn training code, deterministic baseline, Joblib artifacts |
| Email | fastapi-mail over configured SMTP |
| Data processing | Pandas and NumPy |

A Google Maps distance-enrichment helper exists, but the current dataset preparation uses fixed corridor distance and risk mappings. The backend settings still require `GOOGLE_MAPS_API_KEY`.

## Project Layout

```text
.
├── app/
│   ├── api/                 # API routers
│   ├── core/                # Authentication, OTP, Redis, WebSocket manager
│   ├── data/                # State list and generated demo CSV
│   ├── ml/                  # Baseline, predictor, training, data preparation
│   ├── models/              # SQLAlchemy models
│   ├── schemas/              # API schemas
│   ├── scripts/             # Route seeder, demo data, pipeline entry point
│   ├── services/            # Business logic
│   ├── trained_models/       # Runtime model location from app/config.py default
│   └── main.py              # FastAPI application
├── alembic/                 # Migrations
├── data/                    # Survey workbook and generated clean CSV
|── notebook_outputs         # outputs (images and data) from the notebook (main.ipynb) are stored here
├── trained_models/          # Default training output directory
├── main.ipynb               # Modelling notebook
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── requirements.txt
```

## Requirements

- Python 3.11 or Docker.
- PostgreSQL.
- Redis for OTP operations.
- SMTP credentials for OTP and order notification email.
- Values for the required environment variables below.

## Local Setup

Run commands from the repository root.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

Create a `.env` file in the repository root. There is no checked-in `.env.example`. The application requires the first eight values below to initialize; the rest have defaults in `app/config.py`. Render overrides some defaults in `render.yaml`.

| Variable | Required | Default or example |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@localhost/db` |
| `JWT_SECRET` | Yes | Set a long, random secret |
| `RESET_PASSWORD_SECRET` | Yes | Set a separate long, random secret |
| `VERIFICATION_SECRET` | Yes | Set a separate long, random secret |
| `GOOGLE_MAPS_API_KEY` | Yes | Required by settings; used by the standalone distance helper |
| `MAIL_USERNAME` | Yes | SMTP username |
| `MAIL_PASSWORD` | Yes | SMTP password or Gmail App Password |
| `MAIL_FROM` | Yes | Sender email address |
| `MAIL_PORT` | No | `465` |
| `MAIL_SERVER` | No | `smtp.gmail.com` |
| `MAIL_STARTTLS` | No | `false` |
| `MAIL_SSL_TLS` | No | `true` |
| `REDIS_URL` | No | `redis://localhost:6379/0` |
| `ML_MODEL_PATH` | No | `app/trained_models/pricing_pipeline.joblib` |
| `OTP_EXPIRY_SECONDS` | No | `600` |
| `FRONTEND_URL` | No | `http://localhost:5173`; currently not used by CORS configuration |

Then migrate, seed, and start the API:

```powershell
alembic upgrade head
python -m app.scripts.seed_routes
uvicorn app.main:app --reload --port 8000
```

The seeder inserts 14 sample routes without checking for existing rows. Run it once per database; reruns create duplicate routes. API documentation is available at `http://localhost:8000/docs`.

To generate the optional 300-row demo CSV:

```powershell
python -m app.scripts.dummy_data
```

It writes `app/data/dummy_waybill_data.csv`. This file is demo/seed data only and is not supported as input to the current model trainer.

## Runtime Notes

The health endpoint is `GET /health`. It returns `status: healthy` and `ml_model: loaded` if a file exists at `ML_MODEL_PATH`, otherwise `ml_model: baseline`. It does not check database, Redis, or SMTP readiness.

CORS currently allows all origins in `app/main.py`; `FRONTEND_URL` does not restrict it. Review this before production use.

GPS positions, connected WebSockets, and chat history are held in process memory. They are lost on restart and are not shared across workers. Run one worker unless tracking state is moved to shared storage/pub/sub.

## ML Workflow

The training and verification workflow uses `data/Survey_Logistics_Dataset_200 (1).xlsx` only. It drops unknown-age rows, applies the vehicle label swap, uses notebook preprocessing, and attaches fixed corridor distances and risk levels. It does not mix in demo data, scraped prices, or published-price rows.

Build the clean audit CSV and train the model:

```powershell
python -m app.scripts.run_pipeline --survey "data/Survey_Logistics_Dataset_200 (1).xlsx"
```

The default outputs are `data/waybill_pricing_clean.csv` and `trained_models/pricing_pipeline.joblib`. To build the clean CSV without training, add `--skip-train`. To override output paths, use `--clean-csv` and `--model-out`.

To build the clean CSV alone:

```powershell
python -m app.ml.data_collection.pipeline `
  --survey "data/Survey_Logistics_Dataset_200 (1).xlsx" `
  --output data/waybill_pricing_clean.csv
```

To verify the published baseline metrics:

```powershell
python -m app.ml.verify_baseline_metrics "data/Survey_Logistics_Dataset_200 (1).xlsx"
```

The verification script reports approximately:

- Train: R2 0.581, MAE 1,274, RMSE 1,583
- Test: R2 0.247, MAE 1,681, RMSE 2,109

The training script separately prints baseline and XGBoost metrics for an 80/20 split with `random_state=42` and then refits the pipeline on all data.

### Model Inference Notes

The predictor supports both the raw 12-feature serving pipeline and the metadata-wrapped pipeline saved by the current trainer. It builds inputs in the fitted model's expected schema and falls back to baseline if a model artifact cannot be loaded or inference fails. The `/pricing/predict` route maps the predictor's `predicted_price` to the public `price` response field.

The trainer's survey model includes fields that a live quote does not provide, such as respondent demographics, survey opinions, origin, and destination labels. For that artifact, missing fields are left for the fitted categorical imputers. This allows inference without changing the model or training protocol, but the reported holdout metrics do not by themselves establish accuracy for these partially observed API inputs. Evaluate live-input performance separately before making production accuracy claims.

| Module | Purpose |
|---|---|
| `app/ml/baseline.py` | Deterministic pricing formula |
| `app/ml/feature_engineering.py` | Feature mappings and transformations |
| `app/ml/predictor.py` | Loads the configured artifact or selects baseline when the file is absent |
| `app/ml/train.py` | Trains and saves the XGBoost pipeline |
| `app/ml/evaluate.py` | Model evaluation utilities |
| `app/ml/verify_baseline_metrics.py` | Reproduces baseline metrics |
| `app/ml/data_collection/pipeline.py` | Survey data preparation |
| `app/ml/data_collection/scraper.py` | Standalone published-price scraper; not used by the current training pipeline |
| `app/ml/data_collection/distance_enrichment.py` | Standalone distance helper; not used by the current training pipeline |
| `app/scripts/dummy_data.py` | Generates demo data and defines sample seed routes |
| `app/scripts/run_pipeline.py` | Data preparation and training command-line entry point |

## Pricing Values

Package values below match the maps in the predictor.

| Package size | Approximate volume |
|---|---:|
| `envelope` | 2,625 cm3 |
| `small` | 30,000 cm3 |
| `medium` | 70,000 cm3 |
| `large` | 175,000 cm3 |
| `extra_large` | 360,000 cm3 |

| Package weight | Approximate weight |
|---|---:|
| `very_light` | 1 kg |
| `light` | 3.5 kg |
| `medium` | 10 kg |
| `heavy` | 22 kg |
| `very_heavy` | 40 kg |

## API Reference

All paths below are mounted at the application root. Open `/docs` on a running server for generated schemas.

### Authentication and Users

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/sender/register` | Public | Register a sender |
| POST | `/auth/driver/register` | Public | Register a driver |
| POST | `/auth/login` | Public | Obtain a JWT bearer token |
| POST | `/auth/otp/request` | Public | Request driver OTP email |
| POST | `/auth/otp/verify` | Public | Verify driver OTP |
| POST | `/auth/forgot-password` | Public | Request password-reset token |
| POST | `/auth/reset-password` | Public | Reset password with token |
| GET | `/users/me` | JWT | Read current user |
| PATCH | `/users/me` | JWT | Update current user |

Sender registration requires `email`, `password`, `first_name`, `last_name`, `phone`, and `address`. Driver registration additionally requires `vehicle_type`, `plate_number`, `state_of_operation`, and `nin_license`. There is no public admin-registration endpoint. Password-reset email delivery is not implemented.

### Routes and Locations

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/routes/origins` | Public | List origins present in the database |
| GET | `/routes/destinations?origin=...` | Public | List routes from an origin |
| GET | `/routes` | Public | List all routes |
| POST | `/routes` | Admin | Add a route |
| PATCH | `/routes/{route_id}/risk?risk_level=3` | Admin | Set route risk from 1 to 5 |
| GET | `/locations/states` | Public | Return the configured state list and count |

The seed data contains a `South Gate Akure` to `Lagos` route. Route examples and quick quotes depend on the route being present in the database.

A route creation body has `origin`, `destination`, `origin_lat`, `origin_lng`, `destination_lat`, `destination_lng`, `distance_km`, `estimated_duration_mins`, and `risk_level` fields.

### Pricing

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/pricing/quick-quote` | Public | Quote an existing route |
| POST | `/pricing/predict` | JWT | Predict from explicit route/package features; returns `price` and `model_used` |

Quick-quote request:

```json
{
  "origin_park": "South Gate Akure",
  "destination": "Lagos",
  "package_size": "medium",
  "package_weight": "light",
  "vehicle_type": "small_car"
}
```

Quick quote looks up the route and uses the current weekday, `is_festive_period=false`, and fuel price `700`. Its response contains `origin`, `destination`, `distance_km`, `estimated_duration_mins`, and `price`.

The authenticated `/pricing/predict` request fields are `package_size`, `package_weight`, `distance_km`, `vehicle_type`, `route_risk`, `day_of_week`, `is_festive_period`, and `fuel_price_per_litre`.

### Orders

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/orders` | Sender | Create an order |
| GET | `/orders/my` | Authenticated user | List orders by user role |
| GET | `/orders/available` | OTP-verified driver | List pending orders |
| GET | `/orders/track/{waybill_number}` | Public | Look up an order by waybill number |
| GET | `/orders/{order_id}` | Authenticated user | Read an order subject to ownership/assignment checks |
| PATCH | `/orders/{order_id}/status` | Authenticated user | Attempt a valid status transition |

Order creation requires `package_description`, `package_size`, `package_weight`, `origin_park`, `destination`, `vehicle_type`, `recipient_name`, `recipient_phone`, `day_of_week`, and `fuel_price_per_litre`; `is_festive_period` defaults to false. The route must already exist.

```json
{
  "package_description": "Bag of clothes",
  "package_size": "medium",
  "package_weight": "light",
  "origin_park": "South Gate Akure",
  "destination": "Lagos",
  "vehicle_type": "small_car",
  "recipient_name": "Jane Doe",
  "recipient_phone": "+2348098765432",
  "day_of_week": 4,
  "is_festive_period": false,
  "fuel_price_per_litre": 700
}
```

Status transitions are `pending → accepted → picked_up → in_transit → delivered`, with cancellation allowed from `pending` and `accepted`. The service checks that assigned drivers perform pickup, transit, and delivery transitions. A driver role is required to accept, but OTP verification is not checked in that status-update operation. The sender may cancel their own pending or accepted order; the assigned driver may cancel an accepted order; an admin may cancel.

### Tracking

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/tracking/update` | OTP-verified driver | Submit GPS coordinates |
| GET | `/tracking/live/{order_id}` | JWT | Get latest location; no order ownership check |
| DELETE | `/tracking/live/{order_id}` | OTP-verified driver | Clear latest location |
| WS | `/tracking/ws/{order_id}` | No authentication | Subscribe to GPS updates by order ID |
| WS | `/tracking/chat/{order_id}?token=JWT` | JWT query parameter | Chat during active delivery |

GPS update body:

```json
{
  "order_id": "uuid",
  "latitude": 7.2480,
  "longitude": 5.2050,
  "accuracy": 15.0,
  "timestamp": 1234567890
}
```

Location messages contain `driver_id`, `lat`, `lng`, `accuracy`, and `updated_at`. The location WebSocket has no authentication or ownership check; anyone who knows an order ID can subscribe. The chat socket validates a token, restricts access to the sender, assigned driver, or admin, and only operates while the order is accepted, picked up, or in transit. Chat history and tracking data are in-memory only.

### Admin

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/admin/dashboard` | Admin | Dashboard statistics |
| GET | `/admin/order-volume?days=30` | Admin | Order counts by date |
| GET | `/admin/route-activity?limit=10` | Admin | Route activity |

## Deployment

`docker-compose.yml` runs the API and Redis locally. Create `.env`, then run:

```bash
docker compose up --build
```

The checked-in `Dockerfile` installs `requirements.txt` and starts Uvicorn on port `8000`. It does not run migrations or seed routes. `render.yaml` configures a Docker web service and currently selects Render's `free` plan; provider pricing and availability can change. The Docker command currently does not use Render's assigned `$PORT`, so update it before deploying where the platform requires a dynamically assigned port. Configure required environment variables in the hosting dashboard, and run migrations and route seeding as explicit operations. Do not rerun the non-idempotent route seeder on a populated database.

This repository contains no frontend application. Any separately hosted frontend must configure its own API and WebSocket base URLs.

## License

MIT. See [LICENSE](LICENSE).