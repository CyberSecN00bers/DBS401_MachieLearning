from typing import List, Dict

# List of required dependencies
REQUIRED_SYSTEM_PACKAGES: List[str] = ["nmap", "curl", "git", "unixodbc"]
REQUIRED_PYTHON_PACKAGES: List[str] = []

def get_dependencies() -> Dict[str, List[str]]:
    """Returns the list of required system packages and Python packages."""
    return {
        "system_packages": REQUIRED_SYSTEM_PACKAGES,
        "python_packages": REQUIRED_PYTHON_PACKAGES,
    }