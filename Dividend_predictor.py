# =============================================================================
# DIVIDEND ANNOUNCEMENT PREDICTOR
# =============================================================================

HELP_TEXT = """
Dividend Announcement Predictor Tool - Advanced Help
===================================================

DESCRIPTION:
    This script predicts upcoming dividend announcements based on historical 
    patterns from Israeli stock market data. It analyzes dividend timing patterns 
    for each company and predicts when they are likely to announce new dividends.

PURPOSE:
    - Identify companies likely to announce dividends soon based on historical patterns
    - Exclude companies that have already announced dividends recently
    - Provide confidence scores based on pattern frequency and recency
    - Help investors anticipate dividend opportunities before official announcements

ANALYSIS METHOD:
    1. Reads historical dividend data from CSV files
    2. Analyzes each company's historical ex-dividend date patterns
    3. Identifies recurring month/day patterns (e.g., always announces in March)
    4. Excludes companies with recent announcements (within 60 days by default)
    5. Predicts future announcement dates within specified timeframe
    6. Calculates confidence scores based on pattern consistency and recency

USAGE:
    python Dividend_predictor.py [OPTIONS]

OPTIONS:
    --csv FILE              Specify input CSV file path (auto-detects if not provided)
    --days N                Number of days ahead to predict (default: 30)
    --min-frequency N       Minimum historical occurrences for prediction (default: 2)
    --list                  List available CSV files in current directory
    
OUTPUT:
    Creates a single CSV file with timestamp: predicted_dividends_YYYY_MM_DD_HHMM.csv
    Contains predictions with company names, predicted dates, confidence scores, etc.

PREDICTION CRITERIA:
    - Company must have at least 2 historical dividend records (configurable)
    - Company must NOT have announced dividends in last 60 days
    - Pattern must repeat at least twice on same month/day combination
    - Prediction date must fall within specified future timeframe

CONFIDENCE SCORING:
    - Based on pattern frequency (more frequent = higher confidence)
    - Penalized for time since last occurrence (recent = higher confidence)
    - Scale: 0-100% confidence level

EXPECTED INPUT FORMAT:
    CSV file with Hebrew column headers:
    חברה, יום אקס דיבידנד, דיבידנד, סוג, תאריך תשלום, תשואה, Comfortable Date X

OUTPUT COLUMNS:
    - חברה: Company name
    - predicted_ex_date: Predicted ex-dividend date
    - days_until: Days until predicted date
    - frequency: How many times this pattern occurred
    - last_occurrence: Year of last occurrence
    - avg_dividend: Average historical dividend amount
    - confidence: Confidence percentage (0-100%)
    - pattern_years: Years when this pattern occurred

EXAMPLES:
    # Basic usage - predict next 30 days
    python Dividend_predictor.py

    # Predict next 60 days with minimum 3 occurrences
    python Dividend_predictor.py --days 60 --min-frequency 3

    # Use specific CSV file
    python Dividend_predictor.py --csv "my_dividend_data.csv"

    # List available files
    python Dividend_predictor.py --list

TECHNICAL NOTES:
    - Uses UTF-8 encoding for Hebrew text support
    - Automatically finds most recent Historical_Dividend*.csv file
    - Handles leap year date validation
    - Sorts results by days until prediction and confidence score
"""

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Prediction parameters
DEFAULT_PREDICTION_DAYS = 30  # How many days ahead to predict
MIN_HISTORICAL_DIVIDENDS = 2  # Minimum number of historical dividends to make prediction
RECENT_ANNOUNCEMENT_WINDOW = 60  # Days to check for recent announcements (exclude companies)
TOLERANCE_DAYS = 7  # Days tolerance for pattern matching

# Output settings
DEFAULT_OUTPUT_ENCODING = 'utf-8-sig'  # Encoding for CSV output files
CONSOLE_ENCODING = 'utf-8'  # Console output encoding

# Date format
DATE_FORMAT = '%d.%m.%Y'

# =============================================================================

import pandas as pd
import argparse
import glob
import os
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

def find_latest_csv_file():
    """Find the most recent CSV file containing dividend data."""
    csv_files = glob.glob("*Historical_Dividend*.csv")
    if not csv_files:
        csv_files = glob.glob("*.csv")
    
    if not csv_files:
        return None
    
    return max(csv_files, key=os.path.getmtime)

