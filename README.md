## Setup Instructions

1. Create a virtual environment:
    - `python -m venv venv`
2. Activate it:
    - `venv\Scripts\activate` (Windows)  
      `source venv/bin/activate` (macOS/Linux)
3. Install dependencies:
    - `pip install -r requirements.txt`
4. Set up the database:
    - `flask db upgrade`
4.1 If the database has been modified (either locally or in a branch from GitHub that is not consistent with the local state of the database):
    - `flask db stamp head`
    - `flask db migrate -m "some descriptive message here"`
    - `flask db upgrade`
5. Run the app:
    - `python run.py`

## Configuration

These settings can be provided via environment variables or by modifying
`config.py`:

- **SECRET_KEY** - Flask secret key. Default: `dev`.
- **SQLALCHEMY_DATABASE_URI** - database connection string.
  Default: `sqlite:///debate_app.db`.
- **SQLALCHEMY_TRACK_MODIFICATIONS** - set to `true` to enable change
  tracking. Default: `False`.
- **CORS_ALLOWED_ORIGINS** - origins allowed for CORS and SocketIO.
  Provide a comma-separated list (e.g. `https://example.com`). Default: `*`.
- **PORT** - port used when running `python run.py`. Default: `5000`.
- **SERVER_NAME** - domain name used for external URLs, e.g. in
  confirmation emails. If unset, Flask uses the request host.
- **PREFERRED_URL_SCHEME** - scheme used for URLs generated with
  `url_for(..., _external=True)`. Default: `http`.

## 🚀 Production Deployment with uWSGI

To run the app in a production environment using **uWSGI**, follow these steps:

---

### 🔧 Step 1: Install uWSGI

Install uWSGI in your virtual environment:

```bash
pip install uwsgi
```

### Step 2: Create a wsgi.py File
Create a file named wsgi.py in the root directory (next to run.py):

```
from app import create_app

app = create_app()
```

### Step 3: Run uWSGI

Use the following command to launch the app on port 8000:

```
uwsgi --http :8000 --wsgi-file wsgi.py --callable app --master --processes 4 --threads 2
```
