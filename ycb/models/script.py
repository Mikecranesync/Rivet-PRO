"""
Video Script Data Models

Pydantic models for video script creation, management, and generation in the YouTube Channel Builder.
These models support the script writing pipeline from concept to final narration.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ===== Enums =====

class ScriptStatus(str, Enum):
    """Current status of script development."""
    CONCEPT = "concept"              # Initial idea/outline
    RESEARCH = "research"            # Research phase
    OUTLINE = "outline"              # Structured outline created
    DRAFT = "draft"                 # First draft written
    REVIEW = "review"               # Under review/revision
    APPROVED = "approved"           # Final approval received
    NARRATION_READY = "narration_ready"  # Ready for voice generation
    COMPLETED = "completed"         # Narration completed
    ARCHIVED = "archived"           # Old version archived


class ScriptType(str, Enum):
    """Type of video script."""
    TUTORIAL = "tutorial"           # How-to/educational content
    REVIEW = "review"              # Product/service reviews
    COMMENTARY = "commentary"       # Opinion/discussion
    NEWS = "news"                  # News/current events
    ENTERTAINMENT = "entertainment" # Entertainment content
    DOCUMENTARY = "documentary"     # Documentary style
    VLOG = "vlog"                  # Personal vlog
    INTERVIEW = "interview"         # Interview format


class VoiceStyle(str, Enum):
    """Voice generation style preferences."""
    PROFESSIONAL = "professional"   # Formal, business-like
    CASUAL = "casual"               # Relaxed, conversational
    ENTHUSIASTIC = "enthusiastic"   # High energy, excited
    EDUCATIONAL = "educational"      # Teaching, informative
    NARRATIVE = "narrative"         # Storytelling
    NEWS_ANCHOR = "news_anchor"     # News broadcast style


# ===== Script Section Models =====

class ScriptSection(BaseModel):
    """Individual section of a video script."""
    section_id: str = Field(..., description="Unique section identifier (e.g., 'intro', 'main_1', 'outro')")
    title: str = Field(..., description="Section title/heading")
    content: str = Field(..., min_length=1, description="Script content for this section")
    duration_estimate: Optional[int] = Field(None, ge=1, description="Estimated duration in seconds")
    
    # Voice direction
    voice_notes: Optional[str] = Field(None, description="Special voice/delivery instructions")
    voice_style: VoiceStyle = Field(default=VoiceStyle.PROFESSIONAL, description="Voice style for this section")
    
    # Visual cues
    visual_cues: List[str] = Field(default_factory=list, description="Visual elements to accompany this section")
    
    # Metadata
    order_index: int = Field(..., ge=0, description="Order position in script")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "section_id": "intro",
                "title": "Introduction",
                "content": "Welcome back to the channel! Today we're diving deep into artificial intelligence and how it's revolutionizing content creation.",
                "duration_estimate": 15,
                "voice_style": "enthusiastic",
                "visual_cues": ["channel_logo", "ai_graphics"],
                "order_index": 0
            }
        }
    )
    
    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Ensure content is not too long for a single section."""
        if len(v) > 2000:  # Reasonable limit for a single section
            raise ValueError('Section content should be under 2000 characters. Consider splitting into multiple sections.')
        return v.strip()


# ===== Video Script Models =====

