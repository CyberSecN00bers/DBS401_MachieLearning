import re


def is_valid_ip(ip: str) -> bool:
    """Validates if the given string is a valid IPv4 address."""
    pattern = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
    if pattern.match(ip):
        parts = ip.split(".")
        return all(0 <= int(part) <= 255 for part in parts)
    return False


def is_valid_url(url: str) -> bool:
    """Validates if the given string is a valid URL."""
    pattern = re.compile(
        r"^(https?://)?"  # Optional scheme
        r"(www\.)?"  # Optional www
        r"[a-zA-Z0-9.-]+"  # Domain name
        r"\.[a-zA-Z]{2,}"  # Top-level domain
        r"(:\d{1,5})?"  # Optional port
        r"(/.*)?$"  # Optional path
    )
    return bool(pattern.match(url))


if __name__ == "__main__":
    # Example usage
    test_ip = "192.168.1.1"
    print(f"Is '{test_ip}' a valid IP? {is_valid_ip(test_ip)}")

    test_url = "https://www.example.com"
    print(f"Is '{test_url}' a valid URL? {is_valid_url(test_url)}")
