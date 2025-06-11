import os
import fire
import tree_sitter_java as tsj
from tqdm import tqdm
from tree_sitter import Language, Parser, Node
from gitignore import GitignoreMatcher

try:
    from gitignore_parser import parse_gitignore
except ImportError:
    print("Warning: 'gitignore-parser' not found. To use .gitignore files, please install it:")
    print("pip install gitignore-parser")
    parse_gitignore = None

class ClassParseResult:
    def __init__(self):
        self.name: str = ""
        self.type: str = ""
        self.methods: list[str] = []
        self.fields: list[str] = []

    def __repr__(self):
        return f"Class(name='{self.name}', fields={len(self.fields)}, methods={len(self.methods)})"

class JavaParseResult:
    def __init__(self):
        self.path: str = ""
        self.package: str = ""
        self.root: str = ""
        self.imports: list[str] = []
        self.classes: list[ClassParseResult] = []

    def __repr__(self):
        return (f"JavaFile(path='{self.path}', package='{self.package}', "
                f"imports={len(self.imports)}, classes={self.classes})")


class JavaParser:
    def __init__(self):
        self.result = None
        self.parser = Parser(Language(tsj.language()))

    def parse(self, path: str) -> JavaParseResult:
        self.result = JavaParseResult()
        self.result.path = path

        try:
            with open(path, "rb") as file:
                source_bytes = file.read()
        except FileNotFoundError:
            print(f"Error: File not found at {path}")
            return self.result # Return empty result
        except Exception as e:
            print(f"Error reading file: {e}")
            return self.result

        tree = self.parser.parse(source_bytes)
        root_node = tree.root_node

        self._traverse_tree(root_node, self.result)
        return self.result

    def _traverse_tree(self, node: Node, rst: JavaParseResult, current_class: ClassParseResult = None):
        if node.type == "package_declaration":
            # Capture package name
            package_name_node = node.named_children[0]
            if package_name_node:
                rst.package = package_name_node.text.decode('utf-8')

        elif node.type == "import_declaration":
            # Capture import statements
            import_text = node.text.decode('utf-8')
            rst.imports.append(import_text)

        elif node.type == "class_declaration" or node.type == "interface_declaration":
            new_class = ClassParseResult()
            name_node = node.child_by_field_name('name')
            if name_node:
                new_class.name = name_node.text.decode('utf-8')
                new_class.type = node.type
            rst.classes.append(new_class)
            if not current_class:
                rst.root = new_class.name
            # For children of this class, the context is the new class
            for child in node.children:
                self._traverse_tree(child, rst, current_class=new_class)
            return # Return to prevent traversing children again

        elif node.type == "field_declaration":
            if current_class: # Ensure we are inside a class
                field_text = node.text.decode('utf-8').strip()
                current_class.fields.append(field_text)

        elif node.type == "method_declaration":
            if current_class: # Ensure we are inside a class
                # Get just the method signature, not the whole body
                method_body_node = node.child_by_field_name('body')
                if method_body_node:
                    method_text = node.text.decode('utf-8')[:node.text.find(method_body_node.text)].strip()
                    current_class.methods.append(method_text)
                else:
                    current_class.methods.append(node.text.decode('utf-8').strip())

        # Continue traversal for other nodes
        for child in node.children:
            self._traverse_tree(child, rst, current_class)


def declarations(path: str) -> None:
    """Prints all parsed class, field, and method declarations."""
    parser = JavaParser()
    result = parser.parse(path)
    if not result.classes:
        print(f"No classes found in {path}")
        return

    print(f"Parsed Declarations for: {result.path}")
    print(f"\nPackage: {result.package or 'Not specified'}")
    print(f"\nRoot: {result.root or 'Not specified'}")
    for cls in result.classes:
        print(f"\n--- {cls.type.replace("_declaration", "")}: {cls.name} ---")
        if cls.fields:
            print("  Fields:")
            for field in cls.fields:
                print(f"    - {field}")
        if cls.methods:
            print("  Methods:")
            for method in cls.methods:
                print(f"    - {method}")

