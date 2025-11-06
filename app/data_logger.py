#!/usr/bin/env python3
"""
Cuphead Boss Keystroke Data Logger - Core Data Models
"""
import json
import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import yaml


@dataclass
class FightSession:
    """Represents a single fight session"""
    fight_id: str
    boss: str
    loadout: str
    difficulty: str
    start_utc: str
    start_time: float
    
    def __post_init__(self):
        """Generate fight_id if not provided"""
        if not self.fight_id:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
            # Add a simple suffix to ensure uniqueness
            suffix = str(int(time.time() * 1000) % 100000)
            self.fight_id = f"{timestamp}_{suffix}"


class DataLogger:
    """Handles all data logging operations"""
    
    def __init__(self, data_dir: Path = None, raw_subdir: str = "raw", csv_filename: str = "fight_summaries.csv"):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.raw_dir = self.data_dir / raw_subdir
        self.summaries_dir = self.data_dir / "summaries"
        self.meta_dir = self.data_dir / "meta"
        self.csv_filename = csv_filename
        
        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[FightSession] = None
        self.current_file: Optional[Any] = None
        self.event_count = 0
        
        # Load config
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        config_path = self.meta_dir / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Default config
            return {
                'difficulty': 'Regular',
                'loadout': 'Peashooter + Smoke Bomb',
                'bosses': ['Cagney Carnation', 'Baroness Von Bon Bon', 'Grim Matchstick', 'Glumstone the Giant'],
                'qa': {'min_duration_s': 10, 'min_events': 30}
            }
    
    def start_fight(self, boss: str, loadout: str = None, difficulty: str = None) -> str:
        """Start a new fight session"""
        if self.current_session:
            raise ValueError("Fight already in progress. End current fight first.")
        
        loadout = loadout or self.config.get('loadout', 'Peashooter + Smoke Bomb')
        difficulty = difficulty or self.config.get('difficulty', 'Regular')
        
        now = datetime.now(timezone.utc)
        self.current_session = FightSession(
            fight_id="",  # Will be auto-generated
            boss=boss,
            loadout=loadout,
            difficulty=difficulty,
            start_utc=now.isoformat(),
            start_time=time.perf_counter()
        )
        
        # Open JSONL file for writing
        file_path = self.raw_dir / f"{self.current_session.fight_id}.jsonl"
        self.current_file = open(file_path, 'w')
        
        # Write metadata line
        meta_line = {
            "fight_id": self.current_session.fight_id,
            "meta": {
                "boss": boss,
                "loadout": loadout,
                "difficulty": difficulty,
                "start_utc": self.current_session.start_utc
            }
        }
        self.current_file.write(json.dumps(meta_line) + '\n')
        self.current_file.flush()
        
        self.event_count = 0
        return self.current_session.fight_id
    
    def log_event(self, event_type: str, key: str):
        """Log a keyboard event"""
        if not self.current_session or not self.current_file:
            return
        
        t_ms = int((time.perf_counter() - self.current_session.start_time) * 1000)
        
        event_line = {
            "fight_id": self.current_session.fight_id,
            "event": event_type,
            "key": key,
            "t_ms": t_ms
        }
        
        self.current_file.write(json.dumps(event_line) + '\n')
        self.current_file.flush()  # Immediate write for safety
        self.event_count += 1
    
    def end_fight(self, outcome: str) -> Dict[str, Any]:
        """End the current fight and write summary"""
        if not self.current_session or not self.current_file:
            raise ValueError("No fight in progress")
        
        end_time = time.perf_counter()
        duration_ms = int((end_time - self.current_session.start_time) * 1000)
        end_utc = datetime.now(timezone.utc).isoformat()
        
        # Write summary line to JSONL
        summary_line = {
            "fight_id": self.current_session.fight_id,
            "summary": {
                "outcome": outcome,
                "duration_ms": duration_ms,
                "end_utc": end_utc
            }
        }
        self.current_file.write(json.dumps(summary_line) + '\n')
        self.current_file.flush()
        self.current_file.close()
        
        # Write to CSV summary
        self._write_csv_summary(outcome, duration_ms, end_utc)
        
        # Save session data for return
        session_data = {
            'fight_id': self.current_session.fight_id,
            'boss': self.current_session.boss,
            'outcome': outcome,
            'duration_s': duration_ms / 1000,
            'n_events': self.event_count
        }
        
        # Reset state
        self.current_session = None
        self.current_file = None
        self.event_count = 0
        
        return session_data
    
    def _write_csv_summary(self, outcome: str, duration_ms: int, end_utc: str):
        """Write fight summary to CSV"""
        csv_path = self.summaries_dir / self.csv_filename
        
        # Check if file exists and has header
        write_header = not csv_path.exists()
        
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if write_header:
                writer.writerow([
                    'fight_id', 'boss', 'loadout', 'difficulty', 
                    'outcome', 'duration_s', 'n_events', 'recorded_utc'
                ])
                f.flush()  # Ensure header is written
            
            writer.writerow([
                self.current_session.fight_id,
                self.current_session.boss,
                self.current_session.loadout,
                self.current_session.difficulty,
                outcome,
                duration_ms / 1000,
                self.event_count,
                end_utc
            ])
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        if not self.current_session:
            return None
        
        elapsed_ms = int((time.perf_counter() - self.current_session.start_time) * 1000)
        return {
            'fight_id': self.current_session.fight_id,
            'boss': self.current_session.boss,
            'elapsed_ms': elapsed_ms,
            'event_count': self.event_count
        }