# @author: stephen

from pathlib import Path
from tqdm import tqdm
from typing import List


disable_tqdm = True


def search_java_files(repo_path: str, search_func) -> List[str]:
    """
    search files by search_func

    """
    repo_path_obj = Path(repo_path)
    if not repo_path_obj.is_dir():
        print(f"Error: Provided path '{repo_path}' is not a valid directory.")
        return []

    java_files = list(repo_path_obj.rglob("*.java"))
    matched_files = []
    for java_file in tqdm(java_files, desc="Searching file in " + repo_path, disable=disable_tqdm):

        if search_func(java_file):
            matched_files.append(str(java_file))
    return matched_files


def search_java_file(repo_path: str, search_func) -> str | None:
    """
    search file by search_func

    """
    repo_path_obj = Path(repo_path)
    if not repo_path_obj.is_dir():
        print(f"Error: Provided path '{repo_path}' is not a valid directory.")
        return None

    java_files = list(repo_path_obj.rglob("*.java"))
    for java_file in tqdm(java_files, desc="Searching file in " + repo_path, disable=disable_tqdm):
        if search_func(java_file):
            return str(java_file)
    return None