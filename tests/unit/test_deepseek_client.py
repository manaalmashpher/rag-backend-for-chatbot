"""
Unit tests for DeepSeek client - Story 9.4
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai import AuthenticationError as OpenAIAuthenticationError
from openai import APIError as OpenAIAPIError

from app.deps.deepseek_client import deepseek_chat, _get_api_key
from app.deps.exceptions import MissingAPIKeyError, InvalidAPIKeyError
from app.deps.utils import sanitize_api_key


class TestDeepSeekClient:
    """Test cases for DeepSeek client functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.valid_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the weather today?"}
        ]
        
        self.mock_response = ChatCompletion(
            id="test-id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="I cannot provide weather information.",
                        role="assistant"
                    )
                )
            ],
            created=1234567890,
            model="deepseek-chat",
            object="chat.completion"
        )
    
    # AC1: Settings integration tests
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_settings_api_key_takes_precedence_over_env_var(self, mock_openai_class, mock_settings):
        """9.4-UNIT-001: Settings API key takes precedence over env var"""
        # Arrange
        mock_settings.deepseek_api_key = "settings_key_12345"
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env_key_67890"}):
            result = deepseek_chat(self.valid_messages)
        
        # Assert - Settings key should be used
        mock_openai_class.assert_called_once_with(
            api_key="settings_key_12345",
            base_url="https://api.deepseek.com/v1"
        )
        assert result == "I cannot provide weather information."
    
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_env_var_used_as_fallback_when_settings_none(self, mock_openai_class, mock_settings):
        """9.4-UNIT-002: Env var used as fallback when Settings is None"""
        # Arrange
        mock_settings.deepseek_api_key = None
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env_key_67890"}):
            result = deepseek_chat(self.valid_messages)
        
        # Assert - Env var should be used
        mock_openai_class.assert_called_once_with(
            api_key="env_key_67890",
            base_url="https://api.deepseek.com/v1"
        )
        assert result == "I cannot provide weather information."
    
    @patch("app.deps.deepseek_client.settings")
    def test_empty_string_in_settings_treated_as_missing(self, mock_settings):
        """9.4-UNIT-003: Empty string in Settings treated as missing"""
        # Arrange
        mock_settings.deepseek_api_key = ""
        
        # Act & Assert
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(MissingAPIKeyError):
                deepseek_chat(self.valid_messages)
    
    # AC3: Error handling tests
    @patch("app.deps.deepseek_client.settings")
    def test_missing_api_key_error_raised(self, mock_settings):
        """9.4-UNIT-004: MissingAPIKeyError raised when no key provided"""
        # Arrange
        mock_settings.deepseek_api_key = None
        
        # Act & Assert
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(MissingAPIKeyError) as exc_info:
                deepseek_chat(self.valid_messages)
            assert "DeepSeek API key is required" in str(exc_info.value)
    
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_invalid_api_key_error_raised_on_auth_error(self, mock_openai_class, mock_settings):
        """9.4-UNIT-005: InvalidAPIKeyError raised when openai.AuthenticationError caught"""
        # Arrange
        mock_settings.deepseek_api_key = "invalid_key"
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = OpenAIAuthenticationError(
            "Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"message": "Invalid API key"}}
        )
        
        # Act & Assert
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            deepseek_chat(self.valid_messages)
        assert "invalid or authentication failed" in str(exc_info.value).lower()
    
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_api_key_sanitized_in_exception_messages(self, mock_openai_class, mock_settings):
        """9.4-UNIT-006: API key sanitized in exception messages and logs"""
        # Arrange
        api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        mock_settings.deepseek_api_key = api_key
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        # Create exception that might contain the key
        error_msg = f"Authentication failed with key {api_key}"
        mock_client.chat.completions.create.side_effect = OpenAIAuthenticationError(
            error_msg,
            response=Mock(status_code=401),
            body={"error": {"message": error_msg}}
        )
        
        # Act & Assert
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            deepseek_chat(self.valid_messages)
        
        # Verify error message doesn't contain full API key
        error_str = str(exc_info.value)
        assert api_key not in error_str
        assert "sk-1" in error_str or "****" in error_str or "invalid" in error_str.lower()
    
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_other_openai_exceptions_not_treated_as_auth_errors(self, mock_openai_class, mock_settings):
        """9.4-UNIT-007: Other OpenAI exceptions (APIError) not treated as auth errors"""
        # Arrange
        mock_settings.deepseek_api_key = "test_key"
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        # Use a generic Exception to simulate a non-auth API error
        # (OpenAIAPIError requires request param which is complex to mock)
        # The important part is that it's NOT InvalidAPIKeyError
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        
        # Act & Assert - Should raise generic Exception, not InvalidAPIKeyError
        with pytest.raises(Exception) as exc_info:
            deepseek_chat(self.valid_messages)
        assert not isinstance(exc_info.value, InvalidAPIKeyError)
        assert "DeepSeek API error" in str(exc_info.value)
    
    # AC4: Error message tests
    @patch("app.deps.deepseek_client.settings")
    def test_missing_api_key_error_message_clear(self, mock_settings):
        """9.4-UNIT-008: MissingAPIKeyError message clearly indicates missing key"""
        # Arrange
        mock_settings.deepseek_api_key = None
        
        # Act & Assert
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(MissingAPIKeyError) as exc_info:
                deepseek_chat(self.valid_messages)
            message = str(exc_info.value)
            assert "required" in message.lower() or "missing" in message.lower()
            assert "DEEPSEEK_API_KEY" in message or "Settings.deepseek_api_key" in message
    
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_invalid_api_key_error_message_clear(self, mock_openai_class, mock_settings):
        """9.4-UNIT-009: InvalidAPIKeyError message clearly indicates invalid key"""
        # Arrange
        mock_settings.deepseek_api_key = "invalid"
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = OpenAIAuthenticationError(
            "Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"message": "Invalid API key"}}
        )
        
        # Act & Assert
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            deepseek_chat(self.valid_messages)
        message = str(exc_info.value)
        assert "invalid" in message.lower() or "authentication failed" in message.lower()
    
    # AC6: Health check tests
    @patch("app.deps.deepseek_client.settings")
    @patch("app.deps.deepseek_client.OpenAI")
    def test_health_check_function_only_checks_config_existence(self, mock_openai_class, mock_settings):
        """9.4-UNIT-011: Health check function only checks config existence (no API call logic)"""
        # This test verifies that _get_api_key doesn't make API calls
        # Just checking configuration logic
        mock_settings.deepseek_api_key = "test_key"
        
        # Act
        result = _get_api_key()
        
        # Assert - No OpenAI client should be created
        assert result == "test_key"
        mock_openai_class.assert_not_called()
    
    # Legacy tests (maintaining backward compatibility)
    @patch("app.deps.deepseek_client.settings")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_successful_api_call(self, mock_openai_class, mock_settings):
        """Test successful API call with mock responses"""
        # Arrange - Mock settings to return None so env var is used
        mock_settings.deepseek_api_key = None
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act
        result = deepseek_chat(self.valid_messages)
        
        # Assert
        assert result == "I cannot provide weather information."
        mock_openai_class.assert_called_once_with(
            api_key="test_key_12345",
            base_url="https://api.deepseek.com/v1"
        )
    
    @patch("app.deps.deepseek_client.settings")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_custom_parameters(self, mock_openai_class, mock_settings):
        """Test function with custom temperature and max_tokens"""
        # Arrange
        mock_settings.deepseek_api_key = None  # Use env var
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act
        result = deepseek_chat(self.valid_messages, temperature=0.5, max_tokens=1000)
        
        # Assert
        assert result == "I cannot provide weather information."
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=self.valid_messages,
            temperature=0.5,
            max_tokens=1000,
            stream=False
        )
    
    @patch("app.deps.deepseek_client.settings")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_api_error_handling(self, mock_openai_class, mock_settings):
        """Test error handling for API failures"""
        # Arrange
        mock_settings.deepseek_api_key = None  # Use env var
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        
        # Act & Assert
        with pytest.raises(Exception, match="DeepSeek API error"):
            deepseek_chat(self.valid_messages)
    
    @patch("app.deps.deepseek_client.settings")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_empty_response_content(self, mock_openai_class, mock_settings):
        """Test handling of empty response content"""
        # Arrange
        mock_settings.deepseek_api_key = None  # Use env var
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        empty_response = ChatCompletion(
            id="test-id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        role="assistant"
                    )
                )
            ],
            created=1234567890,
            model="deepseek-chat",
            object="chat.completion"
        )
        mock_client.chat.completions.create.return_value = empty_response
        
        # Act
        result = deepseek_chat(self.valid_messages)
        
        # Assert
        assert result == ""
    
    @patch("app.deps.deepseek_client.settings")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_no_choices_in_response(self, mock_openai_class, mock_settings):
        """Test handling of response with no choices"""
        # Arrange
        mock_settings.deepseek_api_key = None  # Use env var
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        no_choices_response = ChatCompletion(
            id="test-id",
            choices=[],
            created=1234567890,
            model="deepseek-chat",
            object="chat.completion"
        )
        mock_client.chat.completions.create.return_value = no_choices_response
        
        # Act & Assert
        with pytest.raises(Exception, match="No response content received from DeepSeek API"):
            deepseek_chat(self.valid_messages)


class TestSanitizeAPIKey:
    """Tests for API key sanitization utility"""
    
    def test_sanitize_specific_key(self):
        """Test sanitization of a specific API key"""
        api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        text = f"Error with key {api_key} occurred"
        
        result = sanitize_api_key(text, api_key)
        
        assert api_key not in result
        assert "sk-1" in result or "****" in result
    
    def test_sanitize_pattern_detection(self):
        """Test sanitization detects common API key patterns"""
        text = "Error: sk-1234567890abcdefghijklmnopqrstuvwxyz is invalid"
        
        result = sanitize_api_key(text)
        
        # Should mask the key pattern
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in result
