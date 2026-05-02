"""
KNOWLEDGE LOADER - ChromaDB Sovereign Knowledge Store
PROJECT-MONO | ALGA_FOLD_KERNEL | Node 001
Ingests Biomanifesto, Codex rules, repo code into local ChromaDB.
No cloud. All data stays on Node 001. Full lineage on every record.
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings

CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chromadb")
COLLECTION_NAME = "sovereign_knowledge"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(text, source, doc_type):
    chunks, words, i, idx = [], text.split(), 0, 0
    while i < len(words):
        ct = " ".join(words[i : i + CHUNK_SIZE])
        ch = hashlib.sha256(ct.encode()).hexdigest()[:16]
        chunks.append(
            {
                "id": f"{source}__chunk_{idx:04d}__{ch}",
                "text": ct,
                "metadata": {
                    "source": source,
                    "doc_type": doc_type,
                    "chunk_index": idx,
                    "chunk_hash": ch,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "node_id": "NODE_001",
                    "human_id": "human_001",
                    "lineage": f"ingested_by=knowledge_loader|source={source}|chunk={idx}",
                },
            }
        )
        i += CHUNK_SIZE - CHUNK_OVERLAP
        idx += 1
    return chunks


class SovereignKnowledgeStore:
    def __init__(self, persist_dir=CHROMA_DIR):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "PROJECT-MONO Sovereign Knowledge Ledger"},
        )
        print(f"[KNOWLEDGE] ChromaDB initialized at {persist_dir}")
        print(f"[KNOWLEDGE] Existing records: {self.collection.count()}")

    def ingest_document(self, text, source, doc_type):
        chunks = chunk_text(text, source, doc_type)
        if not chunks:
            return 0
        self.collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        print(f"[KNOWLEDGE] Ingested {len(chunks)} chunks from {source}")
        return len(chunks)

    def ingest_codex_rules(self):
        rules = [
            ("non_extraction", "No system may extract value from a human without sovereign consent and equitable return."),
            ("human_sovereignty", "Every human maintains irrevocable authority over their digital representation."),
            ("lineage_required", "Every action must carry provenance. Anonymous extraction is architecturally impossible."),
        ]
        for name, text in rules:
            self.collection.upsert(
                ids=[f"codex__rule__{name}"],
                documents=[text],
                metadatas=[
                    {
                        "source": "CORE_CODEX",
                        "doc_type": "codex_rule",
                        "rule_name": name,
                        "immutable": "true",
                        "node_id": "NODE_001",
                        "human_id": "human_001",
                    }
                ],
            )
        print("[KNOWLEDGE] Ingested 3 immutable Codex rules.")
        return 3

    def ingest_repo(self, repo_dir):
        total = 0
        for py_file in sorted(Path(repo_dir).rglob("*.py")):
            text = py_file.read_text(encoding="utf-8")
            total += self.ingest_document(text, str(py_file.name), "python_source")
        print(f"[KNOWLEDGE] Total repo chunks: {total}")
        return total

    def query(self, question, n_results=5):
        results = self.collection.query(query_texts=[question], n_results=n_results)
        return [
            {"id": results["ids"][0][i], "text": results["documents"][0][i], "metadata": results["metadatas"][0][i]}
            for i in range(len(results["ids"][0]))
        ]

    def status(self):
        return {
            "collection": COLLECTION_NAME,
            "total_records": self.collection.count(),
            "persist_dir": CHROMA_DIR,
            "node_id": "NODE_001",
            "sovereign": True,
        }


if __name__ == "__main__":
    print("SOVEREIGN KNOWLEDGE LOADER | Node 001 | ChromaDB Local")
    store = SovereignKnowledgeStore()
    store.ingest_codex_rules()
    repo_dir = os.getenv("REPO_DIR", ".")
    if Path(repo_dir).exists():
        store.ingest_repo(repo_dir)
    print(f"Status: {store.status()}")
    results = store.query("What are the Codex rules?")
    print(f"Test query: {len(results)} results")
    print("[KERNEL] Knowledge Ledger initialized. Sovereign memory active.")
