import pandas as pd
import re
import glob
import os
import argparse
import pandas as pd
import re
import glob
import os
import argparse
from datetime import datetime

# =============================================================================
# HELP DOCUMENTATION
# =============================================================================

HELP_TEXT = """
Dividend Updater Tool - Help
============================

DESCRIPTION:
    Updates dividend information from markdown (.md) files to CSV files.
    Automatically finds the most recent files or allows manual specification.

USAGE:
    python dividend_updater_2025_05_29.py [OPTIONS]

OPTIONS:
    --md FILE       Specify input markdown file path
    --csv FILE      Specify output CSV file path  
    --list          List all available MD and CSV files in current directory
    --info          Show detailed help information

AUTOMATIC FILE DETECTION:
    If no files are specified, the script will automatically find:
    - CSV file: Most recent file containing "Dividends" in the name
    - MD file: Most recent file containing "Update" in the name

EXPECTED FILE FORMATS:
    
    Markdown file format:
    ||**Company Name**([ACRONYM](link))|DD.MM.YYYY|amount|||DD.MM.YYYY|
    
    CSV file columns:
    חברה, יום אקס דיבידנד, דיבידנד, סוג, תאריך תשלום, תשואה, Comfortable Date X

FEATURES:
    - Duplicate detection and prevention
    - Date validation (payment date must be after ex-date)
    - Company name normalization for matching
    - Automatic sorting by ex-dividend date
    - Comprehensive error reporting

EXAMPLES:
    python dividend_updater_2025_05_29.py
        (Use automatic file detection)
    
    python dividend_updater_2025_05_29.py --list
        (List available files)
    
    python dividend_updater_2025_05_29.py --md "update_jan.md" --csv "dividends.csv"
        (Specify files manually)

OUTPUT:
    - Summary of entries processed
    - List of duplicates found and skipped
    - List of new entries added to CSV file
    - Updated CSV file with new dividend information
"""

# =============================================================================

def find_latest_file(pattern, search_word=None):
    """Find the most recently modified file matching the pattern and optionally containing a word."""
    files = glob.glob(pattern)
    if search_word:
        files = [f for f in files if search_word.lower() in f.lower()]
    
    if not files:
        return None
    
    return max(files, key=os.path.getmtime)

def normalize_company_name(name):
    """Normalize company name by removing spaces and common variations."""
    if not isinstance(name, str):
        return str(name)
    # Remove all whitespace and convert to string
    name = re.sub(r'\s+', '', name)
    # Remove parentheses and their contents (like acronyms)
    name = re.sub(r'\([^\)]+\)', '', name)
    return name.strip()

