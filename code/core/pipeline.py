import difflib
from typing import Dict, Any
from core.providers.base import BaseProvider
from core.decision_engine import make_decision
from core.safety_gate import evaluate_safety_gate
from core.data_loader import DataLoader
import os

ALLOWED_MESSAGE_TYPES = [
    'personal', 'urgent', 'event', 'payment', 'business_update',
    'promotion', 'greeting', 'forward', 'spam', 'scam', 'unknown'
]

def match_schema_value(value: str, allowed_values: list[str]) -> str:
    """Three-Tier Schema Matcher to recover model-suggested categories."""
    if not value:
        return 'unknown'
    
    val_lower = value.lower().strip()
    
    # 1. Exact match
    if val_lower in allowed_values:
        return val_lower
        
    # 2. Token-subset match (e.g. "payment alert" -> "payment")
    for allowed in allowed_values:
        if allowed in val_lower or val_lower in allowed:
            return allowed
            
    # 3. Fuzzy match fallback
    matches = difflib.get_close_matches(val_lower, allowed_values, n=1, cutoff=0.6)
    if matches:
        return matches[0]
        
    return 'unknown'

def process_message(
    message: Dict[str, Any], 
    provider: BaseProvider, 
    data_loader: DataLoader,
    dataset_dir: str
) -> Dict[str, Any]:
    """
    Main orchestration loop for processing a single message.
    """
    media_type = message.get('media_type', '')
    media_id = message.get('media_id', '')
    media_path = None
    
    if media_type == 'image' and media_id in data_loader.images:
        media_path = os.path.join(dataset_dir, data_loader.images[media_id])
    elif media_type == 'voice' and media_id in data_loader.voice_notes:
        media_path = os.path.join(dataset_dir, data_loader.voice_notes[media_id])
        
    # LOOK Phase
    try:
        history = data_loader.user_message_history.get(message['user_id'], [])
        observations = provider.extract_observations(
            text=message.get('message_text', ''),
            media_path=media_path,
            media_type=media_type,
            history=history
        )
    except Exception as e:
        # Fail closed on provider errors
        return {
            "message_id": message['message_id'],
            "action": "mute",
            "message_type": "unknown",
            "reason": f"Fallback due to provider failure: {str(e)}",
            "confidence": 1.0,
            "evidence_message_ids": "none"
        }

    # DECIDE Phase
    action, raw_msg_type, reason, confidence, python_evidence = make_decision(
        message=message, 
        observations=observations, 
        data_loader=data_loader
    )
    
    # Safety Gate Post-Audit
    action, raw_msg_type, reason, confidence, valid_media = evaluate_safety_gate(
        observations, action, raw_msg_type, reason, confidence
    )
    
    # Schema Map
    final_msg_type = match_schema_value(raw_msg_type, ALLOWED_MESSAGE_TYPES)
    
    # Format evidence IDs
    user_id = message['user_id']
    user_hist = data_loader.user_message_history.get(user_id, [])
    valid_history_ids = {h['message_id'] for h in user_hist}
    
    historical_matches = observations.historical_matches or []
    combined_raw = list(dict.fromkeys(python_evidence + historical_matches))
    valid_matches = [m for m in combined_raw if m in valid_history_ids]

    # Helper to retrieve message timestamp for chronological sorting
    def get_message_timestamp(msg_id: str) -> str:
        msg_row = data_loader.message_history.get(msg_id, {})
        return msg_row.get('created_at', '')

    # Sort valid matches so that the newest messages appear first
    valid_matches.sort(key=get_message_timestamp, reverse=True)

    # Cap the evidence list at the top 2 most recent matches
    final_evidence = valid_matches[:2]

    if not valid_media or not final_evidence:
        evidence_message_ids = "none"
    else:
        evidence_message_ids = ";".join(final_evidence)
        
    return {
        "message_id": message['message_id'],
        "action": action,
        "message_type": final_msg_type,
        "reason": reason,
        "confidence": round(confidence, 2),
        "evidence_message_ids": evidence_message_ids
    }
