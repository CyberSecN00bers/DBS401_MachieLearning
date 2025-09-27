import argparse


def initialize_cli() -> argparse.ArgumentParser:
    """Initializes and configures the command-line interface."""
    parser = argparse.ArgumentParser(
        description="DBS401 Machine Learning CLI Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--check-system",
        action="store_true",
        help="Check the system for required dependencies.",
    )

    parser.add_argument(
        "--install-missing", action="store_true", help="Install missing dependencies."
    )

    parser.add_argument(
        "--run", type=str, help="Run a specific module or task by name."
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    return parser


if __name__ == "__main__":
    parser = initialize_cli()
    args = parser.parse_args()

    if args.check_system:
        print("Checking system...")
        # Import and call the system check function here

    if args.install_missing:
        print("Installing missing dependencies...")
        # Import and call the installer function here

    if args.run:
        print(f"Running task: {args.run}")
        # Logic to run the specified task

    if args.verbose:
        print("Verbose mode enabled.")
