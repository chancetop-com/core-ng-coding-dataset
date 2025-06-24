# @author: stephen

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch


class ActionDocumentContextController:
    def __init__(self, controller: str):
        self.controller = controller

    def get_package(self) -> Optional[str]:
        if not self.controller:
            return None
        splits = self.controller.split(".")[:-2]
        return ".".join(splits)

    def get_class_name(self) -> Optional[str]:
        if not self.controller:
            return None
        return self.controller.split(".")[-2]

    def get_method_name(self) -> Optional[str]:
        if not self.controller:
            return None
        return self.controller.split(".")[-1]


class ActionDocument:
    def __init__(self, source_doc: Dict[str, Any]):
        timestamp_str = source_doc.get("@timestamp")
        self.timestamp: Optional[datetime] = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')) if timestamp_str else None

        self.id: Optional[str] = source_doc.get("id")
        self.app: Optional[str] = source_doc.get("app")
        self.host: Optional[str] = source_doc.get("host")
        self.result: Optional[str] = source_doc.get("result")
        
        self.ref_ids: List[str] = source_doc.get("ref_id", [])
        self.correlation_ids: List[str] = source_doc.get("correlation_id", [])
        self.clients: List[str] = source_doc.get("client", [])
        
        self.action: Optional[str] = source_doc.get("action")
        self.error_code: Optional[str] = source_doc.get("error_code")
        self.error_message: Optional[str] = source_doc.get("error_message")
        self.elapsed: Optional[int] = source_doc.get("elapsed")

        self.context: Dict[str, List[str]] = source_doc.get("context", {})
        self.stats: Dict[str, float] = source_doc.get("stats", {})
        self.performance_stats: Dict[str, Any] = source_doc.get("perf_stats", {})

    def get_context_controller(self) -> ActionDocumentContextController:
        controller = self.context.get("controller", [])
        if not controller:
            return ActionDocumentContextController("")
        return ActionDocumentContextController(controller[0])


    def __repr__(self) -> str:
        return f"ActionDocument(id={self.id}, action={self.action})"


class ActionTraces:
    def __init__(self, action: str, elastic_url: Optional[str] = None, index: str = "action-*"):
        self.action = action
        self.elastic_url = elastic_url or os.environ.get("ELASTIC_URL")
        self.index = index
        self.docs = self._fetch_all_docs()

    def _connect(self):
        if not self.elastic_url:
            raise ValueError("ELASTIC_URL environment variable is not set")
        return Elasticsearch(self.elastic_url)

    def _fetch_action_document(self) -> Optional[ActionDocument]:
        es = self._connect()
        query = {
            "query": {
                "match": {
                    "action": self.action
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ],
            "size": 1
        }
        result = es.search(index=self.index, body=query)
        if result["hits"]["total"]["value"] > 0:
            return ActionDocument(result["hits"]["hits"][0]["_source"])
        return None

    def _fetch_correlation_documents(self, correlation_id: List[str]) -> List[ActionDocument]:
        es = self._connect()
        query = {
            "query": {
                "terms": {
                    "correlation_id": correlation_id
                }
            },
            "sort": [
                {"@timestamp": {"order": "asc"}}
            ],
            "size": 1000
        }
        result = es.search(index=self.index, body=query)
        return [ActionDocument(hit["_source"]) for hit in result["hits"]["hits"]]

    def _fetch_all_docs(self) -> List[ActionDocument]:
        root_doc = self._fetch_action_document()
        if not root_doc:
            print(f"No document found for action: {self.action}")
            return []
        
        correlation_ids = root_doc.correlation_ids
        if not correlation_ids:
            print(f"No correlation_id found in document for action: {self.action}")
            return [root_doc]
        
        related_docs = self._fetch_correlation_documents(correlation_ids)
        all_docs = [root_doc] + related_docs
        return [doc for doc in all_docs if doc.context.get("controller")]

    def get_root_doc(self) -> Optional[ActionDocument]:
        for doc in self.docs:
            if doc.ref_ids is None or doc.ref_ids == []:
                return doc
        return None

    def print_traces(self):
        if not self.docs:
            return

        root_doc = self.get_root_doc()
        if not root_doc:
            return

        children_map: Dict[str, List[ActionDocument]] = {doc.id: [] for doc in self.docs}
        
        for doc in self.docs:
            for parent_id in doc.ref_ids:
                if parent_id in children_map:
                    children_map[parent_id].append(doc)
        
        def print_tree(node: ActionDocument, level: int = 0):
            prefix = "    " * level
            if level > 0:
                prefix += "└── "
                
            controller = node.context.get("controller")
            controller_str = ", ".join(controller)
            print(f"{prefix}app: {node.app}, action: {node.action}, controller: {controller_str}")

            children = children_map.get(node.id, [])
            for child in children:
                print_tree(child, level + 1)

        print(f"--- Call Chain Starting from action: {self.action} ---")
        print_tree(root_doc)