def parse_md_file(md_file_path):
    """Parse the markdown file and extract dividend information."""
    with open(md_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    print(f"\nProcessing file: {md_file_path}")
    
    entries = []
    content_lines = content.split('\n')
    seen_entries = set()  # Track unique entries by company, date, and amount
    
    for line in content_lines:
        line = line.strip()
        
        # Skip empty lines, header lines, and date headers
        if not line or 'חברה' in line or ('יום' in line and ('במאי' in line or 'ביוני' in line or 'באפריל' in line)):
            continue
              # Skip lines with dashes or other separators  
        if '--' in line or not line.startswith('|'):
            continue
        
        # Split by pipes and clean up
        parts = [part.strip() for part in line.split('|')]
        # Remove empty first and last elements (common in markdown tables)
        if len(parts) > 0 and parts[0] == '':
            parts = parts[1:]
        if len(parts) > 0 and parts[-1] == '':
            parts = parts[:-1]
        
        # We need at least 6 parts: empty, company, ex_date, dividend, type, payment_date, yield
        if len(parts) < 6:
            continue
              # Skip rows where the company column is empty (date header rows)
        if not parts[1].strip():
            continue
            
        try:
            # Extract company name (remove parentheses and acronym)
            company_full = parts[1].strip()  # Company is in column 1
            
            # Extract company name and acronym
            if '(' in company_full and ')' in company_full:
                company_match = re.match(r'^([^(]+)\s*\(([^)]+)\)', company_full)
                if company_match:
                    company_name = company_match.group(1).strip()
                    acronym = company_match.group(2).strip()
                    company_with_acronym = f"{company_name} ({acronym})"
                else:
                    company_with_acronym = company_full
            else:
                company_with_acronym = company_full
            
            ex_date = parts[2].strip()       # Ex-date is in column 2
            dividend_str = parts[3].strip()  # Dividend is in column 3
            payment_date = parts[5].strip()  # Payment date is in column 5
            yield_str = parts[6].strip() if len(parts) > 6 else ''  # Yield is in column 6
            
            # Skip entries with empty dividend or invalid dates
            if not dividend_str or not ex_date or not payment_date:
                continue
                
            # Convert dividend to float
            try:
                dividend = float(dividend_str)
            except ValueError:
                continue
                
            # Basic validation
            if dividend <= 0:
                print(f"Warning: Skipping {company_with_acronym} - invalid dividend amount: {dividend}")
                continue
                
            # Validate date format and payment after ex-date
            try:
                ex_date_dt = datetime.strptime(ex_date, '%d.%m.%Y')
                payment_date_dt = datetime.strptime(payment_date, '%d.%m.%Y')
                if payment_date_dt < ex_date_dt:
                    print(f"Warning: Skipping {company_with_acronym} - payment date {payment_date} is before ex-date {ex_date}")
                    continue
            except ValueError as e:
                print(f"Warning: Skipping {company_with_acronym} - invalid date format: {e}")
                continue
            
            # Check for duplicates within MD file
            entry_key = f"{company_with_acronym}_{ex_date}_{dividend}"
            if entry_key in seen_entries:
                print(f"Skipping duplicate in MD file: {company_with_acronym} on {ex_date}")
                continue
            seen_entries.add(entry_key)
            
            entries.append({
                'חברה': company_with_acronym,
                'יום אקס דיבידנד': ex_date,
                'דיבידנד': dividend,
                'סוג': '',  # Empty string for 'סוג' column
                'תאריך תשלום': payment_date,
                'תשואה': yield_str,  # Keep the yield as string
                'Comfortable Date X': ex_date_dt.strftime('%Y-%m-%d')
            })
            print(f"Successfully parsed entry: {company_with_acronym}")
            
        except Exception as e:
            print(f"Error processing line '{line}': {e}")
            continue
    
    print(f"Found {len(entries)} valid entries in file")
    return pd.DataFrame(entries), len(entries)

def is_duplicate_entry(row, df_csv):
    """Check if an entry is a duplicate using normalized company names."""
    try:
        company = row['חברה']
        ex_date = row['יום אקס דיבידנד']
        dividend = row['דיבידנד']
        
        # Extract company name without acronym
        company_match = re.match(r'^([^(]+)', company)
        if company_match:
            company = company_match.group(1).strip()
        
        # Normalize company names for comparison
        normalized_new = normalize_company_name(company)
        
        # Create temporary column with normalized names
        df_csv['normalized_name'] = df_csv['חברה'].apply(normalize_company_name)
        
        try:
            # Check for exact matches
            exact_matches = df_csv[
                (df_csv['normalized_name'] == normalized_new) &
                (df_csv['יום אקס דיבידנד'] == ex_date) &
                (abs(df_csv['דיבידנד'] - dividend) < 0.01)
            ]
            
            if not exact_matches.empty:
                return True, "exact match"
                
            # Check date matches
            date_matches = df_csv[df_csv['יום אקס דיבידנד'] == ex_date]
            for _, existing in date_matches.iterrows():
                if (abs(existing['דיבידנד'] - dividend) < 0.01 and 
                    normalize_company_name(existing['חברה']) == normalized_new):
                    return True, f"same amount and date (normalized name: {existing['חברה']})"
            
            return False, None
            
        finally:
            # Always clean up temporary column
            if 'normalized_name' in df_csv.columns:
                df_csv.drop('normalized_name', axis=1, inplace=True, errors='ignore')
                
    except Exception as e:
        print(f"Warning: Error in duplicate detection: {e}")
        return False, None

def update_csv_file(csv_file_path, md_file_path):
    """Update the CSV file with new dividend information from the MD file."""
    # Define the column names
    columns = ['חברה', 'יום אקס דיבידנד', 'דיבידנד', 'סוג', 'תאריך תשלום', 'תשואה', 'Comfortable Date X']
      # Read existing CSV file and handle empty first row
    try:
        df_csv = pd.read_csv(csv_file_path, encoding='utf-8-sig')
        print(f"CSV columns found: {list(df_csv.columns)}")
        # If the first row is empty, skip it
        if df_csv.iloc[0].isna().all():
            df_csv = df_csv.iloc[1:].reset_index(drop=True)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Parse new entries from MD file
    df_new, total_md_entries = parse_md_file(md_file_path)
    if df_new.empty:
        print("No valid entries found in the MD file.")
        return
    
    # Convert date columns to consistent format for comparison
    df_csv['יום אקס דיבידנד'] = pd.to_datetime(df_csv['יום אקס דיבידנד'], format='%d.%m.%Y', errors='coerce').dt.strftime('%d.%m.%Y')
    df_new['יום אקס דיבידנד'] = pd.to_datetime(df_new['יום אקס דיבידנד'], format='%d.%m.%Y').dt.strftime('%d.%m.%Y')
    
    # Check for duplicates in CSV file
    duplicates = []
    new_entries_list = []
    
    for _, new_row in df_new.iterrows():
        is_dup, reason = is_duplicate_entry(new_row, df_csv)
        if is_dup:
            duplicates.append((new_row, reason))
        else:
            new_entries_list.append(new_row)
    
    # Report duplicates with reasons
    if duplicates:
        print("\nSkipping entries already in CSV:")
        for row, reason in duplicates:
            print(f"- {row['חברה']} on {row['יום אקס דיבידנד']} ({row['דיבידנד']}): {reason}")
    
    # Convert new entries back to DataFrame
    new_entries = pd.DataFrame(new_entries_list) if new_entries_list else pd.DataFrame()
    
    # Print final summary regardless of new entries
    print("\nProcessing Summary:")
    md_duplicates = total_md_entries - len(df_new)  # Duplicates within MD
    csv_duplicates = len(duplicates)  # Entries found in CSV
    new_added = len(new_entries)  # Actually added entries
    
    print(f"- Total entries found in MD file: {total_md_entries}")
    if md_duplicates > 0:
        print(f"- Duplicates within MD file: {md_duplicates}")
    if csv_duplicates > 0:
        print(f"- Already exist in CSV: {csv_duplicates}")
    print(f"- New entries added: {new_added}")
    
    if len(new_entries) == 0:
        return
    
    # Sort by ex-dividend date
    df_updated = pd.concat([df_csv, new_entries], ignore_index=True)
    df_updated['sort_date'] = pd.to_datetime(df_updated['יום אקס דיבידנד'], format='%d.%m.%Y')
    df_updated = df_updated.sort_values('sort_date')
    df_updated = df_updated.drop('sort_date', axis=1)
    
    # Add empty row at the beginning to maintain file structure
    empty_row = pd.DataFrame([['' for _ in range(len(df_updated.columns))]], columns=df_updated.columns)
    df_updated = pd.concat([empty_row, df_updated], ignore_index=True)
    
    # Save updated DataFrame to CSV
    df_updated.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
    print("\nNew entries added to CSV:")
    for _, row in new_entries.iterrows():
        print(f"- {row['חברה']}: {row['יום אקס דיבידנד']}, {row['דיבידנד']}")

def list_available_files():
    """List all available MD and CSV files in the current directory."""
    print("\nAvailable files:")
    print("MD files:")
    for f in sorted(glob.glob("*.md")):
        print(f"  - {f}")
    print("\nCSV files:")
    for f in sorted(glob.glob("*.csv")):
        print(f"  - {f}")
    print()

def show_help():
    """Display comprehensive help information."""
    print(HELP_TEXT)

def main():
    parser = argparse.ArgumentParser(description='Update dividend information from MD file to CSV file.')
    parser.add_argument('--md', help='Input markdown file path')
    parser.add_argument('--csv', help='Output CSV file path')
    parser.add_argument('--list', action='store_true', help='List available files')
    parser.add_argument('--info', action='store_true', help='Show detailed help information')
    args = parser.parse_args()
    
    if args.info:
        show_help()
        return
    
    if args.list:
        list_available_files()
        return
      # Find the most recent files if not specified
    csv_file = args.csv or find_latest_file("*Historical_Dividend*.csv", None) or find_latest_file("*.csv", "Historical")
    md_file = args.md or find_latest_file("*Update*.md", None)  # Look for Update in the filename directly
    
    # If no update file found, try looking for any .md file with "update" in it
    if not md_file:
        md_file = find_latest_file("*.md", "update")
        
    list_available_files()  # Always show available files
    
    if not csv_file:
        print("Error: No CSV file found with 'Dividends' or 'Historical_Dividend' in the name")
        print("Available CSV files:", glob.glob("*.csv"))
        return
    if not md_file:
        print("Error: No markdown file found with 'Update' in the name")
        print("Available MD files:", glob.glob("*.md"))
        return
    
    print(f"Using CSV file: {csv_file}")
    print(f"Using MD file: {md_file}")
    
    update_csv_file(csv_file, md_file)

if __name__ == "__main__":
    main()