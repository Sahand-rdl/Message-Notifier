from typing import Tuple
from core.providers.base import MessageObservations

def evaluate_safety_gate(
    observations: MessageObservations, 
    current_action: str, 
    current_msg_type: str, 
    current_reason: str, 
    current_confidence: float
) -> Tuple[str, str, str, float, bool]:
    """
    Applies the uncompromising Strict Evidence Integrity Gate.
    If observations flag potential safety issues, forces mute and invalidates media.
    
    Returns: (action, message_type, reason, confidence, valid_media)
    """
    if (observations.text_instruction_present or 
        observations.is_scam_or_fraud or 
        observations.possible_manipulation):
        
        override_type = "scam" if observations.is_scam_or_fraud else "spam"
        
        return (
            "mute", 
            override_type, 
            "Blocked by strict evidence integrity gate.", 
            1.0, 
            False # valid_media flag forced to False
        )
        
    return current_action, current_msg_type, current_reason, current_confidence, True
