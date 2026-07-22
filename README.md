# HaulSync — Backend API

> FMCSA Hours of Service compliance engine and trip planning API, built with Django REST Framework.

HaulSync is an enterprise truck route planning application that takes trip inputs (current location, pickup, dropoff, cycle hours used) and returns:
- **Optimised route** via OSRM public routing API
- **FMCSA HOS-compliant timeline** (11-hr drive limit, 14-hr shift window, 30-min break, 10-hr sleeper, 70-hr/8-day cycle)
- **Daily ELD log data** (authentic FMCSA Driver Daily Log format)
- **Server-side geocoding proxy** (Nominatim via Django — no CORS issues)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4 + Django REST Framework |
| Routing | OSRM public API (free, no key) |
| Geocoding | Nominatim / OpenStreetMap (proxied server-side) |
| Server | Gunicorn + WhiteNoise |
| Deployment | Render (free tier) |

---

## Local Setup

### 1. Prerequisites
- Python 3.11+
- pip

### 2. Clone and install

```bash
git clone https://github.com/SohaibShaikh04/haulsync-backend.git
cd haulsync-backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment variables

Create a `.env` file in the project root (optional for local dev — defaults work out of the box):

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4. Run migrations and start server

```bash
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000`.

---

## API Endpoints

### `POST /api/trips/plan/`
Plan a full trip with HOS compliance.

**Request body:**
```json
{
  "current_location": { "lat": 32.7767, "lng": -96.7970, "name": "Dallas, TX" },
  "pickup_location":  { "lat": 32.7555, "lng": -97.3308, "name": "Fort Worth, TX" },
  "dropoff_location": { "lat": 33.4484, "lng": -112.0740, "name": "Phoenix, AZ" },
  "cycle_used_hours": 0
}
```

**Response:** Route polyline, HOS timeline, ELD daily logs, trip summary.

---

### `GET /api/geocode/?q=Dallas, TX`
Server-side geocoding proxy (avoids CORS when called from browser).

**Response:**
```json
{ "lat": 32.776, "lng": -96.796, "name": "Dallas, TX", "display_name": "..." }
```

---

## FMCSA HOS Assumptions (per assessment spec)

- Property-carrying driver, **70 hrs / 8-day cycle**
- No adverse driving conditions
- Fuel stop at least every **1,000 miles**
- **1 hour** each for pickup and drop-off
- Drive time derived from OSRM actual road duration (not estimated from distance/speed)

---

## Project Structure

```
haulsync-backend/
├── api/
│   ├── services/
│   │   ├── hos_engine.py        # FMCSA HOS rules engine
│   │   ├── trip_planner.py      # Main orchestrator
│   │   ├── stop_planner.py      # Stop + fuel event builder
│   │   ├── eld_generator.py     # Daily log page generator
│   │   ├── routing_service.py   # OSRM integration
│   │   ├── fuel_planner.py      # Fuel stop intervals
│   │   └── timeline_builder.py  # Absolute time assignment
│   ├── views.py                 # PlanTripView + GeocodeView
│   ├── serializers.py
│   └── urls.py
├── haulysnc_backend/
│   ├── settings.py
│   └── urls.py
├── requirements.txt
├── Procfile                     # Gunicorn for Render
└── build.sh                     # Render build script
```

---

## Deployment (Render)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn haulysnc_backend.wsgi`
5. Add environment variables:
   - `SECRET_KEY` — generate a secure random string
   - `DEBUG` — `False`
   - `ALLOWED_HOSTS` — your Render domain (e.g. `haulsync-backend.onrender.com`)
6. Deploy — Render auto-redeploys on every push to `main`
