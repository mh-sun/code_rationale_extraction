import json
import re
import requests
import pandas as pd
import os
import time
import google.generativeai as genai
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

from tqdm import tqdm
from const import *

def add_issue_reference(input_path, output, all_issues_path):
    data = pd.read_csv(input_path)
    data.fillna("", inplace=True)

    with open(all_issues_path, 'r') as file:
        all_issues = json.load(file)
        spr_ids_dict = {}

        for issue in all_issues:
            pattern = r"\[SPR-(\d+)\]"
            match = re.search(pattern, issue['title'])
            if match:
                digits = match.group(1)
                spr_ids_dict[digits] = issue['number']

        print(f"\n\nFound {len(spr_ids_dict)} SPR IDs in total {len(all_issues)} Issues\n\n")
            

    def extract_issue_ids(text):
        gh_ids = re.findall(r'gh-(\d+)', text)
        hash_ids = re.findall(r'#(\d+)', text)
        spr_ids = re.findall(r'SPR-(\d+)', text)

        return gh_ids, hash_ids, spr_ids

    def find_gh_numbers(row, spr_ids_dict):
        gh_ids, hash_ids, spr_ids = extract_issue_ids(row['commit_subject'] + "\n\n" + row['commit_body'])

        print(f"GH Issue Count: {len(gh_ids)}, Hash Issue Count: {len(hash_ids)}, SPR Issue Count: {len(spr_ids)}")

        spr_ids = [str(spr_ids_dict[id]) for id in spr_ids]

        issue_ids = list(set(gh_ids+hash_ids+spr_ids))

        issue_ids = ', '.join(issue_ids)

        return issue_ids

    data['linked_issues'] = data.apply(lambda row: find_gh_numbers(row, spr_ids_dict), axis=1)

    data['linked_issues_count'] = data['linked_issues'].apply(lambda row: len(row.split(',')) if not not row else 0)

    data.to_csv(output, index=False)

    return data

def fetch_github_issues(owner='spring-projects', repo='spring-framework'):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {"Authorization": f"token {os.environ['GITHUB_API_KEY']}"}
    issues = []
    params = {"state": "all", "per_page": 100}
    page = 1

    while True:
        params["page"] = page
        print(f"Fetching page {page}...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Failed to fetch issues: {response.status_code} - {response.text}")
            break
        
        page_data = response.json()
        if not page_data:  
            break
        
        issues.extend(page_data)
        page += 1

    return issues

def save_all_issues(output_file):
    print(f"Fetching Issue\n\n")
    issues = fetch_github_issues()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=4)
    print(f"Issues saved to {output_file}")

def extract_issue_details(all_issues_path, issue_link):
    with open(all_issues_path, 'r') as file:
        all_issues = json.load(file)

    for issue in all_issues:
        if issue.get('url') == issue_link:
            return issue
    return None


