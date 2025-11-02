"""
Utility functions for DeepSeek client
"""

import re
from typing import Optional


def sanitize_api_key(text: str, api_key: Optional[str] = None) -> str:
    """
    Sanitize API key from text (logs, error messages, etc.)
    
    Args:
        text: Text that may contain API key
        api_key: Optional API key to mask (if None, will detect common patterns)
    
    Returns:
        Text with API key masked/replaced
    """
    if not text:
        return text
    
    # If specific key provided, mask it directly
    if api_key and api_key in text:
        # Mask all but first 4 and last 4 characters
        masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
        text = text.replace(api_key, masked)
    
    # Also mask common API key patterns (sk-..., deepseek-..., etc.)
    # Pattern: Common API key formats with visible characters
    patterns = [
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI-style keys (sk-...)
        r'deepseek-[a-zA-Z0-9]{20,}',  # DeepSeek-style keys
        r'[a-zA-Z0-9]{32,}',  # Generic long alphanumeric keys
    ]
    
    for pattern in patterns:
        text = re.sub(
            pattern,
            lambda m: m.group()[:4] + "*" * max(0, len(m.group()) - 8) + m.group()[-4:] if len(m.group()) > 8 else "****",
            text
        )
    
    return text

