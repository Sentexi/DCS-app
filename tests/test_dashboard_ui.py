import subprocess
from pathlib import Path

def test_join_button_label_changes():
    script = Path(__file__).with_name('dashboard_button_label.test.js')
    result = subprocess.run(['node', str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
