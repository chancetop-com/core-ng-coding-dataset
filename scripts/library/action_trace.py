# @author: stephen

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch


class ActionDocumentContextHandler:
    def __init__(self, handler: str):
        self.handler = handler

    def get_package(self) -> Optional[str]:
        if not self.handler:
            return None
        splits = self.handler.split(".")[:-1]
        return ".".join(splits)

    def get_class_name(self) -> Optional[str]:
        if not self.handler:
            return None
        return self.handler.split(".")[-1]


class ActionDocumentContextJobClass:
    def __init__(self, job_class: str):
        self.job_class = job_class

    def get_package(self) -> Optional[str]:
        if not self.job_class:
            return None
        splits = self.job_class.split(".")[:-1]
        return ".".join(splits)

    def get_class_name(self) -> Optional[str]:
        if not self.job_class:
            return None
        return self.job_class.split(".")[-1]


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

    def get_context_job_class(self) -> ActionDocumentContextJobClass:
        job_class = self.context.get("job_class", [])
        if not job_class:
            return ActionDocumentContextJobClass("")
        return ActionDocumentContextJobClass(job_class[0])

    def get_context_handler(self) -> ActionDocumentContextHandler:
        handler = self.context.get("handler", [])
        if not handler:
            return ActionDocumentContextHandler("")
        return ActionDocumentContextHandler(handler[0])


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
        # remove duplicates based on app and action
        seen = set()
        unique_docs = []
        for doc in all_docs:
            identifier = (doc.app, doc.action)
            if identifier not in seen and (doc.get_context_controller().controller
                                           or doc.get_context_job_class().job_class
                                           or doc.get_context_handler()):
                seen.add(identifier)
                unique_docs.append(doc)
        return unique_docs

    def get_root_doc(self) -> Optional[ActionDocument]:
        for doc in self.docs:
            if doc.ref_ids is None or doc.ref_ids == []:
                return doc
        return None

    def walk(self, level: Optional[int] = None):
        if not self.docs:
            return

        root_doc = self.get_root_doc()
        if not root_doc:
            return

        # Filter out docs with no ID to prevent errors and build the children map
        docs_with_id = [doc for doc in self.docs if doc.id is not None]
        children_map: Dict[str, List[ActionDocument]] = {doc.id: [] for doc in docs_with_id}
        for doc in docs_with_id:
            for parent_id in doc.ref_ids:
                if parent_id in children_map:
                    children_map[parent_id].append(doc)

        # Sort children by timestamp for deterministic, chronological traversal
        for parent_id in children_map:
            # Handle cases where timestamp might be None
            children_map[parent_id].sort(key=lambda d: d.timestamp or datetime.min)

        # Use a set to track nodes in the current recursion path for cycle detection
        def dfs(node: ActionDocument, current_level: int, recursion_stack: set):
            # Cycle detection: if node.id is already in the current path, we have a cycle.
            if node.id is not None and node.id in recursion_stack:
                return

            yield node

            # Stop traversal if the specified level is reached
            if level is not None and current_level >= level:
                return

            if node.id is not None:
                recursion_stack.add(node.id)

            for child in children_map.get(node.id, []):
                yield from dfs(child, current_level + 1, recursion_stack)

            if node.id is not None:
                recursion_stack.remove(node.id)

        # Start the traversal from the root at level 0
        yield from dfs(root_doc, 0, set())

    def __repr__(self) -> str:
        if not self.docs:
            return f"ActionTraces(action='{self.action}', status='No documents found')"

        root_doc = self.get_root_doc()
        if not root_doc:
            return f"ActionTraces(action='{self.action}', status='No root document found')"

        # Filter out docs with no ID to prevent errors and build the children map
        docs_with_id = [doc for doc in self.docs if doc.id is not None]
        children_map: Dict[str, List[ActionDocument]] = {doc.id: [] for doc in docs_with_id}
        for doc in docs_with_id:
            for parent_id in doc.ref_ids:
                if parent_id in children_map:
                    children_map[parent_id].append(doc)

        # Sort children by timestamp for deterministic, chronological traversal
        for parent_id in children_map:
            children_map[parent_id].sort(key=lambda d: d.timestamp or datetime.min)

        output_lines = []

        def build_tree_string(node: ActionDocument, level: int = 0):
            prefix = "    " * level
            if level > 0:
                prefix = "    " * (level - 1) + "└── "

            context_parts = []
            controller = node.get_context_controller()
            if controller.controller:
                context_parts.append(f"controller: {controller.controller}")

            job_class = node.get_context_job_class()
            if job_class.job_class:
                context_parts.append(f"job_class: {job_class.job_class}")

            handler = node.get_context_handler()
            if handler.handler:
                context_parts.append(f"handler: {handler.handler}")

            context_str = ", ".join(context_parts)

            output_lines.append(f"{prefix}app: {node.app}, action: {node.action}, {context_str}")

            children = children_map.get(node.id, [])
            for child in children:
                build_tree_string(child, level + 1)

        output_lines.append(f"--- Call Chain Starting from action: {self.action} ---")
        build_tree_string(root_doc)

        return "\n".join(output_lines)


