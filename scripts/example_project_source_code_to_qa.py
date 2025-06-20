# @author: stephen

import fire
import textwrap
from repo2qa import repo2qa, file2qa

EXAMPLE_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE = textwrap.dedent("""
# ROLE:
You are a Senior Engineer and a technical authority on applying our internal Java framework named - core-ng. You are an expert at reviewing code and identifying best practices, design patterns, and idiomatic usage of the framework in real-world applications.

# CONTEXT:
You will be provided with a `PRUNED_CONTEXT_BUNDLE`, containing the API signatures of all relevant files for a specific feature module from a real project. You will also receive a `TARGET_FILE` from that module, which is considered a "gold-standard" example of framework usage. Your goal is to abstract the general principles and best practices demonstrated in the `TARGET_FILE`.

# TASK:
Analyze the `TARGET_FILE`'s code within the context of the `PRUNED_CONTEXT_BUNDLE`. Generate a list of **2 to 4** question-and-answer pairs that teach a general best practice or application pattern, using the `TARGET_FILE` as a concrete example.

# CRITERIA FOR EACH PAIR:
- The **Question** must be a general, "how-to" or "what-is-the-best-way-to" question about a common development task. It should not mention the specific file names.
- The **Answer** must first state the general principle or best practice clearly. Then, it must reference the `TARGET_FILE`'s code as a concrete illustration of that principle in action, explaining why the code is a good example.
- The generated pairs should highlight different best practices (e.g., dependency injection, transaction management, state handling, etc.).

# ===============================================
# INPUTS
# ===============================================

## PRUNED_CONTEXT_BUNDLE:
(Contains API signatures & docstrings of all dependency files in the project module)
{PRUNED_CONTEXT_BUNDLE}

## TARGET_FILE_NAME:
(The name of the exemplary file to focus on)
{TARGET_FILE_NAME}

## TARGET_FILE_CONTENT:
(The full, original source code of the exemplary file)
{TARGET_FILE_CONTENT}

# ===============================================
# OUTPUT FORMAT
# ===============================================
You MUST provide the output in a single, valid JSON block. The root element must be a JSON array of objects.

[
  {{
    "query": "What is the recommended way to handle business-specific exceptions within our framework?",
    "response": "The best practice is to create custom, checked exceptions for specific business error conditions and handle them gracefully in the controller layer to produce clean API responses. For instance, in `{{TARGET_FILE_NAME}}`, you can see a `ProductNotFoundException` being thrown from the service layer. The controller catches this specific exception and maps it to a 404 Not Found HTTP response, rather than letting a generic 500 error bubble up. This makes the API robust and predictable."
  }},
  {{
    "query": "...",
    "response": "..."
  }}
]
""")

def example_file_qa(repo_path: str, target_file_path: str) -> None:
    file2qa(repo_path, target_file_path, EXAMPLE_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE, "example-source-code-to-qa.jsonl")

def example_repo_qa(repo_path: str) -> None:
    repo2qa(repo_path, EXAMPLE_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE, "example-source-code-to-qa.jsonl")


if __name__ == "__main__":
    fire.Fire({
        "repo": example_repo_qa,
        "file": example_file_qa
    })