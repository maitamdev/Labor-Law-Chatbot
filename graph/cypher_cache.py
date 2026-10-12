"""
In-memory LRU Cache for Neo4j Cypher query results.
"""
import collections
from typing import Any, Optional

class CypherQueryCache:
    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self.cache: collections.OrderedDict[str, Any] = collections.OrderedDict()

    def get(self, query: str) -> Optional[Any]:
        if query not in self.cache:
            return None
        self.cache.move_to_end(query)
        return self.cache[query]

    def put(self, query: str, result: Any) -> None:
        if query in self.cache:
            self.cache.move_to_end(query)
        self.cache[query] = result
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        self.cache.clear()
