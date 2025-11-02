"""
Custom exceptions for DeepSeek API authentication
"""


class DeepSeekAuthError(Exception):
    """Base exception for DeepSeek authentication errors"""
    pass


class MissingAPIKeyError(DeepSeekAuthError):
    """Raised when DeepSeek API key is missing or empty"""
    
    def __init__(self, message: str = "DeepSeek API key is required. Please configure DEEPSEEK_API_KEY environment variable or Settings.deepseek_api_key"):
        self.message = message
        super().__init__(self.message)


class InvalidAPIKeyError(DeepSeekAuthError):
    """Raised when DeepSeek API key is invalid or authentication fails"""
    
    def __init__(self, message: str = "DeepSeek API key is invalid or authentication failed. Please verify your API key configuration"):
        self.message = message
        super().__init__(self.message)

