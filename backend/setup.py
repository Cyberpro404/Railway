"""
Setup script for Gandiva Pro Backend
Creates necessary directories and verifies installation
"""
import os
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    dirs = [
        'models',
        'data',
        'logs'
    ]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"[OK] Created directory: {dir_name}")

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"[ERROR] Python 3.8+ required. Current: {version.major}.{version.minor}")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
    return True

if __name__ == "__main__":
    print("Gandiva Pro Backend Setup")
    print("=" * 50)
    
    if not check_python_version():
        sys.exit(1)
    
    create_directories()
    
    print("\n[SUCCESS] Setup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Verify installation: python check_dependencies.py")
    print("3. Run server: python app.py")

