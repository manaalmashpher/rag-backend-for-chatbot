"""
Unit tests for ChatOrchestrator follow-up aware retrieval helper methods
"""

import pytest
from app.services.chat_orchestrator import ChatOrchestrator


class TestExtractSectionId:
    """Test cases for _extract_section_id helper method"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.orchestrator = ChatOrchestrator()
    
    def test_extract_section_id_standard_format(self):
        """Test extracting standard section ID format (5.22.3)"""
        text = "what's in section 5.22.3"
        result = self.orchestrator._extract_section_id(text)
        assert result == "5.22.3"
    
    def test_extract_section_id_simple_format(self):
        """Test extracting simple section ID format (1.2)"""
        text = "explain section 1.2"
        result = self.orchestrator._extract_section_id(text)
        assert result == "1.2"
    
    def test_extract_section_id_complex_format(self):
        """Test extracting complex section ID format (10.5.3.2)"""
        text = "what's in section 10.5.3.2"
        result = self.orchestrator._extract_section_id(text)
        assert result == "10.5.3.2"
    
    def test_extract_section_id_no_match(self):
        """Test extracting section ID when none exists"""
        text = "what is machine learning?"
        result = self.orchestrator._extract_section_id(text)
        assert result is None
    
    def test_extract_section_id_first_match(self):
        """Test that first section ID is returned when multiple present"""
        text = "sections 5.22.3 and 1.2 are important"
        result = self.orchestrator._extract_section_id(text)
        assert result == "5.22.3"
    
    def test_extract_section_id_empty_string(self):
        """Test extracting section ID from empty string"""
        text = ""
        result = self.orchestrator._extract_section_id(text)
        assert result is None
    
    def test_extract_section_id_version_number(self):
        """Test that version numbers like 1.2.3 are matched (same pattern)"""
        text = "version 1.2.3 is available"
        result = self.orchestrator._extract_section_id(text)
        assert result == "1.2.3"


class TestIsAmbiguousFollowup:
    """Test cases for _is_ambiguous_followup helper method"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.orchestrator = ChatOrchestrator()
    
    def test_ambiguous_followup_with_this(self):
        """Test ambiguous follow-up with 'this' pronoun"""
        query = "what do I need to submit for this?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True
    
    def test_ambiguous_followup_with_it(self):
        """Test ambiguous follow-up with 'it' pronoun"""
        query = "what are the indicators for it?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True
    
    def test_non_ambiguous_explicit_section(self):
        """Test non-ambiguous query with explicit section ID"""
        query = "explain section 5.22.3"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is False
    
    def test_non_ambiguous_no_pronouns(self):
        """Test non-ambiguous query without pronouns"""
        query = "give me an overview of the framework"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is False
    
    def test_non_ambiguous_with_section_id(self):
        """Test query with section ID even if it has pronouns"""
        query = "what is the evidence for this section 5.22.3?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is False
    
    def test_ambiguous_followup_for_this_phrase(self):
        """Test ambiguous follow-up with 'for this' phrase"""
        query = "what are the requirements for this?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True
    
    def test_ambiguous_followup_for_that_phrase(self):
        """Test ambiguous follow-up with 'for that' phrase"""
        query = "what do I need for that?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True
    
    def test_boundary_length_exactly_80_chars(self):
        """Test query exactly 80 characters with pronoun"""
        query = "a" * 79 + " this"  # 79 + 5 = 84, but let's make it exactly 80
        query = "a" * 75 + " this"  # 75 + 5 = 80
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is False  # >= 80 should be False
    
    def test_boundary_length_79_chars(self):
        """Test query 79 characters with pronoun"""
        query = "a" * 74 + " this"  # 74 + 5 = 79
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True  # < 80 should be True
    
    def test_ambiguous_followup_with_them(self):
        """Test ambiguous follow-up with 'them' pronoun"""
        query = "what are the requirements for them?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True
    
    def test_ambiguous_followup_with_those(self):
        """Test ambiguous follow-up with 'those' pronoun"""
        query = "what are the requirements for those?"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is True
    
    def test_very_long_query_with_pronoun(self):
        """Test very long query (>200 chars) with pronoun should not be ambiguous"""
        query = "a" * 200 + " this"
        result = self.orchestrator._is_ambiguous_followup(query)
        assert result is False