def analyze_dividend_patterns(df, min_frequency):
    """Analyze historical dividend patterns to predict upcoming announcements with custom frequency."""
    print("Analyzing historical dividend patterns...")
    
    # Group by company
    company_patterns = {}
    today = datetime.now().date()
    recent_cutoff = today - timedelta(days=RECENT_ANNOUNCEMENT_WINDOW)
    
    for company in df['חברה'].unique():
        company_data = df[df['חברה'] == company].copy()
        
        # Debug: Print all companies processed
        if company in ['לאומי (LUMI)', 'בינלאומי (FIBI)']:
            print(f"DEBUG: Processing {company}")
            print(f"  Company data count: {len(company_data)}")
            print(f"  Min frequency required: {min_frequency}")
        
        # Skip if not enough historical data
        if len(company_data) < min_frequency:
            if company in ['לאומי (LUMI)', 'בינלאומי (FIBI)']:
                print(f"  -> SKIPPING {company} - not enough data ({len(company_data)} < {min_frequency})")
            continue
            
        # Check if company has announced recently (skip if yes)
        recent_announcements = company_data[
            company_data['יום אקס דיבידנד'].dt.date >= recent_cutoff        ]
        
        # Debug: Print for Leumi specifically
        if company == 'לאומי (LUMI)':
            print(f"DEBUG: {company}")
            print(f"  Recent cutoff: {recent_cutoff}")
            print(f"  Company data dates: {company_data['יום אקס דיבידנד'].dt.date.tolist()}")
            print(f"  Recent announcements count: {len(recent_announcements)}")
            if not recent_announcements.empty:
                print(f"  Most recent announcement: {recent_announcements['יום אקס דיבידנד'].dt.date.max()}")
        
        if not recent_announcements.empty:
            if company == 'לאומי (LUMI)':
                print(f"  -> SKIPPING {company} due to recent announcement")
            continue  # Skip companies with recent announcements
        
        # Sort by ex-dividend date
        company_data = company_data.sort_values('יום אקס דיבידנד')
        
        # Calculate patterns
        patterns = analyze_company_pattern_with_freq(company_data, company, min_frequency)
        if patterns:
            company_patterns[company] = patterns
    
    return company_patterns

def analyze_company_pattern_with_freq(company_data, company_name, min_frequency):
    """Analyze dividend pattern for a specific company with custom frequency."""
    # Extract month/day patterns from historical data
    historical_dates = []
    
    for _, row in company_data.iterrows():
        ex_date = row['יום אקס דיבידנד']
        if pd.notna(ex_date):
            historical_dates.append(ex_date.date())
    
    if len(historical_dates) < min_frequency:
        return None
    
    # Sort dates
    historical_dates.sort()
    
    # Find common patterns (month/day combinations)
    month_day_patterns = defaultdict(list)
    
    for date in historical_dates:
        month_day = (date.month, date.day)
        month_day_patterns[month_day].append(date.year)
    
    # Find most frequent patterns
    frequent_patterns = []
    for (month, day), years in month_day_patterns.items():
        if len(years) >= 2:  # Pattern appears at least twice
            avg_dividend = company_data[
                (company_data['יום אקס דיבידנד'].dt.month == month) &
                (company_data['יום אקס דיבידנד'].dt.day == day)
            ]['דיבידנד'].mean()
            
            last_year = max(years)
            frequency = len(years)
            
            frequent_patterns.append({
                'month': month,
                'day': day,
                'frequency': frequency,
                'last_year': last_year,
                'avg_dividend': avg_dividend,
                'years': years
            })
    
    return frequent_patterns if frequent_patterns else None

def predict_upcoming_announcements(company_patterns, prediction_days=DEFAULT_PREDICTION_DAYS):
    """Predict upcoming dividend announcements based on historical patterns."""
    today = datetime.now().date()
    end_date = today + timedelta(days=prediction_days)
    
    predictions = []
    
    for company, patterns in company_patterns.items():
        for pattern in patterns:
            # Try current year and next year
            for year in [today.year, today.year + 1]:
                try:
                    predicted_date = datetime(year, pattern['month'], pattern['day']).date()
                    
                    # Check if prediction falls within our window
                    if today <= predicted_date <= end_date:
                        # Calculate days until prediction
                        days_until = (predicted_date - today).days
                        
                        # Calculate confidence based on frequency and recency
                        confidence = calculate_confidence(pattern, year)
                        
                        predictions.append({
                            'חברה': company,
                            'predicted_ex_date': predicted_date,
                            'days_until': days_until,
                            'frequency': pattern['frequency'],
                            'last_occurrence': pattern['last_year'],
                            'avg_dividend': pattern['avg_dividend'],
                            'confidence': confidence,
                            'pattern_years': ', '.join(map(str, pattern['years']))
                        })
                        
                except ValueError:
                    # Invalid date (e.g., Feb 29 in non-leap year)
                    continue
    
    # Sort by days until and confidence
    predictions.sort(key=lambda x: (x['days_until'], -x['confidence']))
    
    return predictions

def calculate_confidence(pattern, predicted_year):
    """Calculate confidence score for a prediction."""
    # Base confidence on frequency
    frequency_score = min(pattern['frequency'] / 5.0, 1.0)  # Max at 5 occurrences
    
    # Penalty for time since last occurrence
    years_since_last = predicted_year - pattern['last_year']
    recency_score = max(0, 1.0 - (years_since_last - 1) * 0.2)  # Penalty after first year
    
    # Combined confidence
    confidence = (frequency_score * 0.7 + recency_score * 0.3) * 100
    
    return round(confidence, 1)

