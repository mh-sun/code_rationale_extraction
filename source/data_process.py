import re
import requests
import pandas as pd


def add_issue_reference(input_path, output):
    data = pd.read_csv(input_path)
    data.fillna("", inplace=True)

    # Function to extract gh- numbers from a string
    def extract_gh_numbers(commit_message):
        return re.findall(r'gh-(\d+)', commit_message)

    # Function to search commit_message and description columns for gh- numbers
    def find_gh_numbers(row):
        gh_numbers_col1 = extract_gh_numbers(row['commit_message'])
        gh_numbers_col2 = extract_gh_numbers(row['description'])

        issue_numbers = list(set(gh_numbers_col1 + gh_numbers_col2))

        repo_url = f"https://github.com/spring-projects/spring-framework/issues/"

        issue_links = [f"{repo_url}{issue_number}" for issue_number in issue_numbers]

        return issue_links

    data['linked_issues'] = data.apply(find_gh_numbers, axis=1)

    data.to_csv(output, index=False)

    return data


def add_ref_comments(input_path, output):
    data = pd.read_csv(input_path)
    data.fillna("", inplace=True)

    # gh = input("Enter Github token: ")
    gh = "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"
    headers = {"Authorization": f"token {gh}"}

    # Function to retrieve details and comments for a list of issue links
    def fetch_issue_details(issue_links):
        titles, states, comments_count, comments_texts = [], [], [], []

        for issue_link in eval(issue_links):
            # Fetch issue details
            issue_response = requests.get(issue_link, headers=headers)
            if issue_response.status_code == 200:
                issue_data = issue_response.json()
                titles.append(issue_data.get("title", "N/A"))
                states.append(issue_data.get("state", "N/A"))
                comments_count.append(issue_data.get("comments", "N/A"))

                # Fetch issue comments
                comments_link = issue_data.get("comments_url", "")
                comments_response = requests.get(comments_link, headers=headers)
                if comments_response.status_code == 200:
                    comments_data = comments_response.json()
                    comments_texts.append([comment.get("body", "") for comment in comments_data])
                else:
                    comments_texts.append(["N/A"])
            else:
                titles.append("N/A")
                states.append("N/A")
                comments_count.append("N/A")
                comments_texts.append(["N/A"])

        return {
            'issue_titles': titles,
            'issue_states': states,
            'issue_comments_count': comments_count,
            'issue_comments': comments_texts
        }

    # Apply the fetch_issue_details function and create new columns
    details = data['linked_issues'].apply(fetch_issue_details)
    data['issue_titles'] = details.apply(lambda x: x['issue_titles'])
    data['issue_states'] = details.apply(lambda x: x['issue_states'])
    data['issue_comments_count'] = details.apply(lambda x: x['issue_comments_count'])
    data['issue_comments'] = details.apply(lambda x: x['issue_comments'])

    data.to_csv(output, index=False)

    return data


if __name__ == "__main__":

    datapath = 'dataset/code_rationale_list.csv'
    issues_added_path = 'dataset/code_rationale_list_v1.csv'
    issue_details_path = 'dataset/code_rationale_list_v2.csv'

    add_issue_reference(datapath, issues_added_path)
    # add_ref_comments(issues_added_path, issue_details_path)