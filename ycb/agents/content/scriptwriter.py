"""
ScriptwriterAgent for YCB

AI-powered script writing agent that creates engaging YouTube video scripts
based on topics, keywords, and channel personality.
"""

import asyncio
from typing import Dict, Any, Optional, List
from ycb.core.base_agent import BaseAgent
from ycb.models.script import Script
from ycb.config import settings


class ScriptwriterAgent(BaseAgent):
    """
    Agent responsible for generating YouTube video scripts using AI.
    
    Features:
    - Topic-based script generation
    - SEO optimization
    - Channel personality adaptation
    - Script structure templates
    - Content quality validation
    
    Usage:
        agent = ScriptwriterAgent("scriptwriter_001")
        script = await agent.generate_script(topic="AI in Healthcare", duration=600)
    """
    
    def __init__(self, agent_name: str = "scriptwriter"):
        """
        Initialize the Scriptwriter Agent.
        
        Args:
            agent_name: Unique identifier for this agent instance
        """
        super().__init__(agent_name)
        self.script_templates = self._load_script_templates()
        self.personality_settings = self._load_personality_settings()
    
    def _get_capabilities(self) -> Dict[str, Any]:
        """
        Override to provide Scriptwriter-specific capabilities.
        
        Returns:
            Dict containing agent capabilities
        """
        capabilities = super()._get_capabilities()
        capabilities.update({
            "script_generation": True,
            "seo_optimization": True,
            "personality_adaptation": True,
            "multiple_formats": True,
            "content_validation": True
        })
        return capabilities
    
    def _load_script_templates(self) -> Dict[str, str]:
        """
        Load script templates for different video types.
        
        Returns:
            Dictionary of script templates
        """
        return {
            "educational": """
            [HOOK - 15 seconds]
            {hook_content}
            
            [INTRODUCTION - 30 seconds]
            {introduction}
            
            [MAIN CONTENT - {main_duration} seconds]
            {main_content}
            
            [CONCLUSION - 30 seconds]
            {conclusion}
            
            [CALL_TO_ACTION - 15 seconds]
            {cta_content}
            """,
            
            "entertainment": """
            [COLD_OPEN - 10 seconds]
            {cold_open}
            
            [INTRO - 20 seconds]
            {intro}
            
            [MAIN_SEGMENT - {main_duration} seconds]
            {main_segment}
            
            [OUTRO - 30 seconds]
            {outro}
            """,
            
            "tutorial": """
            [PROBLEM_STATEMENT - 20 seconds]
            {problem}
            
            [OVERVIEW - 40 seconds]
            {overview}
            
            [STEP_BY_STEP - {tutorial_duration} seconds]
            {steps}
            
            [RECAP_AND_RESOURCES - 30 seconds]
            {recap}
            """
        }
    
    def _load_personality_settings(self) -> Dict[str, Any]:
        """
        Load channel personality settings.
        
        Returns:
            Dictionary of personality configurations
        """
        return {
            "tone": "professional_friendly",
            "energy_level": "moderate",
            "technical_depth": "intermediate",
            "humor_level": "light",
            "call_to_actions": ["subscribe", "like", "comment", "share"],
            "brand_voice": "helpful_expert"
        }
    
    async def generate_script(
        self,
        topic: str,
        duration: int = 600,
        script_type: str = "educational",
        keywords: Optional[List[str]] = None,
        target_audience: str = "general"
    ) -> Script:
        """
        Generate a YouTube video script based on the given parameters.
        
        Args:
            topic: Main topic for the video
            duration: Target duration in seconds
            script_type: Type of script (educational, entertainment, tutorial)
            keywords: SEO keywords to include
            target_audience: Target audience demographic
        
        Returns:
            Generated Script object
        """
        await self.log_info(f"Starting script generation for topic: {topic}")
        
        try:
            # Generate script content using OpenAI
            script_content = await self._generate_script_content(
                topic, duration, script_type, keywords, target_audience
            )
            
            # Create Script object
            script = Script(
                title=await self._generate_title(topic, keywords),
                content=script_content,
                duration=duration,
                topic=topic,
                script_type=script_type,
                keywords=keywords or [],
                target_audience=target_audience,
                seo_score=await self._calculate_seo_score(script_content, keywords)
            )
            
            # Validate script quality
            quality_score = await self._validate_script_quality(script)
            script.quality_score = quality_score
            
            await self.log_info(f"Script generated successfully. Quality score: {quality_score}")
            
            return script
            
        except Exception as e:
            await self.log_error(f"Script generation failed: {e}")
            raise
    
    async def _generate_script_content(
        self,
        topic: str,
        duration: int,
        script_type: str,
        keywords: Optional[List[str]],
        target_audience: str
    ) -> str:
        """
        Generate script content using AI.
        
        Args:
            topic: Main topic
            duration: Target duration
            script_type: Script type
            keywords: SEO keywords
            target_audience: Target audience
        
        Returns:
            Generated script content
        """
        # This would integrate with OpenAI API
        # For now, return a structured placeholder
        
        template = self.script_templates.get(script_type, self.script_templates["educational"])
        
        # Calculate section durations
        main_duration = duration - 90  # Total minus intro/outro sections
        
        # Mock content generation (would be replaced with actual AI generation)
        script_content = template.format(
            hook_content=f"Did you know that {topic} could revolutionize the way we think about technology?",
            introduction=f"Welcome back to the channel! Today we're diving deep into {topic}.",
            main_content=f"Let's explore the fascinating world of {topic} and understand why it matters.",
            conclusion=f"That wraps up our exploration of {topic}. I hope you found this insightful!",
            cta_content="Don't forget to like this video and subscribe for more content like this!",
            main_duration=main_duration,
            problem=f"Many people struggle with understanding {topic}",
            overview=f"In this tutorial, we'll cover everything you need to know about {topic}",
            steps="Step 1: Understanding the basics...\nStep 2: Practical applications...",
            recap=f"To recap what we learned about {topic}...",
            tutorial_duration=main_duration
        )
        
        return script_content
    
    async def _generate_title(self, topic: str, keywords: Optional[List[str]]) -> str:
        """
        Generate an SEO-optimized title for the video.
        
        Args:
            topic: Main topic
            keywords: SEO keywords
        
        Returns:
            Generated title
        """
        # Mock title generation (would be replaced with AI)
        base_title = f"The Complete Guide to {topic}"
        
        if keywords:
            # Incorporate primary keyword if available
            primary_keyword = keywords[0]
            base_title = f"{primary_keyword}: {base_title}"
        
        return base_title
    
    async def _calculate_seo_score(self, content: str, keywords: Optional[List[str]]) -> float:
        """
        Calculate SEO score for the script content.
        
        Args:
            content: Script content
            keywords: Target keywords
        
        Returns:
            SEO score (0.0 to 1.0)
        """
        if not keywords:
            return 0.5
        
        score = 0.0
        content_lower = content.lower()
        
        # Check keyword density
        for keyword in keywords:
            keyword_count = content_lower.count(keyword.lower())
            # Optimal keyword density is 1-3%
            keyword_density = keyword_count / len(content.split())
            if 0.01 <= keyword_density <= 0.03:
                score += 0.2
            elif keyword_count > 0:
                score += 0.1
        
        # Basic content structure checks
        if "[HOOK" in content:
            score += 0.2
        if "[CALL_TO_ACTION" in content or "subscribe" in content_lower:
            score += 0.2
        if len(content) > 500:  # Adequate length
            score += 0.2
        
        return min(score, 1.0)
    
    async def _validate_script_quality(self, script: Script) -> float:
        """
        Validate the quality of the generated script.
        
        Args:
            script: Script object to validate
        
        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 0.0
        
        # Check script structure
        if "[HOOK" in script.content:
            score += 0.2
        if "[INTRODUCTION" in script.content or "[INTRO" in script.content:
            score += 0.2
        if "[MAIN" in script.content:
            score += 0.2
        if "[CONCLUSION" in script.content or "[OUTRO" in script.content:
            score += 0.2
        if "[CALL_TO_ACTION" in script.content:
            score += 0.2
        
        return score
    
    async def run(self) -> None:
        """
        Main agent run loop.
        
        Processes script generation requests and maintains agent status.
        """
        await self.log_info("Scriptwriter Agent started")
        
        while self.is_running:
            try:
                # Check for script generation requests in Supabase
                await self._process_script_requests()
                
                # Wait before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                await self.log_error(f"Error in script processing: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _process_script_requests(self) -> None:
        """
        Process pending script generation requests from the database.
        """
        try:
            if not self.supabase_client:
                return
            
            # Query for pending script requests
            result = self.supabase_client.table("script_requests").select("*").eq(
                "status", "pending"
            ).limit(5).execute()
            
            for request in result.data:
                try:
                    # Generate script
                    script = await self.generate_script(
                        topic=request["topic"],
                        duration=request.get("duration", 600),
                        script_type=request.get("script_type", "educational"),
                        keywords=request.get("keywords"),
                        target_audience=request.get("target_audience", "general")
                    )
                    
                    # Update request status
                    self.supabase_client.table("script_requests").update({
                        "status": "completed",
                        "script_id": script.id,
                        "completed_at": script.created_at.isoformat()
                    }).eq("id", request["id"]).execute()
                    
                    await self.log_info(f"Completed script request {request['id']}")
                    
                except Exception as e:
                    # Mark request as failed
                    self.supabase_client.table("script_requests").update({
                        "status": "failed",
                        "error_message": str(e)
                    }).eq("id", request["id"]).execute()
                    
                    await self.log_error(f"Failed script request {request['id']}: {e}")
        
        except Exception as e:
            await self.log_error(f"Error processing script requests: {e}")


# Convenience function for direct usage
async def generate_script(
    topic: str,
    duration: int = 600,
    script_type: str = "educational",
    keywords: Optional[List[str]] = None,
    target_audience: str = "general"
) -> Script:
    """
    Convenience function to generate a script without instantiating the agent.
    
    Args:
        topic: Main topic for the video
        duration: Target duration in seconds
        script_type: Type of script (educational, entertainment, tutorial)
        keywords: SEO keywords to include
        target_audience: Target audience demographic
    
    Returns:
        Generated Script object
    """
    agent = ScriptwriterAgent("scriptwriter_standalone")
    return await agent.generate_script(topic, duration, script_type, keywords, target_audience)