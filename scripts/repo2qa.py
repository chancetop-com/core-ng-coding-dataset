import fire
import litellm
import json
import os
import textwrap
import subprocess
from pathlib import Path
from typing import Optional
from token_cost_counter import count_cost


LIBRARY_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE = textwrap.dedent("""
# ROLE:
You are a Principal Software Engineer and a core architect of an internal Java framework named - core-ng. You have an encyclopedic knowledge of its internal workings, design patterns, and architectural rationale. You are creating a comprehensive knowledge base to train a new AI assistant.

# CONTEXT:
You will be provided with a `PRUNED_CONTEXT_BUNDLE`, which contains the API signatures and documentation of all relevant files for a specific framework module. You will also receive a `TARGET_FILE`, which is the one file you must focus on for this task. Your goal is to generate Q&A pairs specifically about the `TARGET_FILE`, using the `PRUNED_CONTEXT_BUNDLE` to understand its dependencies and interactions with other parts of the framework.

# TASK:
Analyze the `TARGET_FILE` within its full ecosystem context provided by the `PRUNED_CONTEXT_BUNDLE`. Generate a list of **3 to 5** insightful, diverse question-and-answer pairs that illuminate the inner workings of the `TARGET_FILE`.

# CRITERIA FOR EACH PAIR:
- The **Question** must be a deep, specific query about the `TARGET_FILE`'s logic, design choices, or its interaction with dependencies. It should probe the "why" or "how" behind the code.
- The **Answer** must be authoritative and clear. It should leverage information from the `PRUNED_CONTEXT_BUNDLE` to explain how the `TARGET_FILE` collaborates with other classes and what the purpose of these interactions is.
- The generated pairs must cover different aspects (e.g., a specific method's algorithm, class-level design, error handling strategy).

# ===============================================
# INPUTS
# ===============================================

## PRUNED_CONTEXT_BUNDLE:
(Contains API signatures & docstrings of all dependency files in the module)
{PRUNED_CONTEXT_BUNDLE}

## TARGET_FILE_NAME:
(The name of the file to focus on)
{TARGET_FILE_NAME}

## TARGET_FILE_CONTENT:
(The full, original source code of the file to focus on)
{TARGET_FILE_CONTENT}

# ===============================================
# OUTPUT FORMAT
# ===============================================
You MUST provide the output in a single, valid JSON block. The root element must be a JSON array of objects.

[
  {{
    "query": "In `{TARGET_FILE_NAME}`, why is the `someMethod` designed to be asynchronous by returning a CompletableFuture, and how does it interact with the `SomeDependencyService` seen in the context bundle?",
    "response": "The `someMethod` is designed to be asynchronous to prevent blocking the main thread during I/O-intensive operations, a key design principle in our framework for high-throughput services. It interacts with `SomeDependencyService.executeAsync()` (whose signature you can see in the provided context) which is the designated non-blocking client for that external system. This ensures end-to-end reactivity."
  }},
  {{
    "query": "...",
    "response": "..."
  }}
]
""")

LITELLM_MODEL = "azure/gpt-4o"

def generate_qa_pairs(target_file_name: str, target_file_content: str, pruned_context_bundle: str, prompt_template: str = LIBRARY_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE) -> Optional[str]:
    """
    Generates Q&A pairs for a target file using an LLM.

    Args:
        target_file_name: The name of the file to generate Q&A for.
        target_file_content: The full source code of the target file.
        pruned_context_bundle: A string containing the source code of dependency files.
        prompt_template: The template used to format the prompt for the LLM.

    Returns:
        A string containing a JSON array of Q&A pairs, or None if an error occurs.
    """
    print(f"  - Generating Q&A with model: {LITELLM_MODEL}")
    prompt = prompt_template.format(
        PRUNED_CONTEXT_BUNDLE=pruned_context_bundle,
        TARGET_FILE_NAME=target_file_name,
        TARGET_FILE_CONTENT=target_file_content,
    )

    try:
        response = litellm.completion(
            model=LITELLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Lower temperature for more factual, less creative output
        )

        # Extract the text content from the response
        content = response.choices[0].message.content

        # Clean the response: LLMs sometimes wrap JSON in markdown fences (```json ... ```)
        if content.strip().startswith("```json"):
            content = content.strip()[7:-3].strip()
        elif content.strip().startswith("```"):
            content = content.strip()[3:-3].strip()

        usage = response.get("usage")
        completion_tokens = usage.get("completion_tokens", 0)
        completion_cost = count_cost(completion_tokens, model=LITELLM_MODEL, token_type="input_cost_per_token")
        prompt_tokens = usage.get("prompt_tokens", 0)
        prompt_cost = count_cost(completion_tokens, model=LITELLM_MODEL, token_type="output_cost_per_token")
        total_tokens = usage.get("total_tokens", 0)
        total_cost = completion_cost + prompt_cost
        print(f"  - Usage: {completion_tokens} completion tokens - cost: {completion_cost}, {prompt_tokens} prompt tokens - cost: {prompt_cost}, {total_tokens} total tokens - cost: {total_cost}")
        # Validate that the content is valid JSON
        json.loads(content)
        return content

    except json.JSONDecodeError as e:
        print(f"    !! ERROR: LLM returned invalid JSON. {e}")
        print(f"    -- Raw Response --\n{content}\n--------------------")
        return None
    except Exception as e:
        print(f"    !! ERROR: An exception occurred during the litellm API call: {e}")
        return None


