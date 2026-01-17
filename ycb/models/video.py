"""
Video Data Models

Pydantic models for video metadata and upload management in the YouTube Channel Builder.
These models support the end-to-end video creation and publishing pipeline.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# ===== Enums =====

class VideoStatus(str, Enum):
    """Current status of video processing."""
    DRAFT = "draft"                    # Initial creation, script being worked on
    SCRIPT_READY = "script_ready"      # Script completed, ready for production
    RECORDING = "recording"            # Audio/video being generated
    EDITING = "editing"                # Post-production in progress
    READY_FOR_UPLOAD = "ready_for_upload"  # Final video ready
    UPLOADING = "uploading"            # Upload in progress
    UPLOADED = "uploaded"              # Successfully uploaded to platform
    PUBLISHED = "published"            # Live on YouTube
    FAILED = "failed"                  # Processing failed
    CANCELLED = "cancelled"            # Manually cancelled


class VideoPrivacy(str, Enum):
    """YouTube video privacy settings."""
    PRIVATE = "private"      # Only visible to creator
    UNLISTED = "unlisted"    # Accessible via direct link
    PUBLIC = "public"        # Publicly visible
    SCHEDULED = "scheduled"  # Scheduled for future release


class UploadPlatform(str, Enum):
    """Supported upload platforms."""
    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"


# ===== Video Metadata Models =====

class VideoMetadataBase(BaseModel):
    """Base video metadata fields."""
    title: str = Field(..., min_length=1, max_length=100, description="Video title (YouTube max 100 chars)")
    description: str = Field(..., max_length=5000, description="Video description (YouTube max 5000 chars)")
    tags: List[str] = Field(default_factory=list, description="Video tags/keywords (max 500 chars total)")
    thumbnail_url: Optional[str] = Field(None, description="Custom thumbnail URL")
    category_id: Optional[str] = Field(None, description="YouTube category ID")
    language: str = Field(default="en", description="Video language code (ISO 639-1)")
    
    # Privacy and scheduling
    privacy_status: VideoPrivacy = Field(default=VideoPrivacy.PRIVATE, description="Video privacy setting")
    scheduled_publish_time: Optional[datetime] = Field(None, description="When to publish (if scheduled)")
    
    # Engagement settings
    comments_enabled: bool = Field(default=True, description="Allow comments")
    ratings_enabled: bool = Field(default=True, description="Allow likes/dislikes")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "title": "How to Build Amazing YouTube Videos with AI",
                "description": "Learn how to create engaging YouTube content using artificial intelligence and automation tools...",
                "tags": ["AI", "YouTube", "Content Creation", "Automation"],
                "category_id": "28",  # Science & Technology
                "language": "en",
                "privacy_status": "public",
                "comments_enabled": True,
                "ratings_enabled": True
            }
        }
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate YouTube tags constraints."""
        if not v:
            return v
            
        # YouTube limits: max 15 tags, each max 30 chars, total max 500 chars
        if len(v) > 15:
            raise ValueError('Maximum 15 tags allowed')
            
        for tag in v:
            if len(tag) > 30:
                raise ValueError(f'Tag "{tag}" exceeds 30 character limit')
                
        total_chars = sum(len(tag) for tag in v) + len(v) - 1  # Include commas
        if total_chars > 500:
            raise ValueError('Total tags length exceeds 500 characters')
            
        return v


class VideoMetadataCreate(VideoMetadataBase):
    """Model for creating video metadata."""
    pass


