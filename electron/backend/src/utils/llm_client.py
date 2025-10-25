#!/usr/bin/env python3
"""
LLM Client - Claude API wrapper for LocalBrain ingestion
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMClient:
    """Wrapper for Claude API calls."""
    
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        """Initialize Claude client."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def call(self, prompt: str, system: str = None, max_tokens: int = 2048, temperature: float = 0.0) -> str:
        """
        Make a Claude API call.
        
        Args:
            prompt: User message
            system: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            
        Returns:
            Response text from Claude
        """
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system:
            kwargs["system"] = system
        
        response = self.client.messages.create(**kwargs)
        return response.content[0].text
    
    def call_json(self, prompt: str, system: str = None, max_tokens: int = 2048) -> dict:
        """
        Make a Claude API call expecting JSON response.
        
        Returns:
            Parsed JSON dict
        """
        import json
        
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nReturn ONLY valid JSON, no other text."
        
        response_text = self.call(json_prompt, system, max_tokens, temperature=0.0)
        
        # Extract JSON from response (handle markdown code blocks)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        return json.loads(response_text.strip())
