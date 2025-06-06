import os
import fire
import litellm
from tqdm import tqdm
from typing import Tuple

try:
    from gitignore_parser import parse_gitignore
except ImportError:
    print("Warning: 'gitignore-parser' not found. To use .gitignore files, please install it:")
    print("pip install gitignore-parser")
    parse_gitignore = None

# Suppress litellm's informational messages for a cleaner output
litellm.suppress_prompt_logging = True

def count_tokens_and_cost(
    repo_path: str,
    model: str = "gpt-4o",
    default_skip_dirs: Tuple[str, ...] = (
        '.git', '.venv', 'venv', 'env', 'node_modules', '__pycache__',
        'dist', 'build', '.vscode', '.idea', 'target', 'coverage'
    )
):
    """
    Calculates tokens and estimates input cost for a repository.

    :param repo_path: Path to the local code repository.
    :param model: The model for token counting and cost estimation.
    :param default_skip_dirs: Fallback tuple of directories to skip if .gitignore is not present.
    """
    if not os.path.isdir(repo_path):
        print(f"❌ Error: The provided path '{repo_path}' is not a valid directory.")
        return

    abs_repo_path = os.path.abspath(repo_path)
    print(f"🔍 Analyzing repository: {abs_repo_path}")
    print(f"   - Model for count & cost: {model}")

    files_to_process = []
    code_extensions = {
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go',
        '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.m', '.sh', '.html',
        '.css', '.scss', '.less', '.vue', '.jsx', '.tsx', '.json', '.yaml', '.yml',
        '.md', '.toml', '.dockerfile'
    }

    gitignore_path = os.path.join(abs_repo_path, '.gitignore')
    use_gitignore = os.path.exists(gitignore_path) and parse_gitignore

    if use_gitignore:
        print(f"   - Using exclusion rules from: .gitignore")
        matcher = parse_gitignore(gitignore_path, base_dir=abs_repo_path)
    else:
        if not parse_gitignore and os.path.exists(gitignore_path):
            print("   - Warning: Found .gitignore but 'gitignore-parser' is not installed. Falling back to defaults.")
        else:
            print(f"   - .gitignore not found. Using default skip list.")
        print(f"   - Skipping directories: {list(default_skip_dirs)}")

    for root, dirs, files in os.walk(abs_repo_path, topdown=True):
        if '.git' in dirs:
            dirs.remove('.git')

        # Apply exclusion rules
        if use_gitignore:
            # Prune directories based on .gitignore rules for efficiency
            dirs[:] = [d for d in dirs if not matcher(os.path.join(root, d))]

            for file in files:
                file_path = os.path.join(root, file)
                if not matcher(file_path) and os.path.splitext(file)[1] in code_extensions:
                    files_to_process.append(file_path)
        else:
            # Fallback: Prune directories based on the default list
            dirs[:] = [d for d in dirs if d not in default_skip_dirs]

            for file in files:
                if os.path.splitext(file)[1] in code_extensions:
                    files_to_process.append(os.path.join(root, file))

    if not files_to_process:
        print("\n⚠️ No processable code files found in the specified path (after exclusions).")
        return

    total_tokens = 0
    with tqdm(total=len(files_to_process), desc="Processing files", unit="file", ncols=100) as pbar:
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    total_tokens += litellm.token_counter(model=model, text=content)
            except Exception as e:
                tqdm.write(f"❌ Failed to process file {file_path}: {e}")
            pbar.update(1)

    estimated_cost = 0.0
    try:
        model_info = litellm.get_model_info(model=model)
        input_cost_per_token = model_info.get('input_cost_per_token', 0.0)
        if input_cost_per_token > 0:
            estimated_cost = total_tokens * input_cost_per_token
    except Exception as e:
        print(f"\nDEBUG: An error occurred during cost calculation: {e}")

    print("\n" + "="*50)
    print(f"✅ Analysis Complete!")
    print(f"📊 Total Tokens in Repository: {total_tokens:,}")

    if estimated_cost is not None and estimated_cost > 0:
        print(f"💵 Estimated Input Cost (USD): ${estimated_cost:.6f}")
    else:
        print(f"⚠️ Could not calculate cost for model '{model}'. It may not be in litellm's pricing data.")
    print("="*50)

if __name__ == "__main__":
    fire.Fire(count_tokens_and_cost)