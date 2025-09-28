# DBS401_MachineLearning

An automatically penetration testing tool for database implementations using deepagent.

## Disclaimer — Authorized Use Required

This security testing tool is intended solely for educational, research, and authorized penetration testing purposes. You must obtain explicit, written permission from the owner of any system, network, or data before testing. The authors and distributors of this tool are not responsible for any damage or legal consequences resulting from unauthorized or improper use. Use of this tool is at your own risk and must comply with all applicable laws and policies. If you are unsure whether you have authorization, stop and obtain written consent before proceeding.

## Installation and Usage

```bash
# Install uv
# https://docs.astral.sh/uv/getting-started/installation/

# Install dependencies
uv sync

# Copy the example .env.example to .env and set your GOOGLE_API_KEY
cp .env.example .env
# Set your Google API Key in the .env file

# Run the main application
uv run main.py
```
