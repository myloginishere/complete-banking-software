#!/usr/bin/env python3
"""
install.py - One-step installer for Complete Banking Software
- Creates virtual environment
- Installs dependencies
- Initializes database schema and default admin
- Prints next steps
"""
import os
import subprocess
import sys
import venv

APP_PORT = os.environ.get("APP_PORT", "5000")
PYTHON_BIN = sys.executable or "python3"

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(ROOT, ".venv")
REQ_FILE = os.path.join(ROOT, "requirements.txt")


def run(cmd, cwd=None, env=None):
    print(f"$ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd or ROOT, env=env)


def ensure_venv():
    if not os.path.isdir(VENV_DIR):
        print("Creating virtual environment .venv ...")
        venv.create(VENV_DIR, with_pip=True)
    else:
        print("Virtual environment already exists: .venv")


def venv_bin(name):
    if os.name == 'nt':
        return os.path.join(VENV_DIR, 'Scripts', name + '.exe')
    return os.path.join(VENV_DIR, 'bin', name)


def pip_install():
    pip = venv_bin('pip')
    print("Upgrading pip ...")
    run([pip, "install", "--upgrade", "pip"]) 
    if os.path.isfile(REQ_FILE):
        print("Installing dependencies from requirements.txt ...")
        run([pip, "install", "-r", "requirements.txt"]) 
    else:
        print("requirements.txt not found; installing minimal deps ...")
        run([pip, "install", "flask", "reportlab"]) 


def init_database():
    python = venv_bin('python')
    print("Initializing database (creates default admin admin/admin123) ...")
    code = (
        "import os; "
        "from app import init_database; "
        "os.makedirs('database', exist_ok=True); "
        "init_database(); "
        "print('Database initialized.')"
    )
    run([python, "-c", code])


def main():
    print("Installing Complete Banking Software ...")
    ensure_venv()
    pip_install()
    init_database()
    print("\nInstallation complete. Next steps:")
    print("  1) Activate venv: source .venv/bin/activate (Windows: .venv\\Scripts\\activate)")
    print(f"  2) Run the app: python app.py")
    print(f"  3) Open: http://localhost:{APP_PORT}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Error: command failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
