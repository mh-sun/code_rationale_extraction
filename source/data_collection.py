import argparse
from concurrent.futures import ThreadPoolExecutor
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


def get_last_commits(commit_limit, file, repo_path):
    command = f'git log -n {commit_limit} --pretty=format:"%H" --follow -- {file}'
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


def process_file(commit_limit, file, repo_path, output_path):
    commits = get_last_commits(commit_limit, file, repo_path)
    for commit in commits:
        diff = get_diff(file, commit, repo_path)
        check_n_save_changes(diff, file, commit, repo_path, output_path)

def process_files(rationale_dataset_path, commit_limit, repo_path):

    print(f"Rationale Dataset Path: {rationale_dataset_path}")
    print(f"Commit Limit: {commit_limit}")
    print(f"Repository Path: {repo_path}")

    java_files = get_java_files(repo_path)

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = [
            executor.submit(process_file, commit_limit, file, repo_path, rationale_dataset_path)
            for file in java_files
        ]

        for future in tqdm(futures):
            future.result()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Java files in a repository.")
    parser.add_argument('-o', '--OUTPUT', type=str, default="dataset/code_rationale_list.csv", help="output path of the rationale dataset")
    parser.add_argument('-c', '--COMMITLENGTH', type=int, default=10, help="limit on the number of commits to process")
    parser.add_argument('-t', '--TARGET', type=str, default='dataset/spring-framework', help="path to the target repository")

    args = parser.parse_args()

    process_files(args.OUTPUT, args.COMMITLENGTH, args.TARGET)