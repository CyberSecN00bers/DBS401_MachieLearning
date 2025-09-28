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

    # Check for required system packages
    dependencies = get_dependencies()
    missing_system_packages = []

    for package in dependencies["system_packages"]:
        if platform.system() == "Windows":
            # Check installed programs on Windows
            try:
                result = subprocess.run(
                    ["powershell", "-Command", f"Get-Package -Name {package}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    missing_system_packages.append(package)
            except FileNotFoundError:
                missing_system_packages.append(package)
        elif platform.system() == "Linux":
            # Check installed packages on Linux (Debian-based example)
            try:
                result = subprocess.run(
                    ["dpkg", "-l", package],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    missing_system_packages.append(package)
            except FileNotFoundError:
                missing_system_packages.append(package)
        elif platform.system() == "Darwin":
            # Check installed packages on macOS
            try:
                result = subprocess.run(
                    ["brew", "list", package],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    missing_system_packages.append(package)
            except FileNotFoundError:
                missing_system_packages.append(package)
        else:
            # Fallback to `which` for unknown platforms
            if not which(package):
                missing_system_packages.append(package)

    info["missing_system_packages"] = missing_system_packages

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