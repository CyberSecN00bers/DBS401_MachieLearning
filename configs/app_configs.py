from pydantic import BaseSettings
from pydantic_settings import SettingsConfigDict
from pydantic import Field, computed_field
from typing import Optional


class AppConfig(BaseSettings):
    """Application configuration parsed from .env file."""

    APP_NAME: Optional[str] = Field(
        description="Name of the application.", default="DBS401 Machine Learning"
    )
    DEBUG: Optional[bool] = Field(description="Enable debug mode.", default=False)
    GOOGLE_API_KEY: Optional[str] = Field(
        description="Google API key for authentication.", default=None
    )
    GEMINI_API_KEY: Optional[str] = Field(
        description="Gemini API key for authentication.", default=None
    )
    OPENAI_API_KEY: Optional[str] = Field(
        description="OpenAI API key for authentication.", default=None
    )
    OPENAI_BASE_URL: Optional[str] = Field(
        description="OpenAI base URL for API requests.", default=None
    )

    model_config = SettingsConfigDict(
        # read from dotenv format config file
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        # ignore extra attributes
        extra="ignore",
    )


# Example usage
if __name__ == "__main__":
    config = AppConfig()
    print("Application Name:", config.APP_NAME)
