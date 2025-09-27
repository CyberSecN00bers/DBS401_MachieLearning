from colorama import Fore, Style, init
from typing import Literal
from enum import Enum
import json

# Initialize colorama for cross-platform support
init(autoreset=True)


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


def notify(message: str, level: LogLevel = LogLevel.INFO) -> None:
    """Prints a formatted notification message with color based on the level."""
    levels = {
        LogLevel.INFO: Fore.BLUE + "INFO",
        LogLevel.WARN: Fore.YELLOW + "WARN",
        LogLevel.SUCCESS: Fore.GREEN + "SUCCESS",
        LogLevel.ERROR: Fore.RED + "ERROR",
    }

    level_str = levels.get(level, Fore.WHITE + "INFO")
    print(f"[{level_str}{Style.RESET_ALL}] {message}")


def parse_input(prompt: str) -> str:
    """Prompts the user for input and returns the entered string."""
    return input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL} ")


def format_json_output(data: dict) -> None:
    """Formats and prints a dictionary as a JSON-like structure."""
    print(Fore.MAGENTA + json.dumps(data, indent=2) + Style.RESET_ALL)


def parse_int_input(prompt: str, min_value: int = None, max_value: int = None) -> int:
    """Prompts the user for an integer input and validates it against optional min and max values."""
    while True:
        try:
            user_input = int(input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL} "))
            if min_value is not None and user_input < min_value:
                notify(f"Value must be at least {min_value}.", LogLevel.WARN)
                continue
            if max_value is not None and user_input > max_value:
                notify(f"Value must be at most {max_value}.", LogLevel.WARN)
                continue
            return user_input
        except ValueError:
            notify("Invalid input. Please enter a valid integer.", LogLevel.ERROR)


if __name__ == "__main__":
    # Example usage
    notify("This is an info message.", LogLevel.INFO)
    notify("This is a warning message.", LogLevel.WARN)
    notify("This is a success message.", LogLevel.SUCCESS)
    notify("This is an error message.", LogLevel.ERROR)

    user_input = parse_input("Enter your name:")
    notify(f"Hello, {user_input}!", LogLevel.SUCCESS)

    sample_data = {"name": user_input, "status": "active"}
    format_json_output(sample_data)

    age = parse_int_input("Enter your age:", 0, 120)
    notify(f"Your age is {age}.", LogLevel.SUCCESS)
