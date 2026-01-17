#!/usr/bin/env python3

"""Test script to verify YCB models work correctly."""

import sys
import os
sys.path.append('.')

from ycb.models.video import VideoMetadataCreate, VideoQualityScoreCreate, UploadJobCreate, QualityMetrics
from ycb.models.script import VideoScriptCreate, ScriptSection, ScriptGenerationRequest
from uuid import uuid4

def test_models():
    print("Testing YCB Pydantic models...")
    
    # Test VideoMetadata
    try:
        metadata = VideoMetadataCreate(
            title='AI-Powered Content Creation',
            description='Learn how to create amazing content with AI tools',
            tags=['AI', 'content', 'YouTube']
        )
        print(f"[OK] VideoMetadata: {metadata.title}")
    except Exception as e:
        print(f"[FAIL] VideoMetadata failed: {e}")
        return False
    
    # Test VideoScript
    try:
        sections = [
            ScriptSection(
                section_id='intro',
                title='Introduction',
                content='Welcome to our amazing video about AI!',
                order_index=0
            ),
            ScriptSection(
                section_id='main',
                title='Main Content',
                content='Now let us dive into the main topic...',
                order_index=1
            )
        ]
        
        script = VideoScriptCreate(
            title='AI Tutorial Script',
            description='A comprehensive script about AI tools',
            script_type='tutorial',
            target_audience='Content creators and developers',
            sections=sections,
            keywords=['AI', 'tutorial', 'automation']
        )
        print(f"[OK] VideoScript: {script.title} with {len(script.sections)} sections")
    except Exception as e:
        print(f"[FAIL] VideoScript failed: {e}")
        return False
    
    # Test UploadJob
    try:
        job = UploadJobCreate(
            video_id=uuid4(),
            platform='youtube',
            video_file_path='/tmp/video.mp4'
        )
        print(f"[OK] UploadJob: {job.platform}")
    except Exception as e:
        print(f"[FAIL] UploadJob failed: {e}")
        return False
    
    # Test VideoQualityScore
    try:
        metrics = QualityMetrics(
            audio_quality=85.0,
            video_quality=90.0,
            content_quality=75.0,
            technical_quality=88.0,
            seo_score=70.0
        )
        
        # Calculate weighted average for overall score
        overall = (85.0 * 0.2) + (90.0 * 0.25) + (75.0 * 0.3) + (88.0 * 0.15) + (70.0 * 0.1)
        
        quality_score = VideoQualityScoreCreate(
            video_id=uuid4(),
            overall_score=overall,
            metrics=metrics,
            is_publishable=True
        )
        print(f"[OK] VideoQualityScore: {quality_score.overall_score:.1f}")
    except Exception as e:
        print(f"[FAIL] VideoQualityScore failed: {e}")
        return False
    
    print("\nAll models tested successfully!")
    return True

if __name__ == "__main__":
    success = test_models()
    sys.exit(0 if success else 1)