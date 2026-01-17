"""
YCB Configuration System

Centralized configuration management for the YouTube Channel Builder using Pydantic BaseSettings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """YCB Configuration settings using Pydantic BaseSettings for environment variable management."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Supabase Configuration
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase anonymous key")
    
    # YouTube API Configuration
    youtube_client_id: Optional[str] = Field(default=None, description="YouTube OAuth client ID")
    youtube_client_secret: Optional[str] = Field(default=None, description="YouTube OAuth client secret")
    youtube_channel_id: Optional[str] = Field(default=None, description="Target YouTube channel ID")
    
    # ElevenLabs Configuration
    elevenlabs_api_key: Optional[str] = Field(default=None, description="ElevenLabs API key for voice synthesis")
    elevenlabs_voice_id: Optional[str] = Field(default=None, description="ElevenLabs voice ID to use")
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for content generation")
    
    # YCB-specific Configuration
    ycb_output_dir: str = Field(default="./ycb_output", description="Directory for YCB output files")
    ycb_max_videos_per_day: int = Field(default=5, description="Maximum videos to process per day")
    ycb_default_privacy: str = Field(default="private", description="Default video privacy setting")
    ycb_auto_publish: bool = Field(default=False, description="Whether to automatically publish videos")
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are present and non-empty."""
        required_fields = [
            self.supabase_url,
            self.supabase_key,
            self.youtube_client_id,
            self.youtube_client_secret,
            self.youtube_channel_id,
            self.elevenlabs_api_key,
            self.elevenlabs_voice_id,
            self.openai_api_key
        ]
        
        return all(field and str(field).strip() for field in required_fields)
    
    @property
    def is_auto_publish_enabled(self) -> bool:
        """Check if auto-publish is enabled and privacy allows it."""
        return self.ycb_auto_publish and self.ycb_default_privacy in ("public", "unlisted")


# Global settings instance
settings = Settings()

# Alias for backward compatibility
YCBConfig = Settings