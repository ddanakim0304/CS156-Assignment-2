import json
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns

def load_fight_data(raw_data_dir: Path) -> list:
    """
    Loads all fight data from .jsonl files in the specified directory.

    Args:
        raw_data_dir: The path to the directory containing raw fight logs.

    Returns:
        A list of dictionaries, where each dictionary represents a single fight.
    """
    fight_sessions = []
    jsonl_files = list(raw_data_dir.glob("*.jsonl"))
    print(f"Found {len(jsonl_files)} fight log files.")

    for file_path in tqdm(jsonl_files, desc="Loading raw fight logs"):
        with open(file_path, 'r') as f:
            events, meta_info, summary_info = [], {}, {}
            for line in f:
                try:
                    data = json.loads(line)
                    if 'meta' in data:
                        meta_info = data['meta']
                    elif 'event' in data:
                        events.append(data)
                    elif 'summary' in data:
                        summary_info = data['summary']
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode line in {file_path}")

            if 'boss' in meta_info and events and 'duration_ms' in summary_info:
                fight_sessions.append({
                    'meta': meta_info,
                    'events': events,
                    'summary': summary_info
                })
    return fight_sessions

def _featurize_single_fight(fight_session: dict) -> dict:
    """Helper function to convert one fight's event stream into a feature dictionary."""
    meta = fight_session['meta']
    events = fight_session['events']
    summary = fight_session['summary']

    # --- Data Cleaning Step ---
    # Filter out fights that are too short to be meaningful
    duration_ms = summary.get('duration_ms', 0)
    if duration_ms < 10000:  # Fights shorter than 10 seconds are likely errors
        return None

    keydown_events = [e for e in events if e['event'] == 'keydown']
    total_keydowns = len(keydown_events)
    if total_keydowns < 2: # Need at least two keydowns for timing stats
        return None

    # --- Feature Engineering ---
    features = {'boss': meta['boss']}

    # 1. Activity Metrics
    duration_s = duration_ms / 1000.0
    features['duration_s'] = duration_s
    features['apm'] = (total_keydowns / duration_s) * 60

    # 2. Key Press Frequencies
    keys_to_track = ['Key.space', 'Key.up', 'Key.down', 'Key.left', 'Key.right', 'f', 'd', 'a', 'x']
    key_counts = {k: 0 for k in keys_to_track}
    for e in keydown_events:
        if e['key'] in key_counts:
            key_counts[e['key']] += 1

    for key, count in key_counts.items():
        clean_key_name = key.replace('.', '_')
        features[f'pct_{clean_key_name}'] = count / total_keydowns

    # 3. Rhythm & Timing Features
    timestamps = [e['t_ms'] for e in keydown_events]
    time_deltas = np.diff(timestamps)
    features['avg_time_between_presses'] = np.mean(time_deltas)
    features['std_time_between_presses'] = np.std(time_deltas)

    # 4. Behavioral Ratio Features
    # Add 1 to numerator and denominator to avoid division by zero
    features['vertical_to_horizontal_ratio'] = (key_counts['Key.up'] + key_counts['Key.down'] + 1) / (key_counts['Key.left'] + key_counts['Key.right'] + 1)
    features['duck_to_jump_ratio'] = (key_counts['Key.down'] + 1) / (key_counts['Key.space'] + 1)

    return features

def create_feature_dataframe(fight_sessions: list) -> pd.DataFrame:
    """
    Generates a full feature DataFrame from a list of loaded fight sessions.

    Args:
        fight_sessions: A list of fight data, from the load_fight_data function.

    Returns:
        A pandas DataFrame where each row is a featurized fight.
    """
    feature_list = [_featurize_single_fight(fight) for fight in tqdm(fight_sessions, desc="Featurizing fights")]
    
    # Filter out None results from the cleaning step
    clean_feature_list = [f for f in feature_list if f is not None]
    
    print(f"Successfully featurized {len(clean_feature_list)} of {len(fight_sessions)} fights after cleaning.")
    
    return pd.DataFrame(clean_feature_list)

def plot_eda_visualizations(df: pd.DataFrame):
    """
    Generates and displays key EDA plots to validate feature hypotheses.

    Args:
        df: The feature DataFrame.
    """
    print("\n--- Exploratory Data Analysis ---")
    
    # Set plot style
    sns.set_style("whitegrid")
    
    # 1. Class Distribution
    plt.figure(figsize=(10, 5))
    sns.countplot(y=df['boss'], order=df['boss'].value_counts().index, palette="viridis")
    plt.title('Number of Fights Recorded per Boss')
    plt.xlabel('Count')
    plt.ylabel('Boss')
    plt.show()

    # 2. APM Plot (Hypothesis for Baroness)
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='boss', y='apm', order=df['boss'].value_counts().index)
    plt.title('Hypothesis Check: Actions Per Minute (APM) by Boss')
    plt.ylabel('Actions Per Minute')
    plt.xlabel('')
    plt.xticks(rotation=10)
    plt.show()

    # 3. Rhythm Plot (Hypothesis for Baroness vs. Grim)
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='boss', y='std_time_between_presses', order=df['boss'].value_counts().index)
    plt.title('Hypothesis Check: Input Rhythm Consistency (Lower is more rhythmic)')
    plt.ylabel('Std. Dev. of Time Between Presses (ms)')
    plt.xlabel('')
    plt.xticks(rotation=10)
    plt.show()
    
    # 4. Ducking Plot (Hypothesis for Glumstone)
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='boss', y='pct_Key_down', order=df['boss'].value_counts().index)
    plt.title('Hypothesis Check: Percentage of Duck Actions by Boss')
    plt.ylabel('Duck Actions as % of Total')
    plt.xlabel('')
    plt.xticks(rotation=10)
    plt.show()

# This block allows you to run the script directly for testing
if __name__ == '__main__':
    import sys
    
    # Check for --new-dataset flag to use new dataset
    use_new_dataset = '--new-dataset' in sys.argv
    
    if use_new_dataset:
        data_path = Path("./data/raw_new")
        print("Using NEW dataset from: data/raw_new")
    else:
        data_path = Path("./data/raw")
        print("Using default dataset from: data/raw")
    
    # 1. Load the data
    all_fights_data = load_fight_data(data_path)
    
    # 2. Create the feature DataFrame
    feature_df = create_feature_dataframe(all_fights_data)
    
    # 3. Display descriptive statistics and plots
    if not feature_df.empty:
        print("\n--- DataFrame Head ---")
        print(feature_df.head())
        print("\n--- DataFrame Description ---")
        print(feature_df.describe())
        plot_eda_visualizations(feature_df)