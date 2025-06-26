# @author: stephen

import fire
import litellm
import json
import os
import textwrap
from pathlib import Path
from token_cost_counter import count_cost
from library.action_trace import ActionTraces, RecentActions
from library.repo_java_parser import RepoJavaParser
from repo_action_java_parser import fetch_action_context
from typing import Optional

EXAMPLE_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE = textwrap.dedent("""
# ROLE:
You are a Senior Engineer and a technical authority on our internal Java framework, core-ng. Your expertise lies in writing high-quality, production-ready code and mentoring other developers on how to implement features effectively using the framework.

# CONTEXT:
You will be provided with a `RELEVANT_SOURCE_CODES`, which includes all the necessary Java files (controllers, services, interfaces, DTOs, etc.) for a complete, working feature. You will also receive an `ACTION_TRACE` for this feature, which is a dependency trace of a feature's action.

# TASK:
Your task is to create a detailed, step-by-step tutorial in a question-and-answer format based on the provided code. This tutorial will be used to fine-tune a large language model to help developers write code for new features using core-ng. You should generate **5** plus comprehensive Q&A pairs.

# CRITERIA FOR EACH PAIR:
- The **Question** should be a practical, "how-to" question about implementing a specific type of feature. For example, "How do I implement an API to search for records and return a paginated list?". The question should be general enough to be reusable but specific enough to be useful.
- The **Answer** must be a detailed, step-by-step guide that walks a developer through the implementation process. It must:
    1.  Provide a high-level overview of the implementation steps.
    2.  For each step, clearly state the goal (e.g., "Define the API endpoint," "Implement the business logic").
    3.  Identify the specific file(s) to be created or modified for that step (e.g., `ProductController.java`, `ProductService.java`).
    4.  Include the relevant Java code snippet from the provided files as a concrete example for that step.
    5.  Explain *why* the code is structured that way, referencing core-ng conventions.

# ===============================================
# INPUTS
# ===============================================

## ACTION_TRACE:
{ACTION_TRACE}

## RELEVANT_SOURCE_CODES:
(Contains all direct relevant files in the project)
{RELEVANT_SOURCE_CODES}

# ===============================================
# OUTPUT FORMAT
# ===============================================
You MUST provide the output in a single, valid JSON block. The root element must be a JSON array of objects.

[
  {{
    "query": "How do I implement an API to get a resource by its ID, and handle cases where the resource is not found?",
    "response": "To implement an API to fetch a resource by its ID, you should follow these steps, which separate concerns between the controller, service, and repository layers.\\n\\n**Step 1: Define the API Endpoint in the Controller**\\nFirst, define the endpoint in your controller class. Use `@Path` to specify the URL and `@PathParam` to capture the ID from the path. This method will delegate the core logic to the service layer.\\n*File: `{{CONTROLLER_FILE_NAME}}`*\\n```java\\n@Path(\\"/product/:id\\")\\n@GET\\npublic GetProductResponse get(@PathParam(\\"id\\") String id) {{\\n    return productService.get(id);\\n}}\\n```\\n\\n**Step 2: Implement the Business Logic in the Service**\\nNext, in the service layer, implement the `get` method. This method is responsible for fetching the data. If the resource doesn't exist, it should throw a business-specific exception, like `NotFoundException`, to be handled by the framework's exception handler. This keeps the controller clean.\\n*File: `{{SERVICE_FILE_NAME}}`*\\n```java\\npublic GetProductResponse get(String id) {{\\n    Product product = repository.get(id).orElseThrow(() -> new NotFoundException(\\"product not found, id=\\" + id));\\n    GetProductResponse response = new GetProductResponse();\\n    response.id = product.id;\\n    response.name = product.name;\\n    response.description = product.description;\\n    return response;\\n}}\\n```\\n\\n**Step 3: Define the Data Transfer Objects (DTOs)**\\nCreate request and response objects (DTOs) to define the API's contract. This ensures a stable interface and decouples your API from your internal domain models.\\n*File: `{{RESPONSE_DTO_FILE_NAME}}`*\\n```java\\npublic class GetProductResponse {{\\n    @NotNull\\n    @Property(name = \\"id\\")\\n    public String id;\\n\\n    @NotNull\\n    @Property(name = \\"name\\")\\n    public String name;\\n\\n    @Property(name = \\"description\\")\\n    public String description;\\n}}\\n```"
  }},
  {{
    "query": "...",
    "response": "..."
  }}
]
""")


