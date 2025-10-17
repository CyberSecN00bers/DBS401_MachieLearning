"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_target_config():
    """Sample target configuration for testing"""
    return {
        "host": "127.0.0.1",
        "port": 1433,
        "username": "test_user",
        "password": "test_password",
        "database": "test_db"
    }


@pytest.fixture
def mock_nmap_result():
    """Mock nmap scan result"""
    return {
        "success": True,
        "xml": '<?xml version="1.0"?><nmaprun></nmaprun>',
        "stdout": "Nmap scan completed",
        "stderr": "",
        "returncode": 0
    }


@pytest.fixture
def mock_sqlmap_result():
    """Mock sqlmap scan result"""
    return {
        "success": True,
        "stdout": "sqlmap identified possible injection points",
        "stderr": "",
        "returncode": 0
    }
