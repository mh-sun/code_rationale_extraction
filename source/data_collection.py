import csv
import subprocess
import re
import os
from tqdm import tqdm


def run_command(command, repo_path):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    return result.stdout.strip()


def get_java_files(repo_path):
    command = 'git ls-files "*.java" | grep -v "test"'
    return run_command(command, repo_path).splitlines()


def get_last_commits(file, repo_path):
    command = f'git log -n 10 --pretty=format:"%H" --follow -- {file}'
    return run_command(command, repo_path).splitlines()


def get_diff(file, commit, repo_path):
    command = f'git show {commit} -- {file}'
    return run_command(command, repo_path)


def save_changes(diff, change_type, file, commit, repo_path, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    csv_row = [
        os.path.basename(repo_path), file, commit, change_type, str(diff)
    ]

    file_exists = os.path.isfile(output_path)
    with open(output_path, 'a') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['repo', 'file', 'commit', 'change_type', 'diff'])
        writer.writerow(csv_row)


def check_n_save_changes(diff, file, commit, repo_path, output_path):
    #condition change
    if re.search(r'^\+.*(if|else|for|while)\s*\(', diff, re.MULTILINE):
        change_type = "Condition_Change"
        save_changes(diff, change_type, file, commit, repo_path, output_path)

    #method addition
    if re.search(r'^\+\s*(public|protected|private)\s+\w+\s+\w+\s*\(', diff, re.MULTILINE):
        change_type = "Method_Addition"
        save_changes(diff, change_type, file, commit, repo_path, output_path)

    #return type changes
    if re.search(r'^\-.*(public|protected|private)\s+\w+\s+\w+\s*\(', diff, re.MULTILINE):
        change_type = "Return_Type_Change"
        save_changes(diff, change_type, file, commit, repo_path, output_path)

    #parameter changes
    removed_params = re.search(r'^\-.*\(.*\).*', diff, re.MULTILINE)
    added_params = re.search(r'^\+.*\(.*\).*', diff, re.MULTILINE)
    if removed_params and added_params:
        change_type = "Parameter_Change"
        save_changes(diff, change_type, file, commit, repo_path, output_path)


def process_files():
    rationale_dataset_path = "dataset/code_rationale_list.csv"

    repo_path = 'dataset/spring-framework'

    java_files = get_java_files(repo_path)

    for file in tqdm(java_files):
        # print(f"\nProcessing file: {file}")

        commits = get_last_commits(file, repo_path)
        for commit in commits:
            # print(f"Checking commit: {commit}")

            diff = get_diff(file, commit, repo_path)
            check_n_save_changes(diff, file, commit, repo_path, rationale_dataset_path)


if __name__ == "__main__":
    process_files()
