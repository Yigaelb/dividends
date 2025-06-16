import pandas as pd
import re

def fix_company_names_in_csv(csv_file_path):
    """Fix company names that have markdown formatting in the CSV file."""
    
    # Read the CSV file
    print(f"Reading CSV file: {csv_file_path}")
    df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
    
    # Check if first row is empty and skip it
    if df.iloc[0].isna().all():
        df = df.iloc[1:].reset_index(drop=True)
        had_empty_row = True
    else:
        had_empty_row = False
    
    print(f"Total rows to process: {len(df)}")
    
    # Track changes
    changes_made = 0
    
    # Process each company name
    for idx, row in df.iterrows():
        company_name = str(row['חברה'])
        
        # Check if this has markdown formatting
        # Pattern: **Company Name** ([ACRONYM](link)) or variations
        markdown_pattern = r'\*\*([^*]+)\*\*\s*\(\[([^\]]+)\]'
        match = re.match(markdown_pattern, company_name)
        
        if match:
            # Extract clean company name and acronym
            clean_company = match.group(1).strip()
            acronym = match.group(2).strip()
            new_name = f"{clean_company} ({acronym})"
            
            print(f"Fixing: '{company_name}' -> '{new_name}'")
            df.at[idx, 'חברה'] = new_name
            changes_made += 1
    
    print(f"\nTotal changes made: {changes_made}")
    
    if changes_made > 0:
        # Restore empty row at beginning if it existed
        if had_empty_row:
            empty_row = pd.DataFrame([['' for _ in range(len(df.columns))]], columns=df.columns)
            df = pd.concat([empty_row, df], ignore_index=True)
        
        # Save the updated CSV
        df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
        print(f"Updated CSV file saved: {csv_file_path}")
    else:
        print("No changes were needed.")

if __name__ == "__main__":
    csv_file = "Historical_Dividend_Announcements_Tel_Aviv_125_2022-05-06_to_2025-07-01.csv"
    fix_company_names_in_csv(csv_file)
