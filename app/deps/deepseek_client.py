"""
DeepSeek client implementation with OpenAI-compatible interface
"""

import os
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai import AuthenticationError as OpenAIAuthenticationError
from openai import APIError as OpenAIAPIError

from app.core.config import settings
from app.deps.exceptions import MissingAPIKeyError, InvalidAPIKeyError
from app.deps.utils import sanitize_api_key

logger = logging.getLogger(__name__)


def _get_api_key(api_key: Optional[str] = None) -> str:
    """
    Get API key from parameter, Settings, or environment variable (in that order).
    
    Args:
        api_key: Optional API key parameter (takes highest precedence)
    
    Returns:
        API key string
        
    Raises:
        MissingAPIKeyError: If no API key is found
    """
    # Priority: parameter > Settings > environment variable
    resolved_key = api_key or settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
    
    # Treat empty string as missing
    if not resolved_key or resolved_key.strip() == "":
        raise MissingAPIKeyError()
    
    return resolved_key.strip()


def deepseek_chat(
    messages: List[Dict[str, str]], 
    temperature: float = 0.1, 
    max_tokens: int = 700,
    api_key: Optional[str] = None
) -> str:
    """
    Send chat completion request to DeepSeek API.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        temperature: Sampling temperature (0.0 to 1.0, default: 0.1)
        max_tokens: Maximum tokens in response (default: 700)
        api_key: Optional API key (overrides Settings/env var)
    
    Returns:
        Content string from the assistant's response
        
    Raises:
        MissingAPIKeyError: If API key is missing
        InvalidAPIKeyError: If API key is invalid or authentication fails
        Exception: For other API errors, network issues, or failures
    """
    resolved_api_key = None
    try:
        # Get API key with proper precedence
        resolved_api_key = _get_api_key(api_key)
        
        # Initialize OpenAI client with DeepSeek configuration
        # OpenAI client automatically handles Bearer token authentication
        client = OpenAI(
            api_key=resolved_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
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
            
    except MissingAPIKeyError:
        # Re-raise authentication errors as-is
        raise
    except InvalidAPIKeyError:
        # Re-raise authentication errors as-is
        raise
    except OpenAIAuthenticationError as e:
        # Convert OpenAI authentication error to our custom exception
        # Sanitize error message to avoid exposing API key
        error_msg = sanitize_api_key(str(e), resolved_api_key)
        logger.error(f"DeepSeek authentication failed: {sanitize_api_key(error_msg)}")
        raise InvalidAPIKeyError("DeepSeek API key is invalid or authentication failed. Please verify your API key configuration") from e
    except OpenAIAPIError as e:
        # Other OpenAI API errors (non-authentication)
        error_msg = sanitize_api_key(str(e), resolved_api_key)
        logger.error(f"DeepSeek API error: {sanitize_api_key(error_msg)}")
        raise Exception(f"DeepSeek API error: {sanitize_api_key(error_msg)}") from e
    except Exception as e:
        # Other errors (network, etc.) - sanitize any potential API key exposure
        error_msg = sanitize_api_key(str(e), resolved_api_key)
        logger.error(f"DeepSeek API error: {sanitize_api_key(error_msg)}")
        raise Exception(f"DeepSeek API error: {sanitize_api_key(error_msg)}") from e
