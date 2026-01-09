"""
Dependency checker for Gandiva Pro Backend
Verifies all required packages are installed
"""
import sys

REQUIRED_PACKAGES = {
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn[standard]',
    'websockets': 'websockets',
    'pymodbus': 'pymodbus',
    'pyserial': 'pyserial',
    'sqlalchemy': 'sqlalchemy',
    'pydantic': 'pydantic',
    'pydantic_settings': 'pydantic-settings',
    'sklearn': 'scikit-learn',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'yaml': 'pyyaml',
    'aiofiles': 'aiofiles',
}

def check_imports():
    """Check if all required packages can be imported"""
    missing = []
    errors = []
    
    for module_name, package_name in REQUIRED_PACKAGES.items():
        try:
            if module_name == 'pydantic_settings':
                __import__('pydantic_settings')
            elif module_name == 'sklearn':
                __import__('sklearn')
            elif module_name == 'yaml':
                __import__('yaml')
            else:
                __import__(module_name)
            print(f"[OK] {package_name}")
        except ImportError as e:
            missing.append(package_name)
            errors.append(f"[FAIL] {package_name} - {str(e)}")
            print(f"[FAIL] {package_name} - NOT INSTALLED")
    
    return missing, errors

if __name__ == "__main__":
    print("Checking Gandiva Pro Backend Dependencies...")
    print("=" * 50)
    
    missing, errors = check_imports()
    
    print("=" * 50)
    if missing:
        print(f"\n[ERROR] {len(missing)} package(s) missing:")
        for pkg in missing:
            print(f"   pip install {pkg}")
        print("\nTo install all dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All dependencies installed successfully!")
        sys.exit(0)

