from typing import List, Dict

# List of required dependencies
REQUIRED_BINARIES: List[str] = ["nmap", "curl", "git", "unixodbc"]
REQUIRED_PYTHON_PACKAGES: List[str] = []

def get_dependencies() -> Dict[str, List[str]]:
    """Returns the list of required binaries and Python packages."""
    return {
        "binaries": REQUIRED_BINARIES,
        "python_packages": REQUIRED_PYTHON_PACKAGES,
    }