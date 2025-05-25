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
5. Run the app:
    - `python run.py`

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