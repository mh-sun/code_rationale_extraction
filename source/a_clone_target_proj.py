from const import *

import os
import subprocess

def clone_and_checkout(repo_url, local_path, commit_hash):
    try:
        os.makedirs(local_path, exist_ok=True)
        print(f"Cloning repository from {repo_url} to {local_path}...")
        subprocess.run(["git", "clone", repo_url], check=True, cwd=local_path)

        folder_name:str = repo_url.split('/')[-1]
        folder_name = folder_name.replace('.git', '')

        os.chdir(os.path.join(local_path, folder_name))

        print(f"Checking out commit {commit_hash}...")
        subprocess.run(["git", "checkout", commit_hash], check=True)

        print("Repository cloned and checked out successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing Git commands: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

clone_and_checkout(TARGET_PROJ, TARGET_PROJ_LOCAL, TARGET_PROJ_LAST_COMMIT)