def add_ref_comments(input_path, output):
    data = pd.read_csv(input_path)
    data.fillna("", inplace=True)

    headers = {"Authorization": f"token {os.environ['GITHUB_API_KEY']}"}

    def fetch_issue_details(issue_links):
        titles, bodies, states, comments_count, all_comments_texts = [], [], [], [], []

        issue_links = [i.strip() for i in issue_links.split(',')]

        if len(issue_links) == 1 and '' in issue_links:
            return {
                    'issue_titles': "N/A",
                    'issue_bodies': "N/A",
                    'issue_states': "N/A",
                    'issue_comments_count': "N/A",
                    'issue_comments': "N/A"
                }

        for issue_link in issue_links:
            issue_link = f"https://api.github.com/repos/spring-projects/spring-framework/issues/{issue_link}"

            issue_response = requests.get(issue_link, headers=headers)

            if issue_response.status_code == 200:
                try:
                    issue_data = issue_response.json()
                    titles.append(issue_data.get("title", "N/A"))
                    bodies.append(issue_data.get("body", "N/A"))
                    states.append(issue_data.get("state", "N/A"))
                    comments_count.append(issue_data.get("comments", "N/A"))

                    comments_link = issue_data.get("comments_url", "")
                    comments_response = requests.get(comments_link, headers=headers)

                    if comments_response.status_code == 200:
                        try:
                            comments_data = comments_response.json()
                            comments_texts = [comment.get("body", "") for comment in comments_data]
                            all_comments_texts = comments_texts
                        except requests.JSONDecodeError:
                            raise ValueError(f"Invalid JSON in comments response for {comments_link}")
                    else:
                        print(f"Failed to fetch << comments >> from {comments_link}, status code: {comments_response.status_code}")
                        all_comments_texts = ["N/A"]
                except requests.JSONDecodeError:
                    raise ValueError(f"Invalid JSON in issue response for {issue_link}")
            else:
                print(f"Failed to fetch << issue >> from {issue_link}, status code: {issue_response.status_code}")
                return {
                    'issue_titles': "N/A",
                    'issue_bodies': "N/A",
                    'issue_states': "N/A",
                    'issue_comments_count': "N/A",
                    'issue_comments': "N/A"
                }

        return {
            'issue_titles': titles,
            'issue_bodies': bodies,
            'issue_states': states,
            'issue_comments_count': comments_count,
            'issue_comments': all_comments_texts
        }

    tqdm.pandas(desc="Fetching Issue Details")
    details = data['linked_issues'].progress_apply(fetch_issue_details)

    data['issue_titles'] = details.apply(lambda x: x['issue_titles'])
    data['issue_bodies'] = details.apply(lambda x: x['issue_bodies'])
    data['issue_states'] = details.apply(lambda x: x['issue_states'])
    data['issue_comments_count'] = details.apply(lambda x: x['issue_comments_count'])
    data['issue_comments'] = details.apply(lambda x: x['issue_comments'])

    data.to_csv(output, index=False)
    print(f"Issue details added to Issue List and saved to: {output}")

    return data

def filter_issue_desc(path):
    df = pd.read_csv(path)

    def filter_diff(diff_text):
        lines = diff_text.split('\n')
        filtered_lines = [
            line for line in lines if not re.match(r'^[\+\-]\s*\*\s*Copyright', line, re.IGNORECASE)
        ]
        # Join the filtered lines back
        return '\n'.join(filtered_lines)

    df['diff'] = df['diff'].apply(filter_diff)

    df.to_csv(path, index=False)

def getGeminiCCSummary(row, model):
    try:
        response = model.generate_content(
            f"summarize this code change made in {row['file']}:\n{row['diff']}", 
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=100,
                temperature=0.2,
                top_k=3,
            )
        )

        # Wait 4.5 second till next request
        time.sleep(4.1)
        
        return {
            "text": response.text, 
            "avg_logprobs": response.candidates[0].avg_logprobs,
            "usage_metadata": response.usage_metadata
        }
    except Exception as e:
        print(f"Error processing row {row['file']}: {e}")
        return {"text": None, "avg_logprobs": None, "usage_metadata": None}

def add_diff_summary(input_path, output_path):
    df = pd.read_csv(input_path)
    df = df.drop_duplicates(subset='diff', keep='first')
    
    model = genai.GenerativeModel(
        "models/gemini-1.5-flash-8b", 
        system_instruction=(
            "You are an advanced code summarization assistant specialized in Java. Your task is to analyze and summarize changes in code diffs, with a focus on modifications to conditional logic (e.g., if, else if, switch) and iteration constructs (e.g., for, while)."
        )
    )
    
    tqdm.pandas(desc="Generating Code Change Summaries")
    df['gemini_cc_summary__k_3__temp_2'] = df.progress_apply(
        lambda row: getGeminiCCSummary(row, model=model), axis=1
    )
    
    df.to_csv(output_path, index=False)



if __name__ == "__main__":
    # save_all_issues(ALL_ISSUES)
    # add_issue_reference(COMMIT_DETAILS, COMMIT_W_ISSUE_ID, ALL_ISSUES)
    # add_ref_comments(COMMIT_W_ISSUE_ID, COMMIT_W_ISSUE_DESC)
    # filter_issue_desc(COMMIT_W_ISSUE_DESC)
    add_diff_summary(COMMIT_W_ISSUE_DESC, COMMIT_W_CC_SUMMARY)