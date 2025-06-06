import os
import fire
import litellm
from tqdm import tqdm
from typing import Tuple

def count_tokens_in_repo(
    repo_path: str,
    model: str = "gpt-3.5-turbo",
    skip_dirs: Tuple[str, ...] = (
        '.git', '.venv', 'venv', 'env', 'node_modules', '__pycache__',
        'dist', 'build', '.vscode', '.idea', 'target', 'coverage'
    )
):
    """
    Calculates the total number of tokens for all code files in a given repository path,
    with support for skipping specified directories.

    :param repo_path: Path to the local code repository.
    :param model: The model name to use for token calculation.
    :param skip_dirs: A tuple of directory names to skip.
    """
    if not os.path.isdir(repo_path):
        print(f"❌ Error: The provided path '{repo_path}' is not a valid directory.")
        return

    abs_repo_path = os.path.abspath(repo_path)
    print(f"🔍 Analyzing repository: {abs_repo_path}")
    print(f"   - Model: {model}")
    print(f"   - Skipping: {list(skip_dirs)}")

    total_tokens = 0
    code_extensions = {
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go',
        '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.m', '.sh', '.html',
        '.css', '.scss', '.less', '.vue', '.jsx', '.tsx', '.json', '.yaml', '.yml',
        '.md', '.toml', '.dockerfile'
    }

    files_to_process = []
    for root, dirs, files in os.walk(repo_path, topdown=True):
        # Efficiently prune specified directories from traversal.
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if os.path.splitext(file)[1] in code_extensions:
                files_to_process.append(os.path.join(root, file))

    if not files_to_process:
        print("\n⚠️ No processable code files found in the specified path (after exclusions).")
        return

    with tqdm(total=len(files_to_process), desc="Processing files", unit="file", ncols=100) as pbar:
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    token_count = litellm.token_counter(model=model, text=content)
                    total_tokens += token_count
            except Exception as e:
                tqdm.write(f"❌ Failed to process file {file_path}: {e}")
            pbar.update(1)

    print("\n" + "="*45)
    print(f"✅ Analysis Complete!")
    print(f"📊 Total Tokens in Repository: {total_tokens:,}")
    print("="*45)

if __name__ == "__main__":
    fire.Fire(count_tokens_in_repo)