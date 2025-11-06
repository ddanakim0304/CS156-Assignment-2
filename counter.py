#!/usr/bin/env python3
"""
Script to count wins and losses for each boss from fight summaries data.
"""

import csv
from pathlib import Path
from collections import defaultdict

def count_win_loss_by_boss(csv_file_path):
    """Count wins and losses for each boss from the fight summaries CSV."""
    
    if not Path(csv_file_path).exists():
        print(f"Error: File {csv_file_path} not found.")
        return
    
    # Initialize counters
    boss_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total': 0})
    total_fights = 0
    
    try:
        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                boss = row['boss']
                outcome = row['outcome'].lower()
                
                boss_stats[boss]['total'] += 1
                
                if outcome == 'win':
                    boss_stats[boss]['wins'] += 1
                elif outcome == 'lose':
                    boss_stats[boss]['losses'] += 1
                
                total_fights += 1
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Display results
    print("🎯 Boss Fight Statistics")
    print("=" * 50)
    
    overall_wins = 0
    overall_losses = 0
    
    for boss, stats in sorted(boss_stats.items()):
        wins = stats['wins']
        losses = stats['losses']
        total_boss_fights = stats['total']
        win_rate = (wins / total_boss_fights * 100) if total_boss_fights > 0 else 0
        
        print(f"\n{boss}:")
        print(f"  Total Fights: {total_boss_fights}")
        print(f"  Wins: {wins}")
        print(f"  Losses: {losses}")
        print(f"  Win Rate: {win_rate:.1f}%")
        
        overall_wins += wins
        overall_losses += losses
    
    # Overall statistics
    print("\n" + "=" * 50)
    print("📊 Overall Statistics:")
    print(f"  Total Fights: {total_fights}")
    print(f"  Total Wins: {overall_wins}")
    print(f"  Total Losses: {overall_losses}")
    print(f"  Overall Win Rate: {(overall_wins / total_fights * 100):.1f}%")

def main():
    # Default path to the fight summaries CSV
    csv_path = "data/summaries/fight_summaries.csv"
    
    # Allow command line argument for custom path
    import sys
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    count_win_loss_by_boss(csv_path)

if __name__ == "__main__":
    main()