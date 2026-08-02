import sys
import os
import argparse
import json
import csv
from typing import List, Dict, Any

# Ensure core modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.pipeline import process_message
from evaluation.metrics import score_predictions

def read_sample_messages(dataset_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(dataset_dir, 'sample_messages.csv')
    if not os.path.exists(path):
        return []
    with open(path, mode='r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', default='anthropic')
    parser.add_argument('--resume', action='store_true', default=True)
    parser.add_argument('--no-resume', dest='resume', action='store_false')
    args = parser.parse_args()
    
    dataset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dataset'))
    checkpoint_file = '.checkpoint_eval.json'
    
    # Provider Initialization
    if args.provider == 'anthropic':
        from core.providers.anthropic import AnthropicProvider
        provider = AnthropicProvider()
    else:
        raise ValueError(f"Unknown provider {args.provider}")
        
    predictions = []
    if args.resume and os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
            
    processed_ids = {p['message_id'] for p in predictions}
    
    loader = DataLoader(dataset_dir)
    loader.load_all()
    
    sample_msgs = read_sample_messages(dataset_dir)
    print(f"Loaded {len(sample_msgs)} sample messages for evaluation.")
    
    for idx, msg in enumerate(sample_msgs):
        if args.resume and msg['message_id'] in processed_ids:
            continue
            
        print(f"Evaluating {msg['message_id']} ({idx+1}/{len(sample_msgs)})...")
        result = process_message(msg, provider, loader, dataset_dir)
        predictions.append(result)
        
        if args.resume:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, indent=2)
                
    # Evaluate
    score_predictions(predictions, sample_msgs)

if __name__ == "__main__":
    main()
