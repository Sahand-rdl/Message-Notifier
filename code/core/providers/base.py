from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class MessageObservations(BaseModel):
    """
    Strictly typed JSON structure containing observations extracted by the VLM.
    This is the core output of the LOOK phase.
    """
    message_category_guess: str  # 'personal', 'alert', 'transaction', 'promo', 'scam', 'greeting'
    contains_urgent_action_items: bool
    direct_mention_detected: bool  # True if the user's name/ID is explicitly mentioned
    non_original_media: bool  # True if stock/watermarked image
    text_instruction_present: bool  # True if prompt injection attempt is visible
    possible_manipulation: bool
    is_scam_or_fraud: bool # True if suspected scam/phishing
    transcribed_text: Optional[str] = None  # Filled for voice notes
    extracted_image_text: Optional[str] = None  # Text parsed from images
    historical_matches: List[str]  # List of semantic message_ids from history matching this content


class ProviderException(Exception):
    """Base exception for provider-related errors to ensure consistent handling."""
    pass


class BaseProvider(ABC):
    """
    Stable provider interface for the VLM/LLM. 
    Guarantees the router pipeline doesn't care which LLM is used.
    """

    @abstractmethod
    def extract_observations(
        self, 
        text: Optional[str] = None, 
        media_path: Optional[str] = None, 
        media_type: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> MessageObservations:
        """
        Parses the provided text and/or media to extract structured observations.
        
        Args:
            text: Optional text content of the message.
            media_path: Optional path to the media file (image or audio).
            media_type: Type of media ('image' or 'voice').
            history: Optional list of historical messages for the user.
            
        Returns:
            MessageObservations object.
            
        Raises:
            ProviderException: If the API fails, rate limits, or returns invalid schema.
        """
        pass