class VideoScriptBase(BaseModel):
    """Base video script fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Script title/working title")
    description: str = Field(..., max_length=1000, description="Brief description of the video content")
    script_type: ScriptType = Field(..., description="Type of script content")
    
    # Target metrics
    target_duration: Optional[int] = Field(None, ge=30, le=3600, description="Target video duration in seconds")
    target_audience: str = Field(..., description="Target audience description")
    
    # Content structure
    sections: List[ScriptSection] = Field(default_factory=list, description="Script sections in order")
    
    # SEO and discovery
    keywords: List[str] = Field(default_factory=list, description="Target keywords for SEO")
    topics: List[str] = Field(default_factory=list, description="Main topics covered")
    
    # Production notes
    production_notes: Optional[str] = Field(None, description="Additional production guidance")
    research_sources: List[str] = Field(default_factory=list, description="Research sources/references")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "title": "AI-Powered Content Creation: The Future is Here",
                "description": "Exploring how artificial intelligence is transforming the way we create and consume content",
                "script_type": "tutorial",
                "target_duration": 600,
                "target_audience": "Content creators, marketers, tech enthusiasts aged 25-45",
                "keywords": ["AI content creation", "artificial intelligence", "automation"],
                "topics": ["AI tools", "content strategy", "future of media"],
                "sections": []
            }
        }
    )
    
    @field_validator('sections')
    @classmethod
    def validate_sections_order(cls, v: List[ScriptSection]) -> List[ScriptSection]:
        """Ensure sections are properly ordered."""
        if not v:
            return v
            
        # Check for duplicate section IDs
        section_ids = [section.section_id for section in v]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError('Duplicate section IDs found')
            
        # Ensure order_index values are sequential
        sorted_sections = sorted(v, key=lambda x: x.order_index)
        expected_indices = list(range(len(sorted_sections)))
        actual_indices = [section.order_index for section in sorted_sections]
        
        if actual_indices != expected_indices:
            raise ValueError('Section order_index values must be sequential starting from 0')
            
        return sorted_sections
    
    @property
    def estimated_total_duration(self) -> int:
        """Calculate total estimated duration from all sections."""
        return sum(section.duration_estimate or 30 for section in self.sections)
    
    @property
    def total_word_count(self) -> int:
        """Calculate total word count of all sections."""
        return sum(len(section.content.split()) for section in self.sections)


class VideoScriptCreate(VideoScriptBase):
    """Model for creating video scripts."""
    pass


class VideoScriptUpdate(BaseModel):
    """Model for updating video scripts (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    script_type: Optional[ScriptType] = None
    target_duration: Optional[int] = Field(None, ge=30, le=3600)
    target_audience: Optional[str] = None
    sections: Optional[List[ScriptSection]] = None
    keywords: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    production_notes: Optional[str] = None
    research_sources: Optional[List[str]] = None
    status: Optional[ScriptStatus] = None
    
    model_config = ConfigDict(use_enum_values=True)


class VideoScript(VideoScriptBase):
    """Full video script record."""
    script_id: UUID = Field(..., description="Unique script identifier")
    video_id: Optional[UUID] = Field(None, description="Associated video ID (if linked)")
    
    # Script status and workflow
    status: ScriptStatus = Field(default=ScriptStatus.CONCEPT, description="Current script status")
    version: int = Field(default=1, ge=1, description="Script version number")
    
    # Generation metadata
    generated_by: Optional[str] = Field(None, description="AI model or user that generated this script")
    generation_params: Optional[Dict[str, Any]] = Field(None, description="Parameters used for AI generation")
    
    # Quality metrics
    readability_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Readability score (0-100)")
    engagement_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Predicted engagement score")
    
    # Approval workflow
    approved_by: Optional[str] = Field(None, description="Who approved this script")
    approval_notes: Optional[str] = Field(None, description="Approval feedback/notes")
    
    # Timestamps
    created_at: datetime = Field(..., description="When script was created")
    updated_at: datetime = Field(..., description="Last script update")
    approved_at: Optional[datetime] = Field(None, description="When script was approved")
    
    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Script Generation Models =====

class ScriptGenerationRequest(BaseModel):
    """Request for AI script generation."""
    # Content requirements
    topic: str = Field(..., min_length=5, description="Main topic/subject for the video")
    script_type: ScriptType = Field(..., description="Type of script to generate")
    target_duration: int = Field(..., ge=30, le=3600, description="Target video duration in seconds")
    target_audience: str = Field(..., description="Target audience description")
    
    # Generation parameters
    tone: str = Field(default="professional", description="Tone of voice (professional, casual, enthusiastic, etc.)")
    keywords: List[str] = Field(default_factory=list, description="Keywords to include")
    key_points: List[str] = Field(default_factory=list, description="Specific points to cover")
    
    # Constraints
    avoid_topics: List[str] = Field(default_factory=list, description="Topics to avoid")
    must_include: List[str] = Field(default_factory=list, description="Elements that must be included")
    
    # AI model settings
    creativity_level: float = Field(default=0.7, ge=0.0, le=1.0, description="AI creativity level (0=conservative, 1=very creative)")
    include_hooks: bool = Field(default=True, description="Include attention-grabbing hooks")
    include_cta: bool = Field(default=True, description="Include call-to-action")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "topic": "How to build a successful YouTube channel with AI tools",
                "script_type": "tutorial",
                "target_duration": 480,
                "target_audience": "Aspiring YouTubers and content creators",
                "tone": "enthusiastic",
                "keywords": ["YouTube growth", "AI tools", "content creation"],
                "key_points": [
                    "Choosing the right AI tools",
                    "Automating video production",
                    "Growing your audience"
                ],
                "creativity_level": 0.8,
                "include_hooks": True,
                "include_cta": True
            }
        }
    )


class ScriptGenerationResponse(BaseModel):
    """Response from AI script generation."""
    request_id: UUID = Field(..., description="Generation request identifier")
    generated_script: VideoScript = Field(..., description="The generated script")
    
    # Generation metadata
    generation_time_seconds: float = Field(..., description="Time taken to generate script")
    model_used: str = Field(..., description="AI model used for generation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence in generated content")
    
    # Suggestions and alternatives
    alternative_titles: List[str] = Field(default_factory=list, description="Alternative title suggestions")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")
    
    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True
    )


# ===== Script Analytics Models =====

class ScriptPerformanceMetrics(BaseModel):
    """Performance metrics for published scripts."""
    script_id: UUID = Field(..., description="Script being analyzed")
    
    # Engagement metrics
    average_view_duration: float = Field(..., ge=0.0, description="Average view duration in seconds")
    retention_rate: float = Field(..., ge=0.0, le=1.0, description="Average retention rate (0-1)")
    engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Like/comment rate vs views")
    
    # Content analysis
    hook_effectiveness: float = Field(..., ge=0.0, le=100.0, description="How effective was the opening hook")
    pacing_score: float = Field(..., ge=0.0, le=100.0, description="Content pacing effectiveness")
    cta_effectiveness: float = Field(..., ge=0.0, le=100.0, description="Call-to-action effectiveness")
    
    # Comparative metrics
    performance_vs_channel_average: float = Field(..., description="Performance vs channel average (multiplier)")
    performance_vs_category_average: float = Field(..., description="Performance vs category average (multiplier)")
    
    # Analysis timestamp
    analyzed_at: datetime = Field(..., description="When analysis was performed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "average_view_duration": 245.3,
                "retention_rate": 0.68,
                "engagement_rate": 0.05,
                "hook_effectiveness": 78.5,
                "pacing_score": 82.1,
                "cta_effectiveness": 71.2,
                "performance_vs_channel_average": 1.15,
                "performance_vs_category_average": 0.94
            }
        }
    )