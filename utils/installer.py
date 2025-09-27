import subprocess
import sys
from typing import List

def install_binaries(binaries: List[str]) -> None:
    """Install missing binaries using the appropriate package manager."""
    platform = sys.platform.lower()

    for binary in binaries:
        try:
            if platform.startswith("linux"):
                # Assuming Debian-based system
                subprocess.run(["sudo", "apt", "install", "-y", binary], check=True)
            elif platform == "win32":
                print(f"Please install {binary} manually on Windows.")
            elif platform == "darwin":
                # macOS
                subprocess.run(["brew", "install", binary], check=True)
            else:
                print(f"Unsupported platform for installing {binary}: {platform}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {binary}: {e}")

def install_python_packages(packages: List[str]) -> None:
    """Install missing Python packages using pip."""
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}: {e}")

def install_dependencies(missing_binaries: List[str], missing_packages: List[str]) -> None:
    """Install missing binaries and Python packages."""
    if missing_binaries:
        print("Installing missing binaries...")
        install_binaries(missing_binaries)

    if missing_packages:
        print("Installing missing Python packages...")
        install_python_packages(missing_packages)

if __name__ == "__main__":
    # Example usage
    missing_binaries = ["nmap", "curl"]
    missing_packages = ["numpy", "pandas"]
    install_dependencies(missing_binaries, missing_packages)