LITELLM_MODEL = "azure/gpt-4o"

def generate_qa_pairs(action_trace: str, relevant_source_codes: str) -> Optional[str]:
    """
    Generates Q&A pairs for a target file using an LLM.

    Args:
        action_trace: A string containing the action trace for the action.
        relevant_source_codes: A string containing the source code of dependency files.

    Returns:
        A string containing a JSON array of Q&A pairs, or None if an error occurs.
    """
    print(f"  - Generating Q&A with model: {LITELLM_MODEL}")
    prompt = EXAMPLE_SOURCE_CODE_TO_QA_PROMPT_TEMPLATE.format(
        RELEVANT_SOURCE_CODES=relevant_source_codes,
        ACTION_TRACE=action_trace
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


def build_relevant_source_codes(repo_parser: RepoJavaParser, action: str) -> str:
    files = fetch_action_context(action, repo_parser, level=1)
    rst = "Relevant files for action: " + action + "\n\n"
    for file_path in files:
        rst += f"### {file_path}\n"
        try:
            file_content = Path(file_path).read_text(encoding="utf-8")
            rst += file_content + "\n\n"
        except FileNotFoundError:
            print(f"!! ERROR: File {file_path} not found in the repository.")
            continue
    return rst


def action2qa(repo_path: str, action: str, repo_parser: RepoJavaParser = None, rst_path: str = "example-repo-action-to-qa.jsonl") -> None:
    if not repo_parser:
        repo_parser = RepoJavaParser(repo_path)

    output_path = Path(rst_path)

    # Check if the file has already been processed
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding="utf-8") as f:
            existing_data = json.load(f)
        processed_actions = {entry.get("action") for entry in existing_data}
        if action in processed_actions:
            print(f"  - SKIPPED: {action} is already processed.")
            return
    else:
        existing_data = []

    try:
        # 1. get action traces
        traces = ActionTraces(action)
        action_trace = str(traces)

        # 2. Build the relevant_source_codes
        print("  - Building relevant_source_codes...")
        relevant_source_codes = build_relevant_source_codes(repo_parser, action)

        # 3. Generate Q&A pairs
        qa_json_str = generate_qa_pairs(
            action_trace=action_trace,
            relevant_source_codes=relevant_source_codes
        )

        # 4. Save the result to a file
        if qa_json_str:
            new_data = json.loads(qa_json_str)

            # Add filepath field to each entry
            for entry in new_data:
                entry["action"] = action
                entry["app"] = traces.get_root_doc().app

            # Append new Q&A pairs to the existing data
            existing_data.extend(new_data)

            # Write the updated data back to the file
            with open(output_path, 'w', encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            print(f"  - SUCCESS: Saved Q&A to {output_path.name}")
        else:
            print("  - FAILED: No Q&A data was generated.")

    except Exception as e:
        print(f"!! ERROR: An unexpected error occurred while processing {action}: {e}")




def repo2qa(repo_path: str, size: int = 100, rst_path ="example-repo-action-to-qa.jsonl") -> None:
    """
    Traverses a repository, finds all .java files, and generates Q&A pairs for each.
    """
    print(f"Starting Q&A generation for repository: {repo_path}")
    print("=" * 60)

    parser = RepoJavaParser(repo_path)
    actions = RecentActions(size, path="recent_actions.json")

    print(f"Found {len(actions.actions)} actions to process.\n")

    for i, action in enumerate(actions.actions):
        print(f"[{i + 1}/{len(actions.actions)}] Processing: {action}")
        try:
            action2qa(repo_path, action.action, parser, rst_path=rst_path)
        except Exception as e:
            print(f"  !! FATAL ERROR in action2qa for {action}: {e}")
        print("-" * 40)

    print("\n" + "=" * 60)
    print("Repository processing complete.")



if __name__ == "__main__":
    fire.Fire({
        "action": action2qa,
        "repo": repo2qa
    })