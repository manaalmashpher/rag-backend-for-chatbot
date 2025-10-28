"""
Unit tests for DeepSeek client
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from app.deps.deepseek_client import deepseek_chat


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
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_successful_api_call(self, mock_openai_class):
        """Test successful API call with mock responses"""
        # Arrange
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
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=self.valid_messages,
            temperature=0.1,
            max_tokens=700,
            stream=False
        )
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_custom_parameters(self, mock_openai_class):
        """Test function with custom temperature and max_tokens"""
        # Arrange
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
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        """Test error handling for missing API key"""
        # Act & Assert
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY environment variable is required"):
            deepseek_chat(self.valid_messages)
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""})
    def test_empty_api_key(self):
        """Test error handling for empty API key"""
        # Act & Assert
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY environment variable is required"):
            deepseek_chat(self.valid_messages)
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_api_error_handling(self, mock_openai_class):
        """Test error handling for API failures"""
        # Arrange
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        
        # Act & Assert
        with pytest.raises(Exception, match="DeepSeek API error: API rate limit exceeded"):
            deepseek_chat(self.valid_messages)
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_empty_response_content(self, mock_openai_class):
        """Test handling of empty response content"""
        # Arrange
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
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_no_choices_in_response(self, mock_openai_class):
        """Test handling of response with no choices"""
        # Arrange
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
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_parameter_validation_temperature_range(self, mock_openai_class):
        """Test parameter validation for temperature range"""
        # Arrange
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act - Test valid temperature values
        deepseek_chat(self.valid_messages, temperature=0.0)
        deepseek_chat(self.valid_messages, temperature=1.0)
        deepseek_chat(self.valid_messages, temperature=0.5)
        
        # Assert - All calls should succeed
        assert mock_client.chat.completions.create.call_count == 3
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_parameter_validation_max_tokens(self, mock_openai_class):
        """Test parameter validation for max_tokens"""
        # Arrange
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act - Test various max_tokens values
        deepseek_chat(self.valid_messages, max_tokens=1)
        deepseek_chat(self.valid_messages, max_tokens=1000)
        deepseek_chat(self.valid_messages, max_tokens=4000)
        
        # Assert - All calls should succeed
        assert mock_client.chat.completions.create.call_count == 3
    
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key_12345"})
    @patch("app.deps.deepseek_client.OpenAI")
    def test_openai_compatible_interface(self, mock_openai_class):
        """Test OpenAI-compatible interface compliance"""
        # Arrange
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = self.mock_response
        
        # Act
        result = deepseek_chat(self.valid_messages)
        
        # Assert
        assert isinstance(result, str)
        assert result == "I cannot provide weather information."
        
        # Verify OpenAI client was initialized correctly
        mock_openai_class.assert_called_once_with(
            api_key="test_key_12345",
            base_url="https://api.deepseek.com/v1"
        )
        
        # Verify correct model and parameters were used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "deepseek-chat"
        assert call_args.kwargs["messages"] == self.valid_messages
        assert call_args.kwargs["temperature"] == 0.1
        assert call_args.kwargs["max_tokens"] == 700
        assert call_args.kwargs["stream"] is False
