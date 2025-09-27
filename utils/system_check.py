from shutil import which
import platform
import subprocess
from typing import Dict, Any
from utils.dependency import get_dependencies

def check_system() -> Dict[str, Any]:
    """Returns basic system information and checks for the presence of required dependencies."""
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }

    # Check for required binaries
    dependencies = get_dependencies()
    missing_binaries = []
    for binary in dependencies["binaries"]:
        if not which(binary):
            missing_binaries.append(binary)
    info["missing_binaries"] = missing_binaries

    # Check for required Python packages
    missing_packages = []
    for package in dependencies["python_packages"]:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    info["missing_python_packages"] = missing_packages

    return info

if __name__ == "__main__":
    import json
    print(json.dumps(check_system(), indent=2))