class VideoMetadataUpdate(BaseModel):
    """Model for updating video metadata (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    category_id: Optional[str] = None
    language: Optional[str] = None
    privacy_status: Optional[VideoPrivacy] = None
    scheduled_publish_time: Optional[datetime] = None
    comments_enabled: Optional[bool] = None
    ratings_enabled: Optional[bool] = None
    
    model_config = ConfigDict(use_enum_values=True)


class VideoMetadata(VideoMetadataBase):
    """Full video metadata record."""
    metadata_id: UUID = Field(..., description="Unique metadata identifier")
    video_id: UUID = Field(..., description="Associated video ID")
    
    # Analytics data (populated after upload)
    platform_video_id: Optional[str] = Field(None, description="Platform-specific video ID (e.g., YouTube ID)")
    view_count: int = Field(default=0, description="Current view count")
    like_count: int = Field(default=0, description="Current like count")
    comment_count: int = Field(default=0, description="Current comment count")
    
    # Timestamps
    created_at: datetime = Field(..., description="When metadata was created")
    updated_at: datetime = Field(..., description="Last metadata update")
    published_at: Optional[datetime] = Field(None, description="When video was published")
    
    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Upload Job Models =====

class UploadJobBase(BaseModel):
    """Base upload job fields."""
    video_id: UUID = Field(..., description="Video being uploaded")
    platform: UploadPlatform = Field(..., description="Target upload platform")
    
    # Upload configuration
    video_file_path: str = Field(..., description="Path to video file")
    thumbnail_file_path: Optional[str] = Field(None, description="Path to thumbnail file")
    
    # Platform-specific settings
    platform_settings: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific upload options")
    
    # Retry configuration
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(default=300, ge=0, description="Delay between retries (seconds)")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "platform": "youtube",
                "video_file_path": "/tmp/videos/amazing_ai_video.mp4",
                "thumbnail_file_path": "/tmp/thumbnails/amazing_thumbnail.jpg",
                "platform_settings": {
                    "made_for_kids": False,
                    "monetization": True,
                    "caption_language": "en"
                },
                "max_retries": 3,
                "retry_delay": 300
            }
        }
    )


class UploadJobCreate(UploadJobBase):
    """Model for creating upload jobs."""
    pass


class UploadJobUpdate(BaseModel):
    """Model for updating upload jobs."""
    status: Optional[VideoStatus] = None
    progress_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    error_message: Optional[str] = None
    platform_video_id: Optional[str] = None
    platform_response: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True)


class UploadJob(UploadJobBase):
    """Full upload job record."""
    job_id: UUID = Field(..., description="Unique job identifier")
    
    # Upload status
    status: VideoStatus = Field(default=VideoStatus.READY_FOR_UPLOAD, description="Current upload status")
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Upload progress percentage")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Last error message if any")
    retry_count: int = Field(default=0, ge=0, description="Current retry attempt")
    
    # Platform response
    platform_video_id: Optional[str] = Field(None, description="Platform-assigned video ID")
    platform_response: Optional[Dict[str, Any]] = Field(None, description="Full platform API response")
    
    # Timestamps
    created_at: datetime = Field(..., description="When job was created")
    started_at: Optional[datetime] = Field(None, description="When upload started")
    completed_at: Optional[datetime] = Field(None, description="When upload completed")
    
    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Video Quality Score Models =====

class QualityMetrics(BaseModel):
    """Individual quality metrics."""
    audio_quality: float = Field(..., ge=0.0, le=100.0, description="Audio quality score (0-100)")
    video_quality: float = Field(..., ge=0.0, le=100.0, description="Video quality score (0-100)")
    content_quality: float = Field(..., ge=0.0, le=100.0, description="Content relevance/engagement score (0-100)")
    technical_quality: float = Field(..., ge=0.0, le=100.0, description="Technical production quality (0-100)")
    seo_score: float = Field(..., ge=0.0, le=100.0, description="SEO optimization score (0-100)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audio_quality": 85.0,
                "video_quality": 92.0,
                "content_quality": 78.0,
                "technical_quality": 88.0,
                "seo_score": 73.0
            }
        }
    )


class VideoQualityScoreBase(BaseModel):
    """Base video quality score fields."""
    video_id: UUID = Field(..., description="Video being scored")
    
    # Overall quality score (weighted average of metrics)
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted overall quality score")
    
    # Individual metric scores
    metrics: QualityMetrics = Field(..., description="Detailed quality metrics")
    
    # Analysis details
    analysis_version: str = Field(default="1.0", description="Quality analysis algorithm version")
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes or recommendations")
    
    # Quality thresholds for decision making
    is_publishable: bool = Field(..., description="Is quality sufficient for publication?")
    needs_improvement: List[str] = Field(default_factory=list, description="Areas needing improvement")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overall_score": 83.2,
                "metrics": {
                    "audio_quality": 85.0,
                    "video_quality": 92.0,
                    "content_quality": 78.0,
                    "technical_quality": 88.0,
                    "seo_score": 73.0
                },
                "analysis_version": "1.0",
                "is_publishable": True,
                "needs_improvement": ["seo_optimization", "content_engagement"]
            }
        }
    )
    
    @model_validator(mode='after')
    def validate_overall_score_calculation(self) -> 'VideoQualityScoreBase':
        """Ensure overall score matches calculated weighted average."""
        # Standard weights for overall score calculation
        weights = {
            'audio_quality': 0.2,
            'video_quality': 0.25,
            'content_quality': 0.3,
            'technical_quality': 0.15,
            'seo_score': 0.1
        }
        
        calculated_score = (
            self.metrics.audio_quality * weights['audio_quality'] +
            self.metrics.video_quality * weights['video_quality'] +
            self.metrics.content_quality * weights['content_quality'] +
            self.metrics.technical_quality * weights['technical_quality'] +
            self.metrics.seo_score * weights['seo_score']
        )
        
        # Allow for small rounding differences
        if abs(self.overall_score - calculated_score) > 1.0:
            raise ValueError(
                f'Overall score {self.overall_score} does not match '
                f'calculated score {calculated_score:.2f} based on weighted metrics'
            )
        
        return self


class VideoQualityScoreCreate(VideoQualityScoreBase):
    """Model for creating quality scores."""
    pass


class VideoQualityScore(VideoQualityScoreBase):
    """Full video quality score record."""
    score_id: UUID = Field(..., description="Unique score identifier")
    
    # Timestamps
    analyzed_at: datetime = Field(..., description="When analysis was performed")
    
    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )