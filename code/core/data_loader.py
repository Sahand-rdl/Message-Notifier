import csv
from typing import Dict, List, Any, Tuple, Optional
import os

class DataLoader:
    """
    Loads all CSV files from the dataset into memory for fast O(1) lookups.
    Handles indexing of users, groups, business history, and message history.
    """
    
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir
        
        # In-memory indexes
        self.users: Dict[str, Dict[str, Any]] = {}
        self.groups: Dict[str, Dict[str, Any]] = {}
        self.group_members: Dict[Tuple[str, str], Dict[str, Any]] = {}  # Indexed by (user_id, group_id)
        self.business_accounts: Dict[str, Dict[str, Any]] = {}
        self.user_business_history: Dict[str, List[Dict[str, Any]]] = {}  # Indexed by user_id
        self.message_history: Dict[str, Dict[str, Any]] = {}
        self.user_message_history: Dict[str, List[Dict[str, Any]]] = {}
        self.message_events: Dict[Tuple[str, str], Dict[str, Any]] = {} # Indexed by (user_id, message_id)
        
        # Media maps
        self.images: Dict[str, str] = {}
        self.voice_notes: Dict[str, str] = {}
        
        self.daily_notification_summary: Dict[str, Dict[str, Any]] = {}

    def _read_csv(self, filename: str) -> List[Dict[str, str]]:
        filepath = os.path.join(self.dataset_dir, filename)
        if not os.path.exists(filepath):
            return []
        
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [row for row in reader]

    def load_all(self):
        """Loads and indexes all required CSVs."""
        # Load Users
        for row in self._read_csv('users.csv'):
            self.users[row['user_id']] = row
            
        # Load Groups
        for row in self._read_csv('groups.csv'):
            self.groups[row['group_id']] = row
            
        # Load Group Members (index by user and group tuple)
        for row in self._read_csv('group_members.csv'):
            self.group_members[(row['user_id'], row['group_id'])] = row
            
        # Load Business Accounts
        for row in self._read_csv('business_accounts.csv'):
            self.business_accounts[row['business_id']] = row
            
        # Load User Business History
        for row in self._read_csv('user_business_history.csv'):
            uid = row['user_id']
            if uid not in self.user_business_history:
                self.user_business_history[uid] = []
            self.user_business_history[uid].append(row)
            
        # Load Message History
        for row in self._read_csv('message_history.csv'):
            self.message_history[row['message_id']] = row
            uid = row['user_id']
            if uid not in self.user_message_history:
                self.user_message_history[uid] = []
            self.user_message_history[uid].append(row)
            
        # Load Message Events
        for row in self._read_csv('message_events.csv'):
            self.message_events[(row['user_id'], row['message_id'])] = row
            
        # Load Images
        for row in self._read_csv('images.csv'):
            self.images[row['image_id']] = row['file_path']
            
        # Load Voice Notes
        for row in self._read_csv('voice_notes.csv'):
            self.voice_notes[row['voice_note_id']] = row['file_path']
            
        # Load Daily Notification Summary
        for row in self._read_csv('daily_notification_summary.csv'):
            self.daily_notification_summary[row['user_id']] = row

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.get(user_id)

    # ... additional fast lookup methods will be added here ...