class TestGetLastSectionIdFromHistory:
    """Test cases for _get_last_section_id_from_history helper method"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.orchestrator = ChatOrchestrator()
    
    def test_history_with_section_id_in_last_user_message(self):
        """Test history with section ID in last user message"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."}
        ]
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result == "5.22.3"
    
    def test_history_with_section_id_in_earlier_message(self):
        """Test history with section ID in earlier user message"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."},
            {"role": "user", "content": "thanks"},
            {"role": "assistant", "content": "you're welcome"}
        ]
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result == "5.22.3"
    
    def test_history_with_multiple_section_ids(self):
        """Test history with multiple section IDs returns most recent"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."},
            {"role": "user", "content": "what about section 1.2?"},
            {"role": "assistant", "content": "Section 1.2 contains..."}
        ]
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result == "1.2"  # Most recent
    
    def test_history_without_section_ids(self):
        """Test history without section IDs"""
        history = [
            {"role": "user", "content": "what is machine learning?"},
            {"role": "assistant", "content": "Machine learning is..."}
        ]
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result is None
    
    def test_empty_history(self):
        """Test empty history"""
        history = []
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result is None
    
    def test_history_with_only_assistant_messages(self):
        """Test history with only assistant messages"""
        history = [
            {"role": "assistant", "content": "Hello, how can I help?"},
            {"role": "assistant", "content": "I'm here to assist."}
        ]
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result is None
    
    def test_history_section_id_in_middle(self):
        """Test history with section ID in middle of conversation"""
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3..."},
            {"role": "user", "content": "thanks"}
        ]
        result = self.orchestrator._get_last_section_id_from_history(history)
        assert result == "5.22.3"


class TestBuildRetrievalQuery:
    """Test cases for _build_retrieval_query helper method"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.orchestrator = ChatOrchestrator()
    
    def test_explicit_section_id_returns_unchanged(self):
        """Test that explicit section ID in current message returns unchanged"""
        history = []
        current_message = "what's in section 5.22.3"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        assert result == current_message
    
    def test_non_ambiguous_query_returns_unchanged(self):
        """Test that non-ambiguous query returns unchanged"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."}
        ]
        current_message = "give me an overview of the framework"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        assert result == current_message
    
    def test_ambiguous_followup_with_history_section_id(self):
        """Test ambiguous follow-up with history section ID returns augmented query"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."}
        ]
        current_message = "what do I need to submit for this?"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        assert "5.22.3" in result
        assert current_message in result
        assert result.startswith("For section")
    
    def test_ambiguous_followup_without_history_section_id(self):
        """Test ambiguous follow-up without history section ID returns unchanged"""
        history = [
            {"role": "user", "content": "what is machine learning?"},
            {"role": "assistant", "content": "Machine learning is..."}
        ]
        current_message = "what do I need to submit for this?"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        assert result == current_message
    
    def test_ambiguous_followup_empty_history(self):
        """Test ambiguous follow-up with empty history returns unchanged"""
        history = []
        current_message = "what do I need to submit for this?"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        assert result == current_message
    
    def test_augmented_query_format(self):
        """Test that augmented query has correct format"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."}
        ]
        current_message = "what do I need to submit for this?"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        expected = f"For section 5.22.3, {current_message}"
        assert result == expected
    
    def test_multiple_ambiguous_followups_uses_most_recent_section(self):
        """Test that multiple ambiguous follow-ups use most recent section ID"""
        history = [
            {"role": "user", "content": "what's in section 5.22.3"},
            {"role": "assistant", "content": "Section 5.22.3 contains..."},
            {"role": "user", "content": "what about section 1.2?"},
            {"role": "assistant", "content": "Section 1.2 contains..."}
        ]
        current_message = "what do I need to submit for this?"
        result = self.orchestrator._build_retrieval_query(history, current_message)
        assert "1.2" in result  # Most recent section
        assert "5.22.3" not in result

