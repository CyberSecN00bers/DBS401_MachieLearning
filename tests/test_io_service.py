"""
Unit tests for IO service
"""
import pytest
from unittest.mock import patch, MagicMock
from services.io_service import (
    notify, 
    LogLevel, 
    format_json_output,
    clear_screen
)


class TestNotify:
    """Tests for notification function"""
    
    def test_notify_info(self, capsys):
        """Test info level notification"""
        notify("Test message", LogLevel.INFO)
        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "Test message" in captured.out
    
    def test_notify_error(self, capsys):
        """Test error level notification"""
        notify("Error occurred", LogLevel.ERROR)
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "Error occurred" in captured.out
    
    def test_notify_success(self, capsys):
        """Test success level notification"""
        notify("Operation successful", LogLevel.SUCCESS)
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
    
    def test_notify_warn(self, capsys):
        """Test warning level notification"""
        notify("Warning message", LogLevel.WARN)
        captured = capsys.readouterr()
        assert "WARN" in captured.out


class TestFormatJsonOutput:
    """Tests for JSON output formatting"""
    
    def test_format_simple_dict(self, capsys):
        """Test formatting a simple dictionary"""
        data = {"key": "value", "number": 42}
        format_json_output(data)
        captured = capsys.readouterr()
        assert "key" in captured.out
        assert "value" in captured.out
        assert "42" in captured.out


class TestClearScreen:
    """Tests for screen clearing function"""
    
    @patch('os.system')
    @patch('platform.system')
    def test_clear_screen_windows(self, mock_platform, mock_system):
        """Test screen clearing on Windows"""
        mock_platform.return_value = "Windows"
        clear_screen()
        mock_system.assert_called_once_with('cls')
    
    @patch('os.system')
    @patch('platform.system')
    def test_clear_screen_linux(self, mock_platform, mock_system):
        """Test screen clearing on Linux"""
        mock_platform.return_value = "Linux"
        clear_screen()
        mock_system.assert_called_once_with('clear')
