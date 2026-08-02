from typing import List, Dict, Any

def score_predictions(predictions: List[Dict[str, Any]], ground_truths: List[Dict[str, Any]]):
    """
    Calculates offline metrics against ground truth.
    """
    total = len(predictions)
    if total == 0:
        print("No predictions to evaluate.")
        return
        
    action_correct = 0
    type_correct = 0
    
    correct_conf_sum = 0
    correct_conf_count = 0
    incorrect_conf_sum = 0
    incorrect_conf_count = 0
    
    jaccard_sum = 0
    mismatches = []
    
    # Map ground truth by message_id
    gt_map = {gt['message_id']: gt for gt in ground_truths}
    
    for pred in predictions:
        msg_id = pred['message_id']
        gt = gt_map.get(msg_id)
        if not gt:
            continue
            
        # 1. Action Accuracy
        if pred['action'] == gt['action']:
            action_correct += 1
            correct_conf_sum += float(pred['confidence'])
            correct_conf_count += 1
        else:
            incorrect_conf_sum += float(pred['confidence'])
            incorrect_conf_count += 1
            mismatches.append({
                'id': msg_id,
                'type': 'Action Mismatch',
                'pred': pred['action'],
                'expected': gt['action'],
                'reason': pred.get('reason', '')
            })
            
        # 2. Type Accuracy
        if pred['message_type'] == gt['message_type']:
            type_correct += 1
        else:
            mismatches.append({
                'id': msg_id,
                'type': 'Type Mismatch',
                'pred': pred['message_type'],
                'expected': gt['message_type'],
                'reason': pred.get('reason', '')
            })
            
        # 3. Evidence Jaccard Similarity
        def parse_evidence(e_str):
            if not e_str or str(e_str).lower() == 'none':
                return set()
            return {e.strip() for e in str(e_str).split(';') if e.strip()}
            
        pred_ev = parse_evidence(pred.get('evidence_message_ids'))
        gt_ev = parse_evidence(gt.get('evidence_message_ids'))
        
        if not pred_ev and not gt_ev:
            jaccard_sum += 1.0
        else:
            intersection = len(pred_ev.intersection(gt_ev))
            union = len(pred_ev.union(gt_ev))
            jaccard_sum += intersection / union if union > 0 else 0
            
    # Print Results
    print(f"\n--- Evaluation Results ({total} messages) ---")
    print(f"Action Accuracy: {action_correct / total * 100:.2f}%")
    print(f"Message Type Accuracy: {type_correct / total * 100:.2f}%")
    print(f"Evidence Jaccard Similarity: {jaccard_sum / total * 100:.2f}%")
    
    avg_corr_conf = (correct_conf_sum / correct_conf_count) if correct_conf_count else 0
    avg_incorr_conf = (incorrect_conf_sum / incorrect_conf_count) if incorrect_conf_count else 0
    print(f"Avg Confidence (Correct): {avg_corr_conf:.2f}")
    print(f"Avg Confidence (Incorrect): {avg_incorr_conf:.2f}")
    
    if mismatches:
        print("\n--- Mismatches ---")
        # Print up to 100 mismatches
        for m in mismatches[:100]:
            print(f"ID {m['id']} | {m['type']} | Pred: {m['pred']:<8} | Expected: {m['expected']:<8} | Reason: {m['reason']}")
