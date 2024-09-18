import subprocess
import os
import shutil
import sys

def install_mkdocs_with_pipenv():
    """
    Builds a particular branch site.
    Having a varying set of requirements can be handled by having each branch
    build their dependencies and then running mkdocs build.
    """
    folder = os.getcwd()
    subprocess.run(["pipenv", "install", "--site-packages"], cwd=folder)
    subprocess.run(["pipenv", "install", "-r", "requirements.txt"], cwd=folder)
    subprocess.run(["pipenv", "run", "mkdocs", "build"], cwd=folder)

def copy_folder(source_dir, target_dir):
    """
    Copies contents from source directory to target directory
    :param source_dir: Source directory from which contents are to be copied
    :param target_dir: Target Directory where the contents are copied to.
    """
    os.makedirs(target_dir, exist_ok=True)

    for item in os.listdir(source_dir):
        source_path = os.path.join(source_dir, item)
        target_path = os.path.join(target_dir, item)

        if os.path.isdir(source_path):
            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            if os.path.exists(target_path):
                os.remove(target_path)
            shutil.copy2(source_path, target_path)

def delete_folders(folder_paths):
    """
    Cleans existing folders for app and branches before executing the builds
    :param folder_paths: List of folders to be deleted under the current working directory
    """
    for folder_path in folder_paths:
        try:
            shutil.rmtree(folder_path)
            print(f"Folder {folder_path} deletion successful.")
        except OSError as e:
            print(f"Error deleting folder: {e}")

def process_branch_folders(branch_pattern):
    """
    Clones the branch specific code to branch/<branch-name> folder.
    It then executes the build command and copy the built site to apps folder
    under the same branch name
    :param branch_pattern: Pattern to identify remote branch to pull and build.
    :return: All branch names identified using the pattern
    """
    delete_folders(["branch", "app"])
    remote_url = subprocess.run(["git", "remote", "get-url", "origin"],
                                capture_output=True,
                                text=True).stdout.strip()
    all_branches = []
    parent_dir = os.getcwd()
    common_dir = "branch"

    for branch in subprocess.run(["git", "branch", "-r", "--list", branch_pattern, "|", "grep", "-v", "'\->'"],
                                 capture_output=True,
                                 text=True).stdout.splitlines():
        branch_name = branch.replace("origin/", "").strip().split(" ", 1)[0]
        all_branches.append(branch_name)
        target_path = os.path.join(common_dir, branch_name)
        os.makedirs(target_path, exist_ok=True)
        os.chdir(target_path)
        subprocess.run(["git", "init"])
        subprocess.run(["git", "remote", "add", "origin", remote_url])
        print(f"Checking out branch {branch_name}")
        subprocess.run(["git", "fetch", "--depth", "1", "origin", branch_name])
        subprocess.run([
            "git", "checkout", "-b", branch_name, "--track",
            f"origin/{branch_name}"
        ])
        install_mkdocs_with_pipenv()
        source_dir = os.path.join(os.getcwd(), "site")
        copy_folder(source_dir, os.path.join(parent_dir, "app", branch_name))
        os.chdir(parent_dir)

    return all_branches

def update_nginx_config(branches):
    """
    Updates nginx.conf file with branches built information to host multiple versions
    of software at the same time.
    :param branches: Branches built for hosting.
    """
    config_file = os.path.join(os.getcwd(), "nginx.conf")
    nginx_location_blocks = ""

    for folder in branches:
        location_block = f"""location /{folder} {{
            alias /app/{folder};
            try_files $uri $uri/ /index.html;
            error_page 404 /404.html;
        }}
        """
        nginx_location_blocks += location_block

    first_folder = branches[0]

    with open(config_file, "r+") as f:
        content = f.read()
        content = content.replace("REPLACE_APPS", nginx_location_blocks)
        content = content.replace("REPLACE_FIRST_APP", first_folder)
        f.seek(0)
        f.write(content)
        f.truncate()

    print("NGINX configuration updated successfully!")

if __name__ == "__main__":
    pattern = sys.argv[1]  # Argument passed from command line to identify branch pattern
    print("Branch pattern:", pattern)
    current_dir = os.getcwd()
    branches = process_branch_folders(pattern)
    update_nginx_config(branches)
