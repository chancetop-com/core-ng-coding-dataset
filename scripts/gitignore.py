import os
from typing import Tuple, Iterator, List, Optional

try:
    from gitignore_parser import parse_gitignore, IgnoreRule
except ImportError:
    print("Warning: 'gitignore-parser' not found. To use .gitignore files, please install it:")
    print("pip install gitignore-parser")
    parse_gitignore = None
    IgnoreRule = None

class GitignoreMatcher:
    """
    A class to determine whether a file or directory should be ignored based on .gitignore rules or default directory list.
    """
    def __init__(self, repo_path: str, default_skip_dirs: Tuple[str, ...] = (
        '.git', '.venv', 'venv', 'env', 'node_modules', '__pycache__',
        'dist', 'build', '.vscode', '.idea', 'target', 'coverage'
    )):
        """
        Initialize the matcher by preparing .gitignore rules or fallback solution.

        :param repo_path: Absolute path to the repository.
        :param default_skip_dirs: Tuple of directory names to skip if not using .gitignore.
        """
        self.repo_path = repo_path
        self.default_skip_dirs = default_skip_dirs
        self.matcher: Optional[callable] = None
        self.use_gitignore_parser = False

        gitignore_path = os.path.join(self.repo_path, '.gitignore')
        has_gitignore_file = os.path.exists(gitignore_path)

        if has_gitignore_file and parse_gitignore:
            print("  - Using exclusion rules from: .gitignore")
            self.matcher = parse_gitignore(gitignore_path, base_dir=self.repo_path)
            self.use_gitignore_parser = True
        else:
            if has_gitignore_file and not parse_gitignore:
                print("  - Warning: Found .gitignore but 'gitignore-parser' is not installed. Falling back to defaults.")
            else:
                print("  - .gitignore not found. Using default skip list.")
            print(f"  - Skipping directories: {list(self.default_skip_dirs)}")

    def ignore(self, path: str) -> bool:
        """
        Check whether the given path should be ignored.

        :param path: Absolute path to file or directory.
        :return: True if the path should be ignored, False otherwise.
        """
        if self.use_gitignore_parser and self.matcher:
            return self.matcher(path)

        # Fallback logic when not using gitignore parser
        relative_path = os.path.relpath(path, self.repo_path)
        # On Windows, relpath might use backslashes
        parts = relative_path.split(os.sep)
        # Check if any part of the path is in default skip list
        return any(part in self.default_skip_dirs for part in parts)

    def walk(self) -> Iterator[Tuple[str, List[str], List[str]]]:
        """
        Walk through the repository, yielding (root, dirs, files) for non-ignored paths.
        This is a generator method that internally handles the ignore logic for directories and files.
        """
        for root, dirs, files in os.walk(self.repo_path, topdown=True):
            # Always remove .git directory from traversal
            if '.git' in dirs:
                dirs.remove('.git')

            # Prune directory list in-place for efficiency based on ignore logic
            dirs[:] = [d for d in dirs if not self.ignore(os.path.join(root, d))]

            # Similarly filter the files list
            files[:] = [f for f in files if not self.ignore(os.path.join(root, f))]

            yield root, dirs, files