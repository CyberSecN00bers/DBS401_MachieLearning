import subprocess
import sys
from typing import List

def install_system_packages(packages: List[str]) -> None:
    """Install missing binaries using the appropriate package manager."""
    platform = sys.platform.lower()

    for package in packages:
        try:
            if platform.startswith("linux"):
                # Assuming Debian-based system
                subprocess.run(["sudo", "apt", "install", "-y", package], check=True)
            elif platform == "win32":
                print(f"Please install {package} manually on Windows.")
            elif platform == "darwin":
                # macOS
                subprocess.run(["brew", "install", package], check=True)
            else:
                print(f"Unsupported platform for installing {package}: {platform}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}: {e}")

def install_python_packages(packages: List[str]) -> None:
    """Install missing Python packages using pip."""
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}: {e}")

def install_dependencies(missing_system_packages: List[str], missing_packages: List[str]) -> None:
    """Install missing system packages and Python packages."""
    if missing_system_packages:
        print("Installing missing system packages...")
        install_system_packages(missing_system_packages)

    if missing_packages:
        print("Installing missing Python packages...")
        install_python_packages(missing_packages)

if __name__ == "__main__":
    # Example usage
    missing_binaries = ["nmap", "curl"]
    missing_packages = ["numpy", "pandas"]
    install_dependencies(missing_binaries, missing_packages)