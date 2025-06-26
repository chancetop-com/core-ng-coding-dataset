# @author: stephen

import re
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional
from tqdm import tqdm
from .java_parser import JavaParser, JavaParseResult, ClassParseResult, MethodParseResult, FieldParseResult, ImportParseResult


class RepoJavaParser:
    def __init__(self, repo_path: str, reparse: bool = False, output_path: str = None):
        """Initialize repository Java parser.
        
        Args:
            repo_path: Path to the repository
            reparse: Whether to force reparse all files
            output_path: Path to save/load the AST JSON file
        """
        self.repo_path = Path(repo_path)
        if not self.repo_path.exists():
            raise ValueError(f"Repository path {repo_path} does not exist")
            
        self.output_path = output_path or str(self.repo_path / 'ast.json')
        self.result: Dict[str, JavaParseResult] = {}

        self.apps = self._parse_all_apps(repo_path)
        if not reparse and Path(self.output_path).exists():
            self._load()
        else:
            self._parse()

    # noinspection PyMethodMayBeStatic
    def _parse_all_apps(self, repo_path: str) -> list[str]:
        apps = []
        dockerfiles = Path(repo_path).rglob('docker/Dockerfile')

        for path in dockerfiles:
            try:
                with path.open('r', encoding='utf-8') as f:
                    for line in f:
                        match = re.search(r'LABEL\s+app=(\S+)', line)
                        if match:
                            apps.append(match.group(1))
                            break
            except IOError as e:
                print(f"Error reading file {path}: {e}")

        print(f"Found {len(apps)} apps: {apps}")
        return apps

    def _load(self) -> None:
        """Load parsed results from JSON file."""
        print(f"Loading parsed results from {self.output_path}...")

        with open(self.output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"Success loaded: {len(data)} files found")

        for path, file_data in data.items():
            result = JavaParseResult()
            result.path = path
            result.root = file_data['root']
            result.package = file_data['package']
            result.implicit_imports = file_data.get('implicit_imports', [])

            # Rebuild imports
            result.imports = []
            for import_data in file_data['imports']:
                import_result = ImportParseResult()
                import_result.package = import_data['package']
                import_result.class_name = import_data['class_name']
                result.imports.append(import_result)
            
            # Rebuild classes
            result.classes = []
            for class_data in file_data['classes']:
                class_result = ClassParseResult()
                class_result.name = class_data['name']
                class_result.modifiers = class_data['modifiers']
                class_result.type_parameters = class_data.get('type_parameters', [])
                class_result.type = class_data['type']
                class_result.interfaces = class_data.get('interfaces', [])
                class_result.superclass = class_data.get('superclass', None)

                # Rebuild fields
                class_result.fields = []
                for field_data in class_data['fields']:
                    field_result = FieldParseResult()
                    field_result.declarator = field_data['declarator']
                    field_result.type = field_data['type']
                    field_result.modifiers = field_data['modifiers']

                    class_result.fields.append(field_result)
                
                # Rebuild methods
                class_result.methods = {}
                for method_name, method_data in class_data['methods'].items():
                    method_result = MethodParseResult()
                    method_result.name = method_name
                    method_result.parameters = method_data['parameters']
                    method_result.type = method_data['type']
                    method_result.modifiers = method_data['modifiers']
                    method_result.type_parameters = method_data.get('type_parameters', [])
                    method_result.throws = method_data.get('throws', [])
                    
                    class_result.methods[method_name] = method_result
                    
                result.classes.append(class_result)
            
            self.result[path] = result
    
    def _parse(self) -> None:
        """Parse all Java files in the repository."""
        print(f"Parsed ast not found, parsing Java files in {self.repo_path}...")

        java_files = list(self.repo_path.rglob('*.java'))

        for java_file in tqdm(java_files, desc="Parsing Java files", unit="file"):
            parser = JavaParser(str(java_file))
            parser.parse(str(java_file))
            self.result[str(java_file)] = parser.result

        packages_map = defaultdict(list)
        for result in self.result.values():
            if result.package:
                packages_map[result.package].append(result)

        for package_name, results_in_package in packages_map.items():
            self._filter_implicit_imports(results_in_package)

        self._filter_imports()

        # Save results
        with open(self.output_path, 'w', encoding='utf-8') as fd:
            # noinspection PyTypeChecker
            json.dump(self.result, fd, indent=2, ensure_ascii=False, default=lambda o: {
                k: v for k, v in o.__dict__.items() if not k.startswith('_') and k != 'node'
            })
        
        print(f"Total {len(java_files)} Java files parsed and saved to {self.output_path}")


    def _filter_imports(self) -> None:
        packages = {j.package for j in self.result.values() if j.package}
        for result in self.result.values():
            result.imports = [imp for imp in result.imports if imp.package in packages or imp.package.startswith("core.framework")]


    # noinspection PyMethodMayBeStatic
    def _filter_implicit_imports(self, files: list[JavaParseResult]) -> None:
        if len(files) < 2: return
        classes = set()
        for rst in files:
            for c in rst.classes:
                classes.add(c.name)

        for rst in files:
            rst.implicit_imports = [i for i in rst.implicit_imports if i in classes and i not in [c.name for c in rst.classes]]

    def find(self, package: str, class_name: str) -> Optional[JavaParseResult]:
        for result in self.result.values():
            if result.package == package and class_name in [c.name for c in result.classes]:
                return result

        return None

    def find_app_or_module_of_class(self, package: str, class_name: str) -> Optional[JavaParseResult]:
        apps = self.find_references("core.framework.module", "App")
        modules = self.find_references("core.framework.module", "Module")
        for app in apps:
            if app.is_import_class(package, class_name):
                return app
        for module in modules:
            if module.is_import_class(package, class_name):
                return module
        return None

    def find_class_superclass(self, package: str, class_name: str) -> Optional[JavaParseResult]:
        rst = self.find(package, class_name)
        clz = rst.get_superclass_of_class(class_name)
        imp = rst.get_import_by_class_name(clz)
        return self.find(imp.package, imp.class_name) if imp else None

    def find_class_interface(self, package: str, class_name: str) -> Optional[JavaParseResult]:
        rst = self.find(package, class_name)
        clz = rst.get_interface_of_class(class_name)
        imp = rst.get_import_by_class_name(clz)
        return self.find(imp.package, imp.class_name) if imp else None

    def _find_references_by_imports(self, package: str, class_name: str) -> list[JavaParseResult]:
        references = []
        for result in self.result.values():
            for i in result.imports:
                if i.package == package and i.class_name == class_name:
                    references.append(result)
                    break
        return references

    def _find_references_by_implicit_imports(self, package: str, class_name: str) -> list[JavaParseResult]:
        references = []
        for result in self.result.values():
            if result.package == package:
                if class_name in result.implicit_imports:
                    references.append(result)
        return references

    def find_references(self, package: str, class_name: str) -> list[JavaParseResult]:
        return (self._find_references_by_imports(package, class_name) +
                self._find_references_by_implicit_imports(package, class_name))