def build_pruned_context_bundle(repo_path: str, target_file_path: str) -> str:
    """
    Build a pruned context bundle by calling an external Java parser script.

    This function executes `repo_java_parser.py resolve` to perform static
    analysis on the target Java file and get its relevant dependencies.

    Args:
        repo_path: The root path of the repository.
        target_file_path: The absolute path to the target .java file.

    Returns:
        A single string containing the concatenated context from the parser,
        or an empty string if an error occurs.
    """
    try:
        parser_script_path = Path(__file__).parent.resolve() / "repo_java_parser.py"
        # Define the command to execute the external script
        command = [
            "python",
            str(parser_script_path),
            "resolve",
            str(repo_path),
            str(target_file_path)
        ]

        # Execute the command and capture the output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # Raise an exception for non-zero exit codes
            encoding='utf-8'
        )
        
        # The standard output of the script is the context bundle
        return result.stdout

    except FileNotFoundError:
        print(f"!! ERROR: The parser script 'repo_java_parser.py' was not found.")
        print("!! Ensure the script is in your current directory or system's PATH.")
        return ""
    except subprocess.CalledProcessError as e:
        # This error is raised when the script returns a non-zero exit code (i.e., it failed)
        print(f"!! ERROR: The parser script failed while processing '{Path(target_file_path).name}'.")
        print(f"   - Exit Code: {e.returncode}")
        print(f"   - Stderr:\n{e.stderr}")
        return ""
    except Exception as e:
        print(f"!! ERROR: An unexpected error occurred while building the context bundle for '{Path(target_file_path).name}': {e}")
        return ""


