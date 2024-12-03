import json
import re
import requests
import pandas as pd
from tqdm import tqdm


def add_issue_reference(input_path, output):
    data = pd.read_csv(input_path)
    data.fillna("", inplace=True)

    # data = data.sample(10, random_state=42)

    def extract_issue_ids(text):
        gh_ids = re.findall(r'gh-(\d+)', text)
        hash_ids = re.findall(r'#(\d+)', text)

        return list(set(gh_ids + hash_ids))

    def find_gh_numbers(row):
        gh_numbers_in_sub = extract_issue_ids(row['commit_subject'])
        gh_numbers_in_body = extract_issue_ids(row['commit_body'])

        issue_numbers = list(set(gh_numbers_in_sub + gh_numbers_in_body))

        repo_url = f"https://api.github.com/repos/{row['repo']}/issues/"

        issue_links = [f"{repo_url}{issue_number}" for issue_number in issue_numbers]

        return issue_links

    data['linked_issues'] = data.apply(find_gh_numbers, axis=1)

    data['linked_issues_count'] = data['linked_issues'].apply(len)

    data.to_csv(output, index=False)
    # print(f"Issue Ids added to Issue List and saved to: {output}")

    return data


def extract_issue_details(all_issues_path, issue_link):
    with open(all_issues_path, 'r') as file:
        all_issues = json.load(file)

    for issue in all_issues:
        if issue.get('url') == issue_link:
            return issue
    return None


def add_ref_comments(input_path, output, all_issues):
    data = pd.read_csv(input_path)
    data.fillna("", inplace=True)

    # gh = input("Enter Github token: ")
    gh = "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"
    # gh = "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"
    headers = {"Authorization": f"token {gh}"}

    def fetch_issue_details(issue_links):
        titles, bodies, states, comments_count, all_comments_texts = [], [], [], [], []

        for issue_link in eval(issue_links):
            # Fetch issue details
            issue_response = requests.get(issue_link, headers=headers)

            if issue_response.status_code == 200:
                try:
                    issue_data = issue_response.json()
                    titles.append(issue_data.get("title", "N/A"))
                    bodies.append(issue_data.get("body", "N/A"))
                    states.append(issue_data.get("state", "N/A"))
                    comments_count.append(issue_data.get("comments", "N/A"))

                    # Fetch comments
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
                        print(f"Failed to fetch comments from {comments_link}, status code: {comments_response.status_code}")
                        all_comments_texts = ["N/A"]
                except requests.JSONDecodeError:
                    raise ValueError(f"Invalid JSON in issue response for {issue_link}")
            else:
                print(f"Failed to fetch issue from {issue_link}, status code: {issue_response.status_code}")
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


if __name__ == "__main__":

    datapath = 'dataset/code_rationale_list.csv'
    issues_added_path = 'dataset/cr_list_issue_ids.csv'
    issue_details_path = 'dataset/cr_list_issue_details.csv'
    all_issues = "dataset/all_issues.json"

    add_issue_reference(datapath, issues_added_path)
    add_ref_comments(issues_added_path, issue_details_path, all_issues)