def save_predictions_to_csv(predictions, output_file):
    """Save predictions to CSV with proper UTF-8 encoding."""
    if not predictions:
        print("No predictions to save.")
        return
        
    df = pd.DataFrame(predictions)
    df['predicted_ex_date'] = df['predicted_ex_date'].apply(lambda x: x.strftime(DATE_FORMAT))
    
    df.to_csv(output_file, index=False, encoding=DEFAULT_OUTPUT_ENCODING)
    print(f"Predicted announcements saved to: {output_file}")

def show_help():
    """Display comprehensive help information."""
    print(HELP_TEXT)

def print_predictions(predictions, prediction_days):
    """Print predictions to console with proper encoding."""
    print(f"\n=== PREDICTED DIVIDEND ANNOUNCEMENTS (Next {prediction_days} days) ===")
    print(f"Based on historical patterns, excluding companies with recent announcements")
    print("=" * 80)
    
    if not predictions:
        print("No dividend announcements predicted based on historical patterns.")
        return
    
    print(f"\n📈 LIKELY UPCOMING ANNOUNCEMENTS ({len(predictions)} companies):")
    print("=" * 80)
    
    for i, pred in enumerate(predictions, 1):
        predicted_date = pred['predicted_ex_date'].strftime(DATE_FORMAT)
        
        print(f"{i}. 🏢 {pred['חברה']}")
        print(f"   📅 Predicted Ex-Date: {predicted_date} ({pred['days_until']} days)")
        print(f"   💰 Avg Historical Dividend: {pred['avg_dividend']:.4f}")
        print(f"   📊 Pattern Frequency: {pred['frequency']} times")
        print(f"   🎯 Confidence: {pred['confidence']}%")
        print(f"   📈 Last Occurrence: {pred['last_occurrence']}")
        print(f"   📋 Pattern Years: {pred['pattern_years']}")
        print()

def main():
    parser = argparse.ArgumentParser(
        description='Predict upcoming dividend announcements based on historical patterns.'
    )
    parser.add_argument('--csv', help='Input CSV file path')
    parser.add_argument('--days', type=int, default=DEFAULT_PREDICTION_DAYS, 
                       help=f'Number of days ahead to predict (default: {DEFAULT_PREDICTION_DAYS})')
    parser.add_argument('--list', action='store_true', help='List available CSV files')
    parser.add_argument('--min-frequency', type=int, default=MIN_HISTORICAL_DIVIDENDS,
                       help=f'Minimum historical occurrences for prediction (default: {MIN_HISTORICAL_DIVIDENDS})')
    parser.add_argument('--info', action='store_true', help='Show detailed help information')
    
    args = parser.parse_args()
    
    if args.info:
        show_help()
        return
    
    if args.list:
        print("Available CSV files:")
        for f in sorted(glob.glob("*.csv")):
            print(f"  - {f}")
        return
    
    # Use the min_frequency from args instead of modifying global
    min_frequency = args.min_frequency
    
    # Find input file
    csv_file = args.csv or find_latest_csv_file()
    
    if not csv_file:
        print("Error: No CSV file found")
        print("Available CSV files:", glob.glob("*.csv"))
        return
    
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} not found")
        return
    
    try:
        print(f"Reading data from: {csv_file}")
        
        # Read CSV with proper encoding for Hebrew
        try:
            df = pd.read_csv(csv_file, encoding=DEFAULT_OUTPUT_ENCODING)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, encoding='utf-8')
        
        # Skip empty first row if present
        if df.iloc[0].isna().all():
            df = df.iloc[1:].reset_index(drop=True)        # Convert date columns
        df['יום אקס דיבידנד'] = pd.to_datetime(df['יום אקס דיבידנד'], format=DATE_FORMAT, errors='coerce')
        df['תאריך תשלום'] = pd.to_datetime(df['תאריך תשלום'], format=DATE_FORMAT, errors='coerce')
          # Normalize company names (replace non-breaking spaces with regular spaces)
        df['חברה'] = df['חברה'].str.replace('\xa0', ' ', regex=False)
        
        # Analyze patterns with custom min_frequency
        company_patterns = analyze_dividend_patterns(df, min_frequency)
        
        if not company_patterns:
            print("No reliable dividend patterns found for prediction.")
            return
            
        print(f"Found patterns for {len(company_patterns)} companies")
        
        # Generate predictions
        predictions = predict_upcoming_announcements(company_patterns, args.days)
        
        # Print results to console
        print_predictions(predictions, args.days)
        
        # Always save to CSV with timestamp format
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")
        output_file = f"predicted_dividends_{timestamp}.csv"
        save_predictions_to_csv(predictions, output_file)
            
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()