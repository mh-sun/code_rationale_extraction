from const import *

import os
import subprocess

import argparse
import random
from concurrent.futures import ThreadPoolExecutor
import csv
import subprocess
import re
import os

import pandas as pd
from tqdm import tqdm


def run_command(command, repo_path):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    return result.stdout.strip()


def get_java_files(repo_path):
    command = "git ls-files '*.java' | grep -v '/test/' | grep -v '/Test'"
    return run_command(command, repo_path).splitlines()


def get_last_commits(file, repo_path, commit_limit=-1):
    command = f'git log {f"-n {commit_limit} " if commit_limit > 0 else ""}--pretty=format:"%H" --follow -- {file}'
    return run_command(command, repo_path).splitlines()

def save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type):
    try:
        diff = commit_info['diff']
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        repo = run_command("git remote get-url origin", repo_path)
        repo = repo.split('/')[-2] + "/" + repo.split('/')[-1].strip('.git')

        csv_row = [
            repo, file, commit, change_type, str(diff),
            commit_info['added_line'] + commit_info['removed_line'], cond_type,
            commit_info['commit_subject'], commit_info['commit_body'], commit_info['notes']
        ]

        file_exists = os.path.isfile(output_path)
        with open(output_path, 'a') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(
                    ['repo', 'file', 'commit', 'change_type', 'diff', 'change_count', 'condition_type',
                     'commit_subject', 'commit_body',
                     'note'])
            writer.writerow(csv_row)
    except Exception as e:
        print(e)


def check_n_save_changes(commit_info, file, commit, repo_path, output_path):
    add_pattern = r'^\+\s+(if|else)\s+.*'
    remove_pattern = r'^-\s+(if|else)\s+.*'

    check_(add_pattern, remove_pattern, commit_info, file, output_path, repo_path, "condition")

    add_pattern = r'^\+\s+(for|while)\s+.*'
    remove_pattern = r'^-\s+(for|while)\s+.*'

    check_(add_pattern, remove_pattern, commit_info, file, output_path, repo_path, "iteration")


def check_(add_pattern, remove_pattern, commit_info, file, output_path, repo_path, cond_type):
    diff = commit_info['diff']
    commit = commit_info['commit_hash']
    added_conditions = re.findall(add_pattern, diff, re.MULTILINE)
    removed_conditions = re.findall(remove_pattern, diff, re.MULTILINE)
    added_count = len(added_conditions)
    removed_count = len(removed_conditions)
    if added_count != 0 and added_count == removed_count:
        change_type = "Condition_Change"
        save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type)
    elif (added_count - removed_count) == 1:
        change_type = "Add_Condition"
        save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type)
    elif (removed_count - added_count) == 1:
        change_type = "Remove_Condition"
        save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type)

def get_commit_info(file, commit_hash, repo_path):
    java_files_count = run_command(f'git diff-tree --no-commit-id --name-only -r {commit_hash}  | grep ".java" | wc -l', repo_path)

    if int(java_files_count) != 1:
        return None

    commitMessage, commitDescription, commitNotes = run_command(
        f'git log -n 1 --pretty=format:"%s<<<SEP>>>%b<<<SEP>>>%N" {commit_hash}',
        repo_path).split("<<<SEP>>>")

    commit_info = run_command(f'git show --stat --patch --format=fuller {commit_hash}', repo_path)
    diff_output = run_command(
        f"git show --unified=0 --no-color {commit_hash} {file} | grep '^[+-]' | grep -Ev '^(---|\+\+\+)'", repo_path)

    # Comment Pattern
    pattern1 = r'^[+-]\s+\*\s*.*$'
    pattern2 = r'^[+-]\s+\/\*\*\s*.*\*\/$'
    pattern3 = r'^[+-]\s+\/\/.*$'

    diff_output_wo_comment = '\n'.join(line for line in diff_output.splitlines() if
                            not re.match(pattern1, line.strip()) and 
                            not re.match(pattern2, line.strip()) and 
                            not re.match(pattern3, line.strip()))
    
    added_lines = sum(1 for line in diff_output_wo_comment.splitlines() if line.startswith('+') and not line.startswith('++'))
    removed_lines = sum(1 for line in diff_output_wo_comment.splitlines() if line.startswith('-') and not line.startswith('--'))

    commit_dict = {
        'commit_subject': commitMessage,
        'commit_body': commitDescription,
        'notes': commitNotes,
        'commit_hash': re.search(r'^commit (\w+)', commit_info).group(1),
        'author': re.search(r'Author:\s*(.+)', commit_info).group(1).strip(),
        'date': re.search(r'CommitDate:\s*(.+)', commit_info).group(1).strip(),
        'diff': diff_output,
        'added_line': added_lines,
        'removed_line': removed_lines
    }

    return commit_dict

def process_file(file, repo_path, output_path):
    try:
        commits = get_last_commits(file, repo_path)
        for commit in commits:
            commit_info = get_commit_info(file, commit, repo_path)
            if commit_info is None:
                continue
            check_n_save_changes(commit_info, file, commit, repo_path, output_path)
    except Exception as e:
        print(e)


def process_files(dataset_path, repo_path):
    print(f"Commit Dataset Path: {dataset_path}")
    print(f"Repository Path: {repo_path}")

    if os.path.exists(dataset_path):
        os.remove(dataset_path)

    java_files = get_java_files(repo_path)

    with ThreadPoolExecutor(max_workers=max(os.cpu_count()-4, 1)) as executor:
        futures = [
            executor.submit(process_file, file, repo_path, dataset_path)
            for file in java_files
        ]

        for future in tqdm(futures):
            future.result()

def clone_and_checkout(repo_url, local_path, commit_hash):
    try:
        local_parent = os.path.dirname(local_path)
        os.makedirs(local_parent, exist_ok=True)
        print(f"\n\nCloning repository from {repo_url} to {local_parent}.\n\n")
        subprocess.run(["git", "clone", repo_url], check=True, cwd=local_parent)

        print(f"\n\nChecking out commit {commit_hash}.\n\n")
        subprocess.run(["git", "checkout", commit_hash], check=True, cwd=local_path)

        print("Repository cloned and checked out successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing Git commands: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def filter_commits(data_path):
    df = pd.read_csv(data_path)

    merged_df = (
    df.groupby("commit")
        .agg({
            "repo": "first",  # Keep the first repo
            "file": "first",  # Keep the first file
            "change_type": lambda x: ", ".join(sorted(set(x))),  # Merge unique change_types
            "diff": "first",  # Keep the first diff
            "change_count": "first",  # Keep the first change_count
            "condition_type": lambda x: ", ".join(sorted(set(x))),  # Merge unique condition_types
            "commit_subject": "first",  # Keep the first subject
            "commit_body": "first",  # Keep the first body
            "note": "first",  # Keep the first note
        })
        .reset_index()
    )

    # Step 2: Filter rows where change_count <= 10
    filtered_df = merged_df[merged_df["change_count"] <= 10]

    # Save the filtered DataFrame to the specified path
    filtered_df.to_csv(data_path, index=False)

    print(f"\n\nTotal Commit Count: {len(filtered_df)}")

if __name__ == "__main__":
    clone_and_checkout(TARGET_PROJ, TARGET_PROJ_LOCAL, TARGET_PROJ_LAST_COMMIT)
    process_files(COMMIT_DETAILS, TARGET_PROJ_LOCAL)
    filter_commits(COMMIT_DETAILS)