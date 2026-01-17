"""
YCB Models Package

Pydantic models for the YouTube Channel Builder system.
All models use Pydantic v2 syntax with Field validators.
"""

# Video models
from .video import (
    # Enums
    VideoStatus,
    VideoPrivacy,
    UploadPlatform,
    
    # Video Metadata models
    VideoMetadataBase,
    VideoMetadataCreate,
    VideoMetadataUpdate,
    VideoMetadata,
    
    # Upload Job models
    UploadJobBase,
    UploadJobCreate,
    UploadJobUpdate,
    UploadJob,
    
    # Quality Score models
    QualityMetrics,
    VideoQualityScoreBase,
    VideoQualityScoreCreate,
    VideoQualityScore,
)

# Script models
from .script import (
    # Enums
    ScriptStatus,
    ScriptType,
    VoiceStyle,
    
    # Script models
    ScriptSection,
    VideoScriptBase,
    VideoScriptCreate,
    VideoScriptUpdate,
    VideoScript,
    
    # Generation models
    ScriptGenerationRequest,
    ScriptGenerationResponse,
    
    # Analytics models
    ScriptPerformanceMetrics,
)

__all__ = [
    # Video enums
    "VideoStatus",
    "VideoPrivacy", 
    "UploadPlatform",
    
    # Video Metadata models
    "VideoMetadataBase",
    "VideoMetadataCreate",
    "VideoMetadataUpdate", 
    "VideoMetadata",
    
    # Upload Job models
    "UploadJobBase",
    "UploadJobCreate",
    "UploadJobUpdate",
    "UploadJob",
    
    # Quality Score models
    "QualityMetrics",
    "VideoQualityScoreBase",
    "VideoQualityScoreCreate",
    "VideoQualityScore",
    
    # Script enums
    "ScriptStatus",
    "ScriptType",
    "VoiceStyle",
    
    # Script models
    "ScriptSection",
    "VideoScriptBase", 
    "VideoScriptCreate",
    "VideoScriptUpdate",
    "VideoScript",
    
    # Generation models
    "ScriptGenerationRequest",
    "ScriptGenerationResponse",
    
    # Analytics models
    "ScriptPerformanceMetrics",
]