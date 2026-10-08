# -*- coding: utf-8 -*-
"""
VietLabor AI - Neo4j Connector
Provides robust, thread-safe database connection management for Neo4j.
Features automated health-checks, graceful offline fallbacks, and connection pooling.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config.settings import (
    NEO4J_DATABASE,
    NEO4J_ENABLED,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
)

logger = logging.getLogger(__name__)

_GLOBAL_CONNECTOR: Optional[Neo4jConnector] = None


class Neo4jConnector:
    """Manages connections and transactions to the Neo4j Knowledge Graph."""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
        database: str = NEO4J_DATABASE,
        enabled: bool = NEO4J_ENABLED,
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.enabled = enabled
        self._driver = None
        self._connected = False

        if self.enabled:
            self._initialize_driver()

    def _initialize_driver(self) -> None:
        """Initializes the Neo4j driver if enabled and dependencies are present."""
        try:
            import neo4j
            self._driver = neo4j.GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=10.0,
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            self._connected = True
            logger.info("Successfully connected to Neo4j Knowledge Graph at %s", self.uri)
        except ImportError:
            logger.warning("neo4j Python package not available. Neo4j connectivity disabled.")
            self._connected = False
            self._driver = None
        except Exception as e:
            logger.warning("Could not connect to Neo4j at %s: %s. Operating in vector-only mode.", self.uri, e)
            self._connected = False
            self._driver = None

    def is_connected(self) -> bool:
        """Checks if the Neo4j driver is active and verified."""
        if not self._driver or not self._connected:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            self._connected = False
            return False

    def run_query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a read Cypher query and returns the record results as a list of dicts.

        Args:
            cypher: The Cypher statement to run.
            parameters: Dictionary of query parameters.

        Returns:
            List of dictionaries representing matched records.
        """
        if not self.is_connected() or not self._driver:
            logger.debug("Neo4j query skipped (database not connected).")
            return []

        try:
            with self._driver.session(database=self.database) as session:
                result = session.run(cypher, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error("Error executing Cypher query: %s. Query: %s", e, cypher)
            return []

    def run_write_batch(self, cypher: str, batch: List[Dict[str, Any]]) -> int:
        """Executes a write query with a batch parameter list.

        Args:
            cypher: Cypher statement utilizing UNWIND $batch AS item.
            batch: List of dictionaries to ingest.

        Returns:
            Number of items processed.
        """
        if not self.is_connected() or not self._driver:
            logger.warning("Cannot write to Neo4j (database not connected).")
            return 0

        try:
            with self._driver.session(database=self.database) as session:
                session.run(cypher, {"batch": batch})
                return len(batch)
        except Exception as e:
            logger.error("Error executing batch write query: %s", e)
            return 0

    def close(self) -> None:
        """Closes the active Neo4j driver."""
        if self._driver:
            self._driver.close()
            self._connected = False
            logger.info("Neo4j connection closed.")


def get_neo4j_connector() -> Neo4jConnector:
    """Returns the global singleton Neo4jConnector instance."""
    global _GLOBAL_CONNECTOR
    if _GLOBAL_CONNECTOR is None:
        _GLOBAL_CONNECTOR = Neo4jConnector()
    return _GLOBAL_CONNECTOR
