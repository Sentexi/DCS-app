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
