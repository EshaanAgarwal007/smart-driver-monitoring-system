# 🚗 AVALON MOTORS
## AI-Powered Smart Driver Safety & Fatigue Monitoring System

> A premium, futuristic web platform for real-time driver drowsiness detection,
> fatigue alerting, GPS tracking and fleet safety management — built on Django + MediaPipe AI.

---

## 📸 Features At A Glance

| Feature | Description |
|---|---|
| 🏠 **Futuristic Homepage** | Dark automotive theme, glassmorphism, animated gradients |
| 👤 **Driver Registration** | Full form with vehicle details — admin approval workflow |
| 🔐 **Role-Based Auth** | Separate driver & admin login flows |
| 🧠 **AI Eye Tracking** | MediaPipe Face Mesh (468 landmarks) — browser-native |
| 👁️ **EAR Detection** | Eye Aspect Ratio computed every frame at 30 FPS |
| 🔔 **Smart Alarm** | Gradual audio escalation via Web Audio API |
| 📊 **Admin Dashboard** | Charts, live feed, driver management, analytics |
| 📋 **History & Reports** | Per-session logs with safety scores |
| 🗺️ **GPS Tracking** | Real-time geolocation capture during sessions |
| 🚨 **Live Alerts** | Instant admin notifications on fatigue/accident |

---

## 🛠️ Tech Stack

```
Backend  : Django 4.2 (Python 3.10+)
Frontend : HTML5 · CSS3 · Vanilla JS · Bootstrap 5.3
AI/CV    : MediaPipe Face Mesh (browser) · Web Audio API
Charts   : Chart.js 4
Database : SQLite (dev) → MySQL/PostgreSQL (prod)
Fonts    : Orbitron · Exo 2 · Share Tech Mono
```

---

## ⚡ Quick Setup

### 1. Clone / Extract

```bash
cd avalon_motors
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Admin / Superuser

```bash
python manage.py createsuperuser
```
> This account will be used as the **Admin/Company** dashboard login.

### 6. Collect Static Files (optional for dev)

```bash
python manage.py collectstatic --noinput
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## 🗺️ URL Routes

| Path | Description |
|---|---|
| `/` | Homepage |
| `/auth/register/` | Driver registration |
| `/auth/login/` | Driver / Admin login |
| `/driver/dashboard/` | Driver dashboard |
| `/driver/monitoring/start/` | Live AI monitoring session |
| `/driver/history/` | Session history & reports |
| `/admin-panel/` | Admin control center |
| `/admin-panel/drivers/` | Manage all drivers |
| `/django-admin/` | Django built-in admin |

---

## 🧠 AI Detection Logic

The detection engine runs **entirely in the browser** using [MediaPipe Face Mesh](https://developers.google.com/mediapipe/solutions/vision/face_landmarker).

```
EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

EAR < 0.25           → Eye considered CLOSED
Closed frames ≥ 15   → 🟡 DROWSINESS alert (Medium)
Closed frames ≥ 20   → 🟠 FATIGUE alert    (High)
Closed frames ≥ 30   → 🔴 CRITICAL alert   (Critical)
```

Alarm volume increases progressively via Web Audio API oscillator.
Alarm stops automatically when eyes reopen.

---

## 👥 User Roles

### Driver
1. Register at `/auth/register/`
2. Wait for **admin approval** (status: PENDING)
3. Login after approval
4. Click **Start Monitoring** → allow camera
5. AI monitors continuously in the browser
6. View session history and safety scores

### Admin / Company
1. Login with Django superuser credentials
2. Approve/reject driver registrations
3. Monitor live sessions
4. View fleet-wide analytics & alert history
5. Receive real-time fatigue notifications

---

## 📁 Project Structure

```
avalon_motors/
├── avalon_motors/          # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                   # Main app
│   ├── models.py           # DB models
│   ├── views.py            # All views
│   ├── urls.py             # URL routes
│   ├── forms.py            # Registration/login forms
│   └── admin.py            # Django admin config
├── templates/
│   ├── base.html           # Master layout
│   ├── home.html           # Homepage
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── driver/
│   │   ├── dashboard.html
│   │   ├── monitoring.html # AI monitoring page
│   │   └── history.html
│   └── admin_panel/
│       ├── dashboard.html
│       ├── drivers.html
│       └── driver_detail.html
├── static/
│   ├── css/
│   │   └── avalon.css      # Master stylesheet
│   └── js/
│       ├── main.js         # Global UI
│       └── drowsiness.js   # AI detection engine
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration Notes

### Camera Permissions
The browser will request camera access when the driver starts monitoring.
**Must be served over HTTPS in production** for camera API to work.

For local dev, `http://localhost` is whitelisted by browsers.

### GPS
Geolocation API is used to capture driver coordinates.
Must be served over HTTPS in production for GPS to work.

### Production Deployment
1. Set `DEBUG = False` in `settings.py`
2. Set a strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Use PostgreSQL or MySQL instead of SQLite
5. Serve with Gunicorn + Nginx
6. Enable HTTPS (required for camera + GPS)

---

## 🎨 Design System

| Element | Value |
|---|---|
| Primary color | `#00d4ff` (Cyan) |
| Accent | `#0066ff` (Electric Blue) |
| Success | `#00ff88` (Neon Green) |
| Danger | `#ff2244` (Alert Red) |
| Background | `#020a18` (Deep Navy) |
| Font Display | Orbitron |
| Font Body | Exo 2 |
| Font Mono | Share Tech Mono |

---

## 📝 License

Built for educational / portfolio / hackathon purposes.
© 2024 Avalon Motors — AI Safety Platform
