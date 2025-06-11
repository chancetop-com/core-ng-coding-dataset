import os
import fire
import litellm
from tqdm import tqdm
from typing import Tuple
from gitignore import GitignoreMatcher

# Suppress litellm's informational messages for a cleaner output
litellm.suppress_prompt_logging = True

def count_repo_tokens(
    repo_path: str,
    model: str = "gpt-4o"
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
    print(f"🔍Analyzing repository: {abs_repo_path}")
    print(f"  - Model for count & cost: {model}")

    files_to_process = []
    code_extensions = {
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go',
        '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.m', '.sh', '.html',
        '.css', '.scss', '.less', '.vue', '.jsx', '.tsx', '.json', '.yaml', '.yml',
        '.md', '.toml', '.dockerfile'
    }

    matcher = GitignoreMatcher(abs_repo_path)

    for root, _, files in tqdm(matcher.walk(), desc="Scanning directories", unit="dir", ncols=100):
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

def count_stdin_tokens(
    model: str = "gpt-4o"
) -> Tuple[int, float]:
    """
    Count tokens and estimate cost from standard input.
    
    :param model: The model for token counting and cost estimation.
    :return: Tuple of (total_tokens, estimated_cost)
    """
    import sys
    if sys.stdin.isatty():
        print("Error: No input provided via stdin")
        return (0, 0.0)
        
    input_text = sys.stdin.read()
    total_tokens = litellm.token_counter(model=model, text=input_text)
    
    estimated_cost = 0.0
    try:
        model_info = litellm.get_model_info(model=model)
        input_cost_per_token = model_info.get('input_cost_per_token', 0.0)
        if input_cost_per_token > 0:
            estimated_cost = total_tokens * input_cost_per_token
    except Exception as e:
        print(f"\nDEBUG: An error occurred during cost calculation: {e}")
    
    print(f"Tokens: {total_tokens}, Cost: {estimated_cost}")

if __name__ == "__main__":
    fire.Fire({
        'repo': count_repo_tokens,
        'stdin': count_stdin_tokens
    })