"""
DeepSeek client implementation with OpenAI-compatible interface
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion


def deepseek_chat(
    messages: List[Dict[str, str]], 
    temperature: float = 0.1, 
    max_tokens: int = 700
) -> str:
    """
    Send chat completion request to DeepSeek API.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        temperature: Sampling temperature (0.0 to 1.0, default: 0.1)
        max_tokens: Maximum tokens in response (default: 700)
    
    Returns:
        Content string from the assistant's response
        
    Raises:
        ValueError: If API key is missing or invalid
        Exception: For API errors, network issues, or other failures
    """
    # Get API key from environment
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    # Initialize OpenAI client with DeepSeek configuration
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
    
    try:
        # Send chat completion request
        response: ChatCompletion = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False  # No streaming for MVP
        )
        
        # Extract content from response
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        else:
            raise Exception("No response content received from DeepSeek API")
            
    except Exception as e:
        # Re-raise with more context
        raise Exception(f"DeepSeek API error: {str(e)}") from e
