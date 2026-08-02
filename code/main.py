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
from core.providers.anthropic import AnthropicProvider

def read_messages(dataset_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(dataset_dir, 'messages.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_output(dataset_dir: str, predictions: List[Dict[str, Any]]):
    path = os.path.join(dataset_dir, 'output.csv')
    fieldnames = ['message_id', 'action', 'message_type', 'reason', 'confidence', 'evidence_message_ids']
    with open(path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in predictions:
            # Output only the required schema
            row = {k: p.get(k, '') for k in fieldnames}
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', default=True)
    parser.add_argument('--no-resume', dest='resume', action='store_false')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(__file__)
    dataset_dir = os.path.abspath(os.path.join(base_dir, '..', 'dataset'))
    checkpoint_file = '.checkpoint_main.json'
    
    predictions = []
    if args.resume and os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
            
    processed_ids = {p['message_id'] for p in predictions}
    
    loader = DataLoader(dataset_dir)
    loader.load_all()
    
    provider = AnthropicProvider()
    
    messages = read_messages(dataset_dir)
    print(f"Total messages to process: {len(messages)}")
    
    for msg in messages:
        if args.resume and msg['message_id'] in processed_ids:
            continue
            
        print(f"Processing message {msg['message_id']}...")
        result = process_message(msg, provider, loader, dataset_dir)
        predictions.append(result)
        
        if args.resume:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, indent=2)
                
    write_output(dataset_dir, predictions)
    print(f"Processing complete. Wrote {len(predictions)} rows to dataset/output.csv.")

if __name__ == "__main__":
    main()
