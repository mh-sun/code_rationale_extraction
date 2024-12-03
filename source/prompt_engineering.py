import requests
import time
import json
import os
import pandas as pd

def run_model(model, input_text, prompt_technique, result):
    pass

def fetch_annotations(GROUP_ID, BASE_URL, HEADERS, LIMIT = 200):
    response = requests.get(
        f"{BASE_URL}?limit={LIMIT}&group={GROUP_ID}",
        headers=HEADERS
    )
    if response.status_code == 200:
        data = response.json()
        print("=" * 50)
        print(f"Collected {len(data['rows'])} annotations")
        print("=" * 50)
        return data['rows']
        
    elif response.status_code == 429:  # Rate limit exceeded
        print(f"Rate limit hit.")
    else:
        print(f"Failed to fetch data: {response.status_code}")

def existDir(path):
    os.makedirs(path, exist_ok=True)

def collect_annotations(output_path):
    API_TOKEN = "<API_TOKEN>"
    GROUP_ID = "jLAEz9aG"
    BASE_URL = f"https://api.hypothes.is/api/search"
    HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

    annotations = fetch_annotations(GROUP_ID, BASE_URL, HEADERS)

    existDir(os.path.dirname(output_path))
    with open(output_path, 'w') as f:
        json.dump(annotations, f, indent=4)

def get_rationale_data(commit, annotation_data, rationale_type):
    rationales = []

    commit_text = f"https://github.com/{commit['repo']}/commit/{commit['commit']}"

    if not pd.isna(commit['linked_issues_man']) and commit['linked_issues_man'] != "nan":
        if "," in commit['linked_issues_man']:
            linked_issues = [int(i) for i in commit['linked_issues_man'].split(',')]
        else:
            linked_issues = [int(commit['linked_issues_man'])]

        annotation_texts = [f"https://github.com/{commit['repo']}/issues/{li}" for li in linked_issues]
    
    else:
        annotation_texts = []

    for annotation in annotation_data:
        if annotation['uri'] == commit_text or annotation['uri'] in annotation_texts:
            if rationale_type != "RATIONALE" and annotation['text'] == rationale_type:
                texts = []
                for t in annotation['target']:
                    for s in t['selector']:
                        if s['type'] == "TextQuoteSelector":
                            texts.append(s['exact'])

                rationales.extend(texts)
            elif rationale_type == "RATIONALE":
                if annotation['text'].startswith("RATIONALE"):
                    rationales.append(annotation['text'])

    return rationales

    

def create_dataset(annotation_path, commit_path, output_path):
    commits_data = pd.read_csv(commit_path)
    with open(annotation_path, 'r') as file:
        annotation_data = json.load(file)

    commits_data = commits_data[commits_data['MAN_ANNOTATED'] == 1]

    dataset = []

    for _, row in commits_data.iterrows():

        commit = {}

        commit['repo'] = row['repo']
        commit['file'] = row['file']
        commit['commit'] = row['commit']
        commit['diff'] = row['diff']
        commit['change_count'] = row['change_count']
        commit['commit_message'] = str(row['commit_subject']) + "\n\n" + str(row['commit_body'])
        commit['is_commit_enough'] = row['COMMIT_DESC_ENOUGH']
        commit['linked_issues_man'] = str(row['MAN_LINKED_ISSUES'])
        commit['descriptive_issue'] = str(row['DESC_ISSUE'])
        commit['issue_name_change'] = str(row['ISSUE_NAME_CHNG_AFTER_CODE_IMP'])

        commit['IR_RATIONALE_PRES'] = get_rationale_data(commit, annotation_data, "IR_RATIONALE_PRES")
        commit['PR_RATIONALE_PRES'] = get_rationale_data(commit, annotation_data, "PR_RATIONALE_PRES")
        commit['CC_RATIONALE_PRES'] = get_rationale_data(commit, annotation_data, "CC_RATIONALE_PRES")
        commit['COM_T_RATIONALE_PRES'] = get_rationale_data(commit, annotation_data, "COM_T_RATIONALE_PRES")
        commit['COM_B_RATIONALE_PRES'] = get_rationale_data(commit, annotation_data, "COM_B_RATIONALE_PRES")
        commit['RATIONALE'] = get_rationale_data(commit, annotation_data, "RATIONALE")

        dataset.append(commit)
        
    existDir(os.path.dirname(output_path))
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=4)
    
    print(f"Dataset saved successfully to {output_path}")
        

def model_experiment():
    ### Constants Values ###

    models = []
    input_texts = []
    prompt_techniques = []
    results = []

    for model in models:
        for input_text in input_texts:
            for prompt_technique in prompt_techniques:
                for result in results:
                    run_model(model, input_text, prompt_technique, result)

if __name__ == "__main__":
    annotation_path = "dataset/gt_dataset.json"
    commit_list_path = "dataset/manual_analyzed_issues.csv"
    dataset_path = "dataset/annotated_dataset.json"

    # collect_annotations(annotation_path)
    # create_dataset(annotation_path, commit_list_path, dataset_path)

    # model_experiment()

    