def file2qa(repo_path: str, target_file_path: str, prompt_template: str = LIBRARY_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE, rst_path: str = "library-source-code-to-qa.jsonl") -> None:
    """
    Orchestrates the Q&A generation process for a single Java file.
    It builds the context, generates the Q&A, and saves it to a .json file.

    Args:
        repo_path: The root path of the repository.
        target_file_path: The absolute path to the target .java file.
        rst_path: The path where the generated Q&A will be saved as a JSON file.
        prompt_template: The template used to format the prompt for the LLM.
    """
    target_path_obj = Path(target_file_path)
    output_path = Path(rst_path)

    # Check if the file has already been processed
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding="utf-8") as f:
            existing_data = json.load(f)
        processed_files = {entry.get("filename") for entry in existing_data}
        if target_path_obj.name in processed_files:
            print(f"  - SKIPPED: {target_path_obj.name} is already processed.")
            return
    else:
        existing_data = []

    try:
        # 1. Read the target file content
        target_file_content = target_path_obj.read_text(encoding="utf-8")

        # 2. Build the context bundle from sibling files
        print("  - Building context bundle...")
        pruned_context_bundle = build_pruned_context_bundle(repo_path, target_file_path)

        # 3. Generate Q&A pairs
        qa_json_str = generate_qa_pairs(
            target_file_name=target_file_path,
            target_file_content=target_file_content,
            pruned_context_bundle=pruned_context_bundle,
            prompt_template=prompt_template
        )

        # 4. Save the result to a file
        if qa_json_str:
            new_data = json.loads(qa_json_str)

            # Add filepath field to each entry
            for entry in new_data:
                entry["filepath"] = target_file_path

            # Append new Q&A pairs to the existing data
            existing_data.extend(new_data)

            # Write the updated data back to the file
            with open(output_path, 'w', encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            print(f"  - SUCCESS: Saved Q&A to {output_path.name}")
        else:
            print("  - FAILED: No Q&A data was generated.")

    except FileNotFoundError:
        print(f"!! ERROR: Target file not found at {target_file_path}")
    except Exception as e:
        print(f"!! ERROR: An unexpected error occurred while processing {target_path_obj.name}: {e}")


def enhance_repo_file_qa(repo_path: str, target_file_path: str, prompt_template: str = LIBRARY_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE, rst_path: str = "library-source-code-to-qa.jsonl") -> None:
    """
    Enhances the Q&A generation for a specific file in a repository. 
    The rst_path already have the Q&A pairs of this file, this method will generate more Q&A pairs for this file.
    The prompt template will add the context of existed Q&A pairs to the prompt.
    The rst file will be sorted by the filepath.

    :param repo_path: The root path of the repository.
    :param target_file_path: The absolute path to the target .java file.
    :param prompt_template: The template used to format the prompt for the LLM.
    :param rst_path: The path where the generated Q&A will be saved as a JSON file.
    :return: save the enhanced Q&A pairs to a JSON file.
    """
    target_path_obj = Path(target_file_path)
    output_path = Path(rst_path)

    try:
        # 1. Read existing Q&A pairs
        existing_data = []
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding="utf-8") as f:
                existing_data = json.load(f)

        # Find existing Q&A pairs for the target file
        target_qa_pairs = [entry for entry in existing_data if entry.get("filepath") == target_file_path]
        other_qa_pairs = [entry for entry in existing_data if entry.get("filepath") != target_file_path]
        # 2. Read the target file content
        target_file_content = target_path_obj.read_text(encoding="utf-8")

        # 3. Build the context bundle from sibling files
        print("  - Building context bundle...")
        pruned_context_bundle = build_pruned_context_bundle(repo_path, target_file_path)

        # 4. Add existing Q&A pairs to the prompt template
        if target_qa_pairs:
            existing_qa_context = "\n\n#If exist Q&A pair, you should generate more Q&A pairs that different from the existing ones. \n\n## EXISTING Q&A PAIRS:\n"
            for qa in target_qa_pairs:
                existing_qa_context += f"Q: {qa['query']}\nA: {qa['response']}\n\n"
            prompt_template = prompt_template.replace("# OUTPUT FORMAT", f"{existing_qa_context}# OUTPUT FORMAT")

        # 5. Generate new Q&A pairs
        qa_json_str = generate_qa_pairs(
            target_file_name=target_file_path,
            target_file_content=target_file_content,
            pruned_context_bundle=pruned_context_bundle,
            prompt_template=prompt_template
        )

        # 6. Save the result to a file
        if qa_json_str:
            new_data = json.loads(qa_json_str)

            # Add filepath field to each entry
            for entry in new_data:
                entry["filepath"] = target_file_path

            # Combine other files' Q&A pairs with new Q&A pairs
            combined_data = existing_data + new_data

            # Sort the combined data by filepath
            combined_data.sort(key=lambda x: x["filepath"])

            # Write the updated data back to the file
            with open(output_path, 'w', encoding="utf-8") as f:
                json.dump(combined_data, f, ensure_ascii=False, indent=2)
            print(f"  - SUCCESS: Enhanced Q&A saved to {output_path.name}")
        else:
            print("  - FAILED: No enhanced Q&A data was generated.")

    except FileNotFoundError:
        print(f"!! ERROR: Target file not found at {target_file_path}")
    except Exception as e:
        print(f"!! ERROR: An unexpected error occurred while processing {target_path_obj.name}: {e}")


def repo2qa(repo_path: str, prompt_template: str = LIBRARY_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE, rst_path ="library-source-code-to-qa.jsonl") -> None:
    """
    Traverses a repository, finds all .java files, and generates Q&A pairs for each.
    """
    print(f"Starting Q&A generation for repository: {repo_path}")
    print("=" * 60)

    repo_path_obj = Path(repo_path)
    if not repo_path_obj.is_dir():
        print(f"Error: Provided path '{repo_path}' is not a valid directory.")
        return

    java_files = list(repo_path_obj.rglob("*.java"))
    total_files = len(java_files)
    print(f"Found {total_files} .java files to process.\n")

    for i, file_path in enumerate(java_files):
        relative_path = file_path.relative_to(repo_path_obj)
        print(f"[{i + 1}/{total_files}] Processing: {relative_path}")
        try:
            file2qa(repo_path, str(file_path), prompt_template, rst_path)
        except Exception as e:
            print(f"  !! FATAL ERROR in file2qa for {relative_path}: {e}")
        print("-" * 40)

    print("\n" + "=" * 60)
    print("Repository processing complete.")


if __name__ == "__main__":
    fire.Fire({
        "repo": repo2qa,
        "repo_file_enhance": enhance_repo_file_qa,
        "file": file2qa
    })