# @author: stephen

import json
from pathlib import Path
from typing import Dict, Optional
from tqdm import tqdm
from .java_parser import JavaParser, JavaParseResult, ClassParseResult, MethodParseResult, import_to_package_and_class_name


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
        
        if not reparse and Path(self.output_path).exists():
            self._load()
        else:
            self._parse()
    
    def _load(self) -> None:
        """Load parsed results from JSON file."""
        with open(self.output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for path, file_data in data.items():
            result = JavaParseResult()
            result.path = path
            result.package = file_data['package']
            result.imports = file_data['imports']
            
            # Rebuild classes
            result.classes = []
            for class_data in file_data['classes']:
                class_result = ClassParseResult()
                class_result.name = class_data['name']
                class_result.type = class_data['type']
                class_result.fields = class_data['fields']
                
                # Rebuild methods
                class_result.methods = {}
                for method_name, method_data in class_data['methods'].items():
                    method_result = MethodParseResult()
                    method_result.body = method_data['body']
                    
                    # Rebuild signature
                    signature = SignatureParseResult()
                    signature.params = method_data['signature']['params']
                    signature.return_type = method_data['signature']['return_type']
                    method_result.signature = signature
                    
                    class_result.methods[method_name] = method_result
                    
                result.classes.append(class_result)
            
            self.result[path] = result
    
    def _parse(self) -> None:
        """Parse all Java files in the repository."""
        java_files = list(self.repo_path.rglob('*.java'))
        
        for java_file in tqdm(java_files, desc="Parsing Java files", unit="file"):
            parser = JavaParser(str(java_file))
            result = parser.parse(str(java_file))
            self.result[str(java_file)] = result
            
        # Save results
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.result, f, indent=2, ensure_ascii=False,
                     default=lambda o: {k: v for k, v in o.__dict__.items()
                                      if not k.startswith('_') and k != 'node'})
        
        print(f"Total {len(java_files)} Java files parsed and saved to {self.output_path}")


    def find(self, package: str, class_name: str) -> Optional[JavaParseResult]:
        for result in self.result.values():
            if result.package == package and class_name in [c.name for c in result.classes]:
                return result

        return None

    def find_references(self, path: str) -> list[ClassParseResult]:
        result = self.result.get(path)
        if not result:
            return None
        refers = [import_to_package_and_class_name(i) for i in result.imports]
        rst = [self.find(refer[0], refer[1]) for refer in refers]
        return [r for r in rst if r is not None]