"""
Unit tests for validator service
"""
import pytest
from services.validator_service import is_valid_ip, is_valid_url


class TestIPValidation:
    """Tests for IP address validation"""
    
    def test_valid_ipv4(self):
        """Test valid IPv4 addresses"""
        assert is_valid_ip("192.168.1.1") is True
        assert is_valid_ip("10.0.0.1") is True
        assert is_valid_ip("127.0.0.1") is True
        assert is_valid_ip("255.255.255.255") is True
    
    def test_invalid_ipv4(self):
        """Test invalid IPv4 addresses"""
        assert is_valid_ip("256.1.1.1") is False
        assert is_valid_ip("192.168.1") is False
        assert is_valid_ip("192.168.1.1.1") is False
        assert is_valid_ip("abc.def.ghi.jkl") is False
        assert is_valid_ip("") is False
    
    def test_edge_cases(self):
        """Test edge cases"""
        assert is_valid_ip("0.0.0.0") is True
        assert is_valid_ip("192.168.-1.1") is False


class TestURLValidation:
    """Tests for URL validation"""
    
    def test_valid_urls(self):
        """Test valid URLs"""
        assert is_valid_url("https://www.example.com") is True
        assert is_valid_url("http://example.com") is True
        assert is_valid_url("https://example.com:8080") is True
        assert is_valid_url("https://example.com/path/to/resource") is True
    
    def test_invalid_urls(self):
        """Test invalid URLs"""
        assert is_valid_url("not a url") is False
        assert is_valid_url("") is False
        assert is_valid_url("ftp://example") is False  # No TLD
    
    def test_url_with_ports(self):
        """Test URLs with port numbers"""
        assert is_valid_url("http://localhost:8080") is True
        assert is_valid_url("https://example.com:443/api") is True
