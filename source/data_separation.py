import json
import re
import requests
import pandas as pd
from tqdm import tqdm

def save_separated_issue(issue_details_path, issues_for_manual_analysis):
    try:
        issues_df = pd.read_csv(issue_details_path)
    except Exception as e:
        print(f"Error reading the file: {e}")
        return

    print("Preview of issue details:")
    print(issues_df.head())

    filtered_issues = issues_df[
        (issues_df['change_count'] <= 10)
    ]

    print(f"Filtered Issue List Count: {len(filtered_issues)}")

    filtered_issues = filtered_issues.sort_values(by='change_count', ascending=False)
    filtered_issues = filtered_issues.sample(218, random_state=42)

    print(f"Filtered Issue List Count: {len(filtered_issues)}")

    try:
        filtered_issues.to_csv(issues_for_manual_analysis, index=False)
        print(f"Filtered issues saved to {issues_for_manual_analysis}")
    except Exception as e:
        print(f"Error saving the file: {e}")

if __name__ == "__main__":

    issue_details_path = 'dataset/cr_list_issue_details.csv'
    issues_for_manual_analysis = 'dataset/issues_for_manual_analysis.csv'
    
    save_separated_issue(issue_details_path, issues_for_manual_analysis)