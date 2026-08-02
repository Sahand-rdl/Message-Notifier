from typing import Dict, Any, Tuple, List
from core.providers.base import MessageObservations
from core.data_loader import DataLoader
from datetime import datetime

def check_quiet_hours(dnd_window: str, msg_time_str: str) -> bool:
    """Helper to determine if a message timestamp falls within the user's quiet hours."""
    if not dnd_window:
        return False
    try:
        msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00')).time()
        start_str, end_str = dnd_window.split('-')
        start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
        end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= msg_time <= end_time
        else: # Handles overnight quiet hours
            return msg_time >= start_time or msg_time <= end_time
    except Exception:
        return False

def make_decision(
    message: Dict[str, Any],
    observations: MessageObservations,
    data_loader: DataLoader
) -> Tuple[str, str, str, float, List[str]]:
    """
    Applies deterministic pure Python rules to decide action.
    Returns: (action, message_type, reason, confidence, python_evidence)
    """
    user_id = message['user_id']
    business_id = message.get('business_id')
    group_id = message.get('group_id')
    conv_type = message.get('conversation_type')
    created_at = message['created_at']
    
    # Context lookup
    user = data_loader.get_user(user_id) or {}
    
    # Defaults
    action = "digest"
    msg_type = observations.message_category_guess
    reason = "Standard processing based on observations."
    confidence = 0.8
    
    dismissed_count = 0
    muted_by_feedback = False
    python_evidence = []
    
    sender_id = message.get('sender_user_id')
    user_hist = data_loader.user_message_history.get(user_id, [])
    
    if conv_type in ['personal', 'business'] or (conv_type == 'group' and msg_type in ['forward', 'greeting', 'spam', 'scam']):
        # Scan semantic matches from VLM
        for match_id in (observations.historical_matches or []):
            h_row = data_loader.message_history.get(match_id, {})
            match_sender = False
            if conv_type == 'business' and business_id and h_row.get('business_id') == business_id:
                match_sender = True
            elif conv_type == 'personal' and sender_id and h_row.get('sender_user_id') == sender_id:
                match_sender = True
                
            if match_sender:
                event = data_loader.message_events.get((user_id, match_id), {})
                if event.get('muted_after_message') == '1':
                    muted_by_feedback = True
                    python_evidence.append(match_id)
                if event.get('notification_dismissed') == '1':
                    dismissed_count += 1
                    python_evidence.append(match_id)
                
        # Scan same-sender matches in history as fallback
        for h in user_hist:
            match_sender = False
            if conv_type == 'business' and business_id and h.get('business_id') == business_id:
                match_sender = True
            elif conv_type == 'personal' and sender_id and h.get('sender_user_id') == sender_id:
                match_sender = True
                
            if match_sender and h['message_id'] not in python_evidence:
                event = data_loader.message_events.get((user_id, h['message_id']), {})
                if event.get('muted_after_message') == '1':
                    muted_by_feedback = True
                    python_evidence.append(h['message_id'])
                if event.get('notification_dismissed') == '1':
                    dismissed_count += 1
                    python_evidence.append(h['message_id'])
                    
        # Force mute if previously muted or repeatedly dismissed
        if muted_by_feedback:
            ret_type = msg_type
            if conv_type == 'business':
                ret_type = "spam" if not observations.is_scam_or_fraud else "scam"
            return "mute", ret_type, "The user has explicitly muted this sender before.", 0.9, python_evidence
        if dismissed_count >= 2:
            if conv_type == 'business':
                ret_type = "spam" if not observations.is_scam_or_fraud else "scam"
                return "mute", ret_type, "The user has repeatedly dismissed messages from this business.", 0.9, python_evidence
            elif conv_type == 'personal' and msg_type in ['spam', 'scam', 'promotion']:
                return "mute", msg_type, "The user has repeatedly dismissed promotional messages from this personal contact.", 0.9, python_evidence
    
    # Scam & Spam checks (Handled primarily by safety_gate, but baseline fallback here)
    if observations.is_scam_or_fraud:
        return "mute", "scam", "Suspected scam or fraud detected by VLM.", 0.95, python_evidence
        
    # Domain Spoofing / Phishing Detection
    if conv_type == 'business' and business_id:
        bus_details = data_loader.business_accounts.get(business_id, {})
        verified = bus_details.get('verified', '0')
        domain_used = bus_details.get('domain_used_by_sender', '')
        official_domain = bus_details.get('official_domain', '')
        reports = int(bus_details.get('user_reports_30d', 0) or 0)
        
        if verified == '0' and official_domain and domain_used != official_domain:
            return "mute", "scam", "Suspected domain spoofing.", 0.95, python_evidence
        if verified == '0' and reports > 20:
            return "mute", "spam", "High user reports on unverified business.", 0.95, python_evidence
            
    # Muted Group Escalation Rule
    if conv_type == 'group' and group_id:
        group_membership = data_loader.group_members.get((user_id, group_id), {})
        group_muted = group_membership.get('group_muted_by_user', '0')
        
        if group_muted == '1':
            if observations.direct_mention_detected:
                action = "notify"
                reason = "Urgent direct mention escalated from muted group."
                confidence = 0.95
            else:
                return "mute", msg_type, "Group is muted by user.", 0.9, python_evidence
        else:
            group_details = data_loader.groups.get(group_id, {})
            g_type = group_details.get('group_type', '')
            g_name = group_details.get('group_name', '').lower()
            if g_type in ['school_group', 'safety'] or 'school' in g_name or 'safety' in g_name:
                if msg_type not in ['greeting', 'spam', 'scam', 'promotion']:
                    action = "notify"
                    reason = "Critical circular or safety alert in trusted group."
                
    # Direct Mention (General)
    if observations.direct_mention_detected and conv_type in ['group', 'personal'] and action != "notify":
        return "notify", msg_type, "Direct mention detected in chat.", 1.0, python_evidence
        
    # Personal Chat routing rules
    if conv_type == 'personal':
        sender_id = message.get('sender_user_id')
        user_hist = data_loader.user_message_history.get(user_id, [])
        familiar = any(h.get('sender_user_id') == sender_id for h in user_hist)
        
        if familiar:
            if observations.contains_urgent_action_items or msg_type == 'urgent' or observations.direct_mention_detected:
                action = "notify"
                reason = "Urgent personal chat from trusted contact."
            else:
                action = "digest"
                reason = "Trusted contact personal message with no immediate urgency."
        else:
            if observations.contains_urgent_action_items or msg_type == 'urgent':
                action = "notify"
                reason = "Urgent personal message from new sender."
            else:
                action = "digest"
                reason = "Message from unfamiliar sender with no urgency."
    elif msg_type == 'urgent' or observations.contains_urgent_action_items:
        action = "notify"
        reason = "Urgent action items or category detected."
        
    # Business Personalization (Sender Trust)
    if conv_type == 'business' and business_id:
        bus_details = data_loader.business_accounts.get(business_id, {})
        verified = bus_details.get('verified', '0')
        
        user_bus_history = data_loader.user_business_history.get(user_id, [])
        active_history = any(h['business_id'] == business_id for h in user_bus_history)
        
        if active_history or verified == '1':
            text_lower = message.get('message_text', '').lower()
            if any(k in text_lower for k in ['delivery', 'packed', 'arriving', 'appointment', 'prescription', 'pickup', 'scheduled']):
                action = "notify"
                reason = "Verified business transactional update."
            elif msg_type in ['payment', 'business_update', 'event', 'urgent']:
                if observations.contains_urgent_action_items or msg_type == 'payment' or msg_type == 'urgent':
                    action = "notify"
                    reason = f"Verified business alert: {msg_type}."
                else:
                    action = "digest"
                    reason = "Routine verified business update."
            else:
                action = "digest"
                reason = "Routine verified business communication."
        else:
            action = "mute"
            reason = "Unverified business sender with no active history."
            
    # Quiet Hours (do_not_disturb_window)
    dnd_window = user.get('do_not_disturb_window', '')
    if check_quiet_hours(dnd_window, created_at) and action == "notify":
        # Only demote if not urgent and no direct mention
        if not observations.direct_mention_detected and not observations.contains_urgent_action_items:
            action = "digest"
            reason = "Demoted to digest due to active do_not_disturb_window."
            
    return action, msg_type, reason, confidence, python_evidence
