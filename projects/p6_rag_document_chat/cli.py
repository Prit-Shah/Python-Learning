"""
Project P6: CLI Interactive RAG Interface
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import argparse
from pathlib import Path
from .engine import RAGEngine


def main():
    parser = argparse.ArgumentParser(prog="rag", description="P6: RAG Document Chat Engine")
    parser.add_argument("--ingest", "-i", nargs="+", help="File paths to ingest")
    parser.add_argument("--query", "-q", help="Ask a question against the ingested documents")
    args = parser.parse_args()

    engine = RAGEngine()

    if args.ingest:
        for file in args.ingest:
            p = Path(file)
            if p.exists():
                count = engine.ingest_file(p)
                print(f"[SUCCESS] Ingested '{p.name}' into {count} chunks.")
            else:
                print(f"[ERROR] File '{file}' not found.")

    if args.query:
        resp = engine.query(args.query)
        print("
========================================")
        print(f" QUESTION: {args.query}")
        print("========================================")
        print(f"ANSWER: {resp.answer}
")
        print("Citations:")
        for c in resp.citations:
            print(f"  * [{c.doc_name} #chunk-{c.chunk_index}] (Score: {c.relevance_score}) {c.snippet}")
        print(f"
Latency: {resp.latency_ms:.1f}ms")


if __name__ == "__main__":
    main()