class RecentActionResult:
    def __init__(self, action: str, count: int):
        self.action = action
        self.count = count

    def __repr__(self) -> str:
        return "{action: " + self.action + ", count: " + str(self.count) + "}"


class RecentActions:
    def __init__(self, size: int = 10, days: int = 30, path: Optional[str] = None):
        self.size = size
        self.days = days
        self.elastic_url = os.environ.get("ELASTIC_URL")
        if not self.elastic_url:
            raise ValueError("ELASTIC_URL environment variable is not set")
        self.es = Elasticsearch(self.elastic_url)
        self.index = "action-*"
        if path and os.path.exists(path):
            self.actions = self.load(path)
            return
        self.actions = self.fetch()
        if path:
            self.save(path)

    def save(self, path: str):
        if not self.actions:
            print("No recent actions to save.")
            return

        print(f"Saving recent actions to {path}...")
        with open(path, 'w', encoding='utf-8') as f:
            actions_list = [vars(action) for action in self.actions]
            rst = {"actions": actions_list}
            # noinspection PyTypeChecker
            json.dump(rst, f, indent=4, ensure_ascii=False)

    # noinspection PyMethodMayBeStatic
    def load(self, path: str) -> List[RecentActionResult]:
        if not os.path.exists(path):
            print(f"File {path} does not exist.")
            return []

        print(f"Loading recent actions from {path}...")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "actions" in data:
                actions_list = [RecentActionResult(**action) for action in data["actions"]]
                return sorted(actions_list, key=lambda x: x.count, reverse=True)
            else:
                return []

    def fetch(self) -> List[RecentActionResult]:
        now = datetime.now()
        start = now - timedelta(days=self.days)

        action_prefixes = ["api:", "http:", "job:", "sse:", "ws:", "topic:"]
        should_clauses = [{"prefix": {"action": p}} for p in action_prefixes]

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [{
                            "range": {
                                "@timestamp": {
                                    "gte": start.isoformat() + "Z",
                                    "lte": now.isoformat() + "Z"
                                }
                            }
                        }
                    ],
                    "filter": [{
                            "bool": {
                                "should": should_clauses,
                                "minimum_should_match": 1,
                                "must_not": [{
                                    "terms": {
                                            "action": ["http:get:/:all(*)", "http:get:/_sys/api",  "http:options:/event/:app"]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "top_actions": {
                    "terms": {
                        "field": "action",
                        "size": self.size
                    }
                }
            }
        }
        result = self.es.search(index=self.index, body=query)
        buckets = result["aggregations"]["top_actions"]["buckets"]
        return [RecentActionResult(b["key"], b["doc_count"]) for b in buckets]

    def print_recent_actions(self):
        print(f"Recent top {self.size} actions in the last {self.days} days:")
        for action in self.actions:
            print(f"Action: {action.action}, Count: {action.count}")