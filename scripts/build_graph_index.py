# -*- coding: utf-8 -*-
"""
VietLabor AI - Neo4j Knowledge Graph Indexing Script
Reads processed corpus data (READ-ONLY) and constructs the Legal Knowledge Graph in Neo4j.
Zero data modification: Does not alter or delete any source files.

Usage:
    python scripts/build_graph_index.py [--batch-size 200]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import time

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from config.settings import PRODUCTION_CORPUS_PATH
from graph.builder import KnowledgeGraphBuilder
from graph.connector import get_neo4j_connector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_graph_index")


def main():
    parser = argparse.ArgumentParser(description="Build VietLabor AI Neo4j Legal Knowledge Graph.")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size for Neo4j UNWIND queries.")
    parser.add_argument("--corpus", type=str, default=str(PRODUCTION_CORPUS_PATH), help="Path to legal documents JSONL.")
    args = parser.parse_args()

    logger.info("=== STARTING NEO4J KNOWLEDGE GRAPH BUILD PROCESS ===")
    connector = get_neo4j_connector()

    if not connector.is_connected():
        logger.error(
            "Cannot connect to Neo4j at %s. Please verify that Neo4j is running "
            "and check your credentials in config/settings.py or environment variables.",
            connector.uri,
        )
        sys.exit(1)

    t_start = time.time()
    builder = KnowledgeGraphBuilder(connector=connector, corpus_path=Path(args.corpus))
    stats = builder.build_from_corpus(batch_size=args.batch_size)
    elapsed = time.time() - t_start

    logger.info(
        "=== GRAPH BUILD FINISHED in %.2fs: %d Documents, %d Articles, %d Bridges ===",
        elapsed,
        stats.get("documents", 0),
        stats.get("articles", 0),
        stats.get("bridges", 0),
    )


if __name__ == "__main__":
    main()
