#!/usr/bin/env python3
"""
Data analysis utility for Cuphead fight logs
"""
import sys
import os
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter

def analyze_fight_summaries(data_dir):
    """Analyze the fight summaries CSV"""
    csv_file = Path(data_dir) / "summaries" / "fight_summaries.csv"
    
    if not csv_file.exists():
        print("No fight summaries found.")
        return
    
    print("📊 Fight Summary Analysis")
    print("=" * 40)
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        fights = list(reader)
    
    if not fights:
        print("No fight data found.")
        return
    
    print(f"Total fights: {len(fights)}")
    
    # Analyze by boss
    boss_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_time': 0, 'total_events': 0})
    
    for fight in fights:
        boss = fight['boss']
        outcome = fight['outcome']
        duration = float(fight['duration_s'])
        events = int(fight['n_events'])
        
        boss_stats[boss]['total_time'] += duration
        boss_stats[boss]['total_events'] += events
        
        if outcome == 'win':
            boss_stats[boss]['wins'] += 1
        elif outcome == 'lose':
            boss_stats[boss]['losses'] += 1
    
    print("\n🎯 Boss Statistics:")
    for boss, stats in boss_stats.items():
        total_fights = stats['wins'] + stats['losses']
        if total_fights > 0:
            win_rate = stats['wins'] / total_fights * 100
            avg_duration = stats['total_time'] / total_fights
            avg_events = stats['total_events'] / total_fights
            
            print(f"\n{boss}:")
            print(f"  Fights: {total_fights} (W:{stats['wins']} L:{stats['losses']})")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Avg Duration: {avg_duration:.1f}s")
            print(f"  Avg Events: {avg_events:.0f}")
    
    # Overall stats
    total_duration = sum(float(f['duration_s']) for f in fights)
    total_events = sum(int(f['n_events']) for f in fights)
    total_wins = sum(1 for f in fights if f['outcome'] == 'win')
    
    print(f"\n📈 Overall Statistics:")
    print(f"  Total playtime: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    print(f"  Total keystrokes: {total_events}")
    print(f"  Overall win rate: {total_wins/len(fights)*100:.1f}%")
    print(f"  Avg keystrokes per second: {total_events/total_duration:.1f}")

def analyze_event_logs(data_dir, fight_id=None):
    """Analyze individual event logs"""
    raw_dir = Path(data_dir) / "raw"
    
    if not raw_dir.exists():
        print("No raw event logs found.")
        return
    
    jsonl_files = list(raw_dir.glob("*.jsonl"))
    
    if not jsonl_files:
        print("No JSONL files found.")
        return
    
    if fight_id:
        # Analyze specific fight
        target_file = raw_dir / f"{fight_id}.jsonl"
        if target_file.exists():
            jsonl_files = [target_file]
        else:
            print(f"Fight {fight_id} not found.")
            return
    
    print(f"\n⌨️  Event Log Analysis")
    print("=" * 40)
    
    all_keys = Counter()
    all_events = Counter()
    
    for jsonl_file in jsonl_files:
        print(f"\nAnalyzing: {jsonl_file.name}")
        
        with open(jsonl_file, 'r') as f:
            lines = f.readlines()
        
        meta = None
        events = []
        summary = None
        
        for line in lines:
            data = json.loads(line.strip())
            if 'meta' in data:
                meta = data['meta']
            elif 'event' in data:
                events.append(data)
            elif 'summary' in data:
                summary = data['summary']
        
        if meta:
            print(f"  Boss: {meta['boss']}")
            print(f"  Loadout: {meta['loadout']}")
        
        if summary:
            print(f"  Outcome: {summary['outcome']}")
            print(f"  Duration: {summary['duration_ms']/1000:.1f}s")
        
        # Analyze event patterns
        key_counts = Counter()
        event_counts = Counter()
        
        for event in events:
            key = event['key']
            event_type = event['event']
            
            key_counts[key] += 1
            event_counts[event_type] += 1
            all_keys[key] += 1
            all_events[event_type] += 1
        
        print(f"  Events: {len(events)}")
        
        if len(events) > 0:
            print(f"  Top keys: {', '.join([f'{k}({v})' for k, v in key_counts.most_common(3)])}")
    
    # Summary across all files
    if len(jsonl_files) > 1:
        print(f"\n🔍 Aggregate Analysis ({len(jsonl_files)} fights):")
        print(f"  Most used keys: {', '.join([f'{k}({v})' for k, v in all_keys.most_common(5)])}")
        print(f"  Event types: {dict(all_events)}")

def main():
    """Main analysis function"""
    data_dir = Path(__file__).parent / "data"
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "events":
            fight_id = sys.argv[2] if len(sys.argv) > 2 else None
            analyze_event_logs(data_dir, fight_id)
        elif sys.argv[1] == "summary":
            analyze_fight_summaries(data_dir)
        else:
            print("Usage: python analyze_data.py [summary|events] [fight_id]")
    else:
        # Run both analyses
        analyze_fight_summaries(data_dir)
        analyze_event_logs(data_dir)

if __name__ == "__main__":
    main()