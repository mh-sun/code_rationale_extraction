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


def save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type):
    try:
        diff = commit_info['diff']
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        csv_row = [
            os.path.basename(repo_path), file, commit, change_type, str(diff),
            commit_info['added_line'] + commit_info['removed_line'], cond_type,
            commit_info['commit_massage'], commit_info['commit_description'], commit_info['notes']
        ]

        file_exists = os.path.isfile(output_path)
        with open(output_path, 'a') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(
                    ['repo', 'file', 'commit', 'change_type', 'diff', 'change_count', 'condition_type', 'commit_message', 'description',
                     'note'])
            writer.writerow(csv_row)
    except Exception as e:
        print(e)


def check_n_save_changes(commit_info, file, commit, repo_path, output_path):
    add_pattern = r'^\+.*\s+(if|else)\s+.*'
    remove_pattern = r'^-.*\s+(if|else)\s+.*'

    check_(add_pattern, remove_pattern, commit_info, file, output_path, repo_path, "condition")

    add_pattern = r'^\+.*\s+(for|while)\s+.*'
    remove_pattern = r'^-.*\s+(for|while)\s+.*'

    check_(add_pattern, remove_pattern, commit_info, file, output_path, repo_path, "iteration")


def check_(add_pattern, remove_pattern, commit_info, file, output_path, repo_path, cond_type):
    diff = commit_info['diff']
    commit = commit_info['commit_hash']
    added_conditions = re.findall(add_pattern, diff, re.MULTILINE)
    removed_conditions = re.findall(remove_pattern, diff, re.MULTILINE)
    added_count = len(added_conditions)
    removed_count = len(removed_conditions)
    if added_count == 1 and removed_count == 1:
        change_type = "Condition_Change"
        save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type)
    elif added_count == 1 and removed_count == 0:
        change_type = "Add_Condition"
        save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type)
    elif added_count == 0 and removed_count == 1:
        change_type = "Remove_Condition"
        save_changes(commit_info, change_type, file, commit, repo_path, output_path, cond_type)


def get_commit_info(file, commit_hash, repo_path):
    files_changed = run_command(f'git diff-tree --no-commit-id --name-only -r {commit_hash}', repo_path)

    java_files = [file for file in files_changed.split("\n") if file.endswith('.java')]
    java_files_count = len(java_files)

    if java_files_count != 1:
        return None

    if java_files[0] != file:
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

    diff_output = '\n'.join(line for line in diff_output.splitlines() if
                            not re.match(pattern1, line.strip()) and not re.match(pattern2,
                                                                                  line.strip()) and not re.match(
                                pattern3, line.strip()))

    added_lines = sum(1 for line in diff_output.splitlines() if line.startswith('+') and not line.startswith('++'))
    removed_lines = sum(1 for line in diff_output.splitlines() if line.startswith('-') and not line.startswith('--'))

    commit_dict = {
        'commit_massage': commitMessage,
        'commit_description': commitDescription,
        'notes': commitNotes,
        'commit_hash': re.search(r'^commit (\w+)', commit_info).group(1),
        'author': re.search(r'Author:\s*(.+)', commit_info).group(1).strip(),
        'date': re.search(r'CommitDate:\s*(.+)', commit_info).group(1).strip(),
        'diff': diff_output,
        'added_line': added_lines,
        'removed_line': removed_lines
    }

    return commit_dict


def process_file(commit_limit, file, repo_path, output_path):
    try:
        commits = get_last_commits(commit_limit, file, repo_path)
        for commit in commits:
            commit_info = get_commit_info(file, commit, repo_path)

            if commit_info is None:
                continue

            check_n_save_changes(commit_info, file, commit, repo_path, output_path)
    except Exception as e:
        print(e)


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
    parser.add_argument('-o', '--OUTPUT', type=str, default="dataset/code_rationale_list.csv",
                        help="output path of the rationale dataset")
    parser.add_argument('-c', '--COMMITLENGTH', type=int, default=10, help="limit on the number of commits to process")
    parser.add_argument('-t', '--TARGET', type=str, default='dataset/spring-framework',
                        help="path to the target repository")

    args = parser.parse_args()

    process_files(args.OUTPUT, args.COMMITLENGTH, args.TARGET)