def references(path: str) -> None:
    """Prints all parsed package and import references."""
    parser = JavaParser()
    result = parser.parse(path)
    print(f"Parsed References for: {result.path}")
    print(f"\nPackage: {result.package or 'Not specified'}")
    
    if result.imports:
        print("\nImports:")
        for imp in result.imports:
            print(f"  - {imp}")


def resolve(repo_path: str, class_path: str, prefix_level: int = 2) -> None:
    """
    Parses a Java class, finds all imported classes that share a common package
    prefix (indicating they are in the same repo), and prints their declarations.
    
    Args:
        repo_path: The absolute or relative path to the repository's root directory.
        class_path: The path to the starting Java class file.
        prefix_level: The number of package segments to use for matching (default: 2).
                      e.g., for 'com.mycompany.app', level 2 matches 'com.mycompany'.
    """
    print(f"Starting analysis for: {class_path} in repo: {repo_path}")
    parser = JavaParser()
    main_class_result = parser.parse(class_path)

    if not main_class_result.package:
        print("\nError: Could not determine the package of the initial class. Cannot resolve imports by prefix.")
        return
        
    if not main_class_result.imports:
        print("\nNo import statements found in the initial class.")
        return

    # Determine the base package prefix for comparison.
    base_package_parts = main_class_result.package.split('.')
    # Handle cases where package has fewer parts than the desired level.
    actual_level = min(len(base_package_parts), prefix_level)
    base_prefix = ".".join(base_package_parts[:actual_level])
    
    print(f"Using base package prefix '{base_prefix}' (from package '{main_class_result.package}' with level {prefix_level}) to identify in-repo classes.")

    target_imports = [
        imp.replace("import", "").strip().replace(";", "")
        for imp in main_class_result.imports
        if imp.replace("import", "").strip().startswith(base_prefix)
    ]

    if not target_imports:
        print("\nNo in-repo imports matching the prefix were found.")
        return

    print(f"\nFound {len(target_imports)} potential in-repo imports. Now searching for files...")

    files_to_process = set()
    abs_repo_path = os.path.abspath(repo_path)
    matcher = GitignoreMatcher(abs_repo_path)

        # Walk the directory tree just once.
    for root, _, files in tqdm(matcher.walk(), desc="Scanning directories", unit="dir", ncols=100):
        for file_name in files:
            if not file_name.endswith(".java"):
                continue
            
            full_path = os.path.join(root, file_name)
            
            # Check the current file against our list of target imports.
            for imp in target_imports:
                match = False
                is_wildcard = imp.endswith(".*")
                
                # Use normalized paths for reliable, cross-platform checks.
                normalized_full_path = full_path.replace(os.sep, '/')
                
                if is_wildcard:
                    # Match directory path for wildcard imports (e.g., com.example.utils.*)
                    target_dir = imp[:-2].replace('.', '/')
                    normalized_file_dir = os.path.dirname(normalized_full_path)
                    if normalized_file_dir.endswith(target_dir):
                        match = True
                else:
                    # Match exact file path for specific imports (e.g., com.example.MyClass)
                    target_file = imp.replace('.', '/') + ".java"
                    if normalized_full_path.endswith(target_file):
                        match = True

                if match:
                    files_to_process.add(full_path)
                    # Once a file is matched, we can stop checking it against other imports
                    # and move to the next file in the directory.
                    break 
    
    # Exclude the starting file itself from being re-printed.
    abs_class_path = os.path.abspath(class_path)
    files_to_process.discard(abs_class_path)

    if not files_to_process:
        print(" -> No corresponding files found in the repo for the filtered imports.")
        return

    sorted_files = sorted(list(files_to_process))

    print(f"\nFound {len(sorted_files)} unique, relevant files. Now parsing declarations...")

    for path in sorted_files:
        declarations(path)


if __name__ == "__main__":
    fire.Fire({
        "resolve": resolve,
        "references": references,
        "declarations": declarations
    })