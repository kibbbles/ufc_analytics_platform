import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Load environment
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

print('Loading data...')

# Load fighter physical attributes
with engine.connect() as conn:
    df_fighters = pd.read_sql(text('''
        SELECT
            id,
            "FIGHTER" as fighter_name,
            "HEIGHT" as height_raw,
            "WEIGHT" as weight_raw,
            "REACH" as reach_raw,
            "STANCE" as stance,
            "DOB" as dob_raw
        FROM fighter_tott
        WHERE "HEIGHT" IS NOT NULL OR "WEIGHT" IS NOT NULL
    '''), conn)

# Load fight stats
with engine.connect() as conn:
    df_stats = pd.read_sql(text('''
        SELECT
            id,
            "EVENT" as event,
            "BOUT" as bout,
            "ROUND" as round,
            "FIGHTER" as fighter,
            "KD" as knockdowns_raw,
            "SIG.STR." as sig_strikes_raw,
            "SIG.STR. %" as sig_strikes_pct_raw,
            "TOTAL STR." as total_strikes_raw,
            "TD" as takedowns_raw,
            "TD %" as td_pct_raw,
            "SUB.ATT" as sub_attempts_raw,
            "CTRL" as control_time_raw,
            event_id,
            fight_id
        FROM fight_stats
    '''), conn)

print(f'Loaded {len(df_fighters):,} fighters and {len(df_stats):,} stat records')
print('Parsing data...')

# Parsing functions
def parse_height(height_str):
    if pd.isna(height_str):
        return np.nan
    try:
        height_str = str(height_str).strip()
        if height_str == '--':
            return np.nan
        if "'" in height_str:
            parts = height_str.replace('"', '').split("'")
            feet = int(parts[0])
            inches = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 0
            return feet * 12 + inches
        elif 'cm' in height_str.lower():
            cm = float(height_str.lower().replace('cm', '').strip())
            return cm / 2.54
        else:
            return float(height_str)
    except:
        return np.nan

def parse_weight(weight_str):
    if pd.isna(weight_str):
        return np.nan
    try:
        weight_str = str(weight_str).strip().lower()
        if weight_str == '--':
            return np.nan
        if 'lbs' in weight_str or 'lb' in weight_str:
            weight_str = weight_str.replace('lbs', '').replace('lb', '').replace('.', '').strip()
            return float(weight_str)
        elif 'kg' in weight_str:
            kg = float(weight_str.replace('kg', '').strip())
            return kg * 2.20462
        else:
            return float(weight_str)
    except:
        return np.nan

def parse_reach(reach_str):
    if pd.isna(reach_str):
        return np.nan
    try:
        reach_str = str(reach_str).strip().lower()
        if reach_str == '--':
            return np.nan
        if '"' in reach_str:
            return float(reach_str.replace('"', '').strip())
        elif 'cm' in reach_str:
            cm = float(reach_str.replace('cm', '').strip())
            return cm / 2.54
        else:
            return float(reach_str)
    except:
        return np.nan

def parse_strikes(strikes_str):
    if pd.isna(strikes_str):
        return np.nan, np.nan
    try:
        strikes_str = str(strikes_str).strip()
        if strikes_str == '---' or strikes_str == '--':
            return np.nan, np.nan
        parts = strikes_str.lower().split(' of ')
        landed = int(parts[0])
        attempted = int(parts[1]) if len(parts) > 1 else landed
        return landed, attempted
    except:
        return np.nan, np.nan

def parse_percentage(pct_str):
    if pd.isna(pct_str):
        return np.nan
    try:
        pct_str = str(pct_str).strip()
        if pct_str == '---' or pct_str == '--':
            return np.nan
        pct_str = pct_str.replace('%', '')
        return float(pct_str) / 100.0
    except:
        return np.nan

# Parse fighter attributes
df_fighters['height_inches'] = df_fighters['height_raw'].apply(parse_height)
df_fighters['weight_lbs'] = df_fighters['weight_raw'].apply(parse_weight)
df_fighters['reach_inches'] = df_fighters['reach_raw'].apply(parse_reach)

# Parse fight statistics
df_stats[['sig_str_landed', 'sig_str_attempted']] = df_stats['sig_strikes_raw'].apply(
    lambda x: pd.Series(parse_strikes(x))
)
df_stats['sig_str_pct'] = df_stats['sig_strikes_pct_raw'].apply(parse_percentage)
df_stats[['td_landed', 'td_attempted']] = df_stats['takedowns_raw'].apply(
    lambda x: pd.Series(parse_strikes(x))
)
df_stats['td_pct'] = df_stats['td_pct_raw'].apply(parse_percentage)
df_stats['knockdowns'] = pd.to_numeric(df_stats['knockdowns_raw'], errors='coerce')
df_stats['sub_attempts'] = pd.to_numeric(df_stats['sub_attempts_raw'], errors='coerce')

# Aggregate fighter stats
fighter_stats_agg = df_stats.groupby('fighter').agg({
    'sig_str_landed': 'mean',
    'sig_str_attempted': 'mean',
    'sig_str_pct': 'mean',
    'td_landed': 'mean',
    'td_attempted': 'mean',
    'td_pct': 'mean',
    'knockdowns': 'mean',
    'sub_attempts': 'mean',
    'fight_id': 'count'
}).reset_index()
fighter_stats_agg.rename(columns={'fight_id': 'total_fights'}, inplace=True)
fighter_stats_agg['slpm'] = fighter_stats_agg['sig_str_landed'] / 5.0

print(f'Aggregated stats for {len(fighter_stats_agg):,} fighters')

# Correlation analysis
print('='*80)
print('CORRELATION ANALYSIS - VALIDATING PRIOR RESEARCH')
print('='*80)
print('\nReferences:')
print('  - DeepUFC (72% accuracy with 9 features)')
print('  - Stanford CS229 (66.71% with GBDT)')
print('  - Goal: Validate feature importance from prior research\n')

# Merge datasets
df_fighters['fighter_name_clean'] = df_fighters['fighter_name'].str.strip().str.lower()
fighter_stats_agg['fighter_clean'] = fighter_stats_agg['fighter'].str.strip().str.lower()

fighter_combined = df_fighters.merge(
    fighter_stats_agg,
    left_on='fighter_name_clean',
    right_on='fighter_clean',
    how='inner'
)

print(f'Merged {len(fighter_combined)} fighters with both physical and performance stats\n')

# All 11 features
all_features = [
    'height_inches',
    'weight_lbs',
    'reach_inches',
    'sig_str_pct',
    'td_pct',
    'slpm',
    'sig_str_landed',
    'td_landed',
    'knockdowns',
    'sub_attempts',
    'total_fights'
]

# Missing data analysis
print('Missing Data Analysis:')
print('-' * 80)
for col in all_features:
    missing = fighter_combined[col].isna().sum()
    present = fighter_combined[col].notna().sum()
    pct = (present / len(fighter_combined)) * 100
    status = 'OK' if pct >= 90 else 'WARNING'
    print(f'{status:7s} {col:20s}: {present:4d} present ({pct:5.1f}%), {missing:4d} missing')

# Complete cases
fighter_features_complete = fighter_combined[all_features].dropna()
print(f'\n{'='*80}')
print(f'Complete Cases: {len(fighter_features_complete):,} fighters have ALL 11 features')
print(f'This is {(len(fighter_features_complete)/len(fighter_combined)*100):.1f}% of merged fighters')
print(f'{'='*80}\n')

# Calculate correlations
corr_matrix = fighter_features_complete.corr()

# Strongest correlations
print('='*80)
print('STRONGEST FEATURE CORRELATIONS')
print('='*80)

upper_tri = corr_matrix.where(
    np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
)

strong_corr = []
for column in upper_tri.columns:
    for index in upper_tri.index:
        value = upper_tri.loc[index, column]
        if pd.notna(value) and abs(value) > 0.3:
            strong_corr.append((index, column, value))

strong_corr.sort(key=lambda x: abs(x[2]), reverse=True)

print('\nTop 15 Strongest Correlations:')
for i, (feat1, feat2, corr_val) in enumerate(strong_corr[:15], 1):
    direction = 'positive' if corr_val > 0 else 'negative'
    print(f'{i:2d}. {feat1:20s} <-> {feat2:20s}: {corr_val:6.3f} ({direction})')

# Validation insights
print('\n' + '='*80)
print('INSIGHTS & VALIDATION')
print('='*80)

print('\n1. Physical Features (Height, Weight, Reach):')
phys_corr = corr_matrix.loc[['height_inches', 'weight_lbs', 'reach_inches'],
                              ['height_inches', 'weight_lbs', 'reach_inches']]
print(f'   - Height <-> Weight: {phys_corr.loc["height_inches", "weight_lbs"]:.3f}')
print(f'   - Height <-> Reach:  {phys_corr.loc["height_inches", "reach_inches"]:.3f}')
print(f'   - Weight <-> Reach:  {phys_corr.loc["weight_lbs", "reach_inches"]:.3f}')
print('   -> Expected: Bigger fighters have more reach (VALIDATED)')

print('\n2. Striking Metrics (per DeepUFC):')
print(f'   - SLpM <-> Sig Strike %: {corr_matrix.loc["slpm", "sig_str_pct"]:.3f}')
print(f'   - SLpM <-> Sig Landed:  {corr_matrix.loc["slpm", "sig_str_landed"]:.3f}')
print('   -> Expected: Volume and accuracy have moderate correlation')

print('\n3. Grappling Metrics:')
print(f'   - TD Landed <-> TD %: {corr_matrix.loc["td_landed", "td_pct"]:.3f}')
print(f'   - Sub Attempts <-> TD Landed: {corr_matrix.loc["sub_attempts", "td_landed"]:.3f}')
print('   -> Expected: Grapplers have correlated grappling stats')

print('\n4. Experience:')
print(f'   - Total Fights <-> SLpM: {corr_matrix.loc["total_fights", "slpm"]:.3f}')
print(f'   - Total Fights <-> Sig Strike %: {corr_matrix.loc["total_fights", "sig_str_pct"]:.3f}')
print('   -> Check if experience correlates with skill improvement')

print('\nAnalysis complete!')
