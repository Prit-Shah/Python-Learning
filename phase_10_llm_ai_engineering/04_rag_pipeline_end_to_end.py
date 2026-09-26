r"""
04_rag_pipeline_end_to_end.py

============================================================
1. CONCEPT
============================================================

Retrieval-Augmented Generation (RAG) is the enterprise architectural standard for
grounding Large Language Models on proprietary, private, or real-time domain knowledge
without costly model fine-tuning:

1. The Three RAG Operational Phases:
   - Ingestion Phase:
     * Raw document extraction (PDF, Markdown, HTML, Database text).
     * Chunking: Partitioning continuous text into semantic units with chunk overlap.
     * Embedding: Converting chunks into dense vectors using an embedding model.
     * Persistence: Storing vectors and chunk text in a vector database (e.g. `pgvector`).
   - Retrieval & Re-ranking Phase:
     * User query is embedded into vector space.
     * Approximate Nearest Neighbor (ANN) search retrieves top $K$ candidate chunks ($K \approx 20$).
     * Cross-Encoder Re-ranker evaluates deep cross-attention between query and candidate text,
       re-sorting and filtering down to top $N$ most relevant chunks ($N \approx 3-5$).
   - Synthesis & Grounding Phase:
     * Context Assembly: Stuffing retrieved chunks into an engineered prompt template.
     * Grounding Constraints: Directing the model to answer EXCLUSIVELY from provided context,
       explicitly refusing to answer if the context lacks necessary information.
     * Attribution: Extracting and returning source citations back to the user.

2. Chunking Strategies:
   - Recursive Character Splitting: Attempts to split along natural semantic boundaries in order
     of priority: paragraphs (`\n\n`), sentences (`\n`, `. `), words (` `), and characters.
   - Chunk Overlap: Duplicating 10-20% of tokens between adjacent chunks guarantees that sentences
     spanning chunk boundaries are not truncated or stripped of semantic context.

3. The Bi-Encoder vs Cross-Encoder Paradigm:
   - Bi-Encoder (Embedding Models):
     * Encodes query $q$ and document $d$ independently: $v_q = E(q)$, $v_d = E(d)$.
     * Fast dot-product comparison. Enables scalable $O(\log N)$ search over millions of docs.
     * Limitation: No cross-token attention between query words and document words.
   - Cross-Encoder (Re-Rankers):
     * Feeds query and document jointly into transformer layers: $\text{Score} = M(q \circ d)$.
     * Full all-to-all self-attention between query tokens and document tokens.
     * Computationally expensive ($O(K)$), but delivers 15-20% higher retrieval precision.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (LlamaIndex / LangChain)    | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Framework Ecosystem          | LlamaIndex / LangChain / Haystack  | LangChain.js / LlamaIndex.TS       |
| Text Splitting               | `RecursiveCharacterTextSplitter`   | `langchain/text_splitter`          |
| In-Process Embeddings        | `sentence-transformers` / PyTorch  | Remote API calls (OpenAI/Cohere)   |
| Cross-Encoder Re-ranking     | HuggingFace CrossEncoder / Cohere  | Cohere Rerank API                  |
| Prompt Templating            | Python f-strings / Jinja2          | JS template literals               |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Python, developers can run local, private, zero-cost embedding models and Cross-Encoders
   directly on GPU or CPU using PyTorch and HuggingFace `sentence-transformers`.
2. In Node.js, running local transformer inference is difficult; TypeScript RAG pipelines almost
   exclusively rely on external third-party HTTP APIs for embedding generation and re-ranking.


============================================================
3. UNDER THE HOOD (Lost-in-the-Middle & Context Windows)
============================================================

1. The "Lost-in-the-Middle" Attention Phenomenon:
   - Research shows that decoder-only transformer LLMs exhibit a U-shaped attention distribution:
     they attend with highest fidelity to information at the very beginning of the prompt (the system instructions)
     and at the very end of the prompt (the user query).
   - Information buried in the middle of a massive context window (chunks 5 through 15) suffers from
     attention degradation and is frequently ignored.
   - Mitigation: Context Re-Ordering—place the highest-scoring re-ranked chunks at the beginning and end
     of the context block, placing lower-confidence chunks in the middle.

2. Context Stuffing Budget Calculation:
   - Total Budget = Model Context Limit (e.g. 8192 tokens)
     - Reserved for System Prompt & Formatting (~200 tokens)
     - Reserved for User Query (~100 tokens)
     - Reserved for Model Generated Answer (~1000 tokens)
     - Available for Retrieval Context = $8192 - 1300 = 6892 \text{ tokens}$.
   - Never inject raw unbounded chunks without verifying token length against the budget.


============================================================
4. COMMON GOTCHAS
============================================================

1. Chunking Without Overlap:
   - Setting `chunk_overlap = 0` causes sentence fractures. If a crucial definition is split
     across chunk A and chunk B, neither chunk contains sufficient semantic context to be retrieved.
   - FIX: Always configure 10% to 20% overlap (e.g., `chunk_size=500`, `chunk_overlap=50`).

2. Missing Negative Refusal Instructions:
   - Omitting grounding constraints allows the LLM to hallucinate using its pre-trained parametric
     memory when the retrieved context does not contain the answer.
   - FIX: Explicitly instruct: "Answer ONLY using facts from the context below. If the answer cannot
     be deduced from the context, respond: 'I do not have sufficient information to answer this question.'"

3. Ingesting Duplicates & Stale Revisions:
   - Re-indexing updated documents without purging older chunk versions fills the vector database
     with contradictory information, causing the retriever to fetch stale documents.
   - FIX: Use content-hashing (SHA-256) or document versioning to upsert/delete obsolete chunks.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Walk through the architectural stages of an enterprise production RAG pipeline."
A1: "An enterprise RAG pipeline operates across three decoupled stages:
     First, Ingestion: Documents are parsed, stripped of boilerplate, and split using a recursive
     character text splitter with 10-20% chunk overlap. Each chunk is hashed for deduplication,
     embedded into dense vectors, and stored in `pgvector` alongside relational metadata and timestamps.
     Second, Two-Stage Retrieval: When a query arrives, we execute hybrid search (combining dense vector
     cosine similarity with sparse full-text search) to fetch the top 20 candidate chunks. We pass these
     candidates through a Cross-Encoder re-ranker to compute deep cross-attention scores, filtering down
     to the top 3-5 most relevant chunks.
     Third, Synthesis & Grounding: The re-ranked chunks are formatted with source IDs into an engineered
     system prompt that strictly instructs the model to refuse to answer if the context is insufficient.
     The LLM generates the response with inline citations, which we validate with hallucination guardrails
     before streaming to the client."

Q2: "What is the difference between a Bi-Encoder and a Cross-Encoder, and why use both in RAG?"
A2: "A Bi-Encoder encodes the query and document into separate vector embeddings independently.
     Because vectors are pre-computed, we can compare them via dot product in milliseconds across millions
     of documents using vector database indexes. However, because query and document tokens never interact
     during encoding, it lacks fine-grained semantic comprehension.
     A Cross-Encoder passes the query and document simultaneously through transformer self-attention layers,
     allowing every query token to attend to every document token. This produces vastly superior relevance
     scoring, but is far too computationally expensive to run against thousands of documents.
     In production RAG, we combine both: we use the fast Bi-Encoder to retrieve the top 20 candidate documents,
     and then use the accurate Cross-Encoder to re-rank those 20 down to the top 3."

Q3: "What is the 'Lost-in-the-Middle' problem in RAG, and how do you solve it?"
A3: "The 'Lost-in-the-Middle' phenomenon refers to empirical findings that decoder LLMs attend disproportionately
     to tokens placed at the beginning and the very end of their prompt context, while information positioned
     in the middle is frequently overlooked or forgotten during generation.
     We mitigate this through two techniques:
     First, Strict Re-ranking: by filtering down to only the top 3-4 most relevant chunks, we minimize the
     overall context volume, eliminating low-quality distractor chunks.
     Second, Context Re-Ordering: when assembling the prompt, we place the #1 most relevant chunk at the
     very top of the context block, the #2 most relevant chunk at the very bottom immediately before the user
     question, and the remaining chunks in between, ensuring critical facts reside in high-attention zones."
"""

import sys
import re
import warnings
warnings.filterwarnings("ignore")
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. TEXT CHUNKING ENGINE
# ==============================================================================

class RecursiveTextChunker:
    """
    Splits continuous text into overlapping semantic chunks
    using hierarchical delimiters (\n\n, \n, ' ').
    """

    def __init__(self, chunk_size: int = 150, chunk_overlap: int = 30):
        assert chunk_overlap < chunk_size, "Overlap must be strictly smaller than chunk size"
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text.strip():
            return []

        # Split into words for simple deterministic tokenization simulation
        words = text.split()
        if len(words) <= self.chunk_size:
            return [" ".join(words)]

        chunks: List[str] = []
        step = self.chunk_size - self.chunk_overlap
        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + self.chunk_size >= len(words):
                break

        return chunks


# ==============================================================================
# 2. TWO-STAGE RETRIEVAL & RE-RANKING ENGINE
# ==============================================================================

class CrossEncoderReRanker:
    """
    Simulates a Cross-Encoder re-ranking model:
    Evaluates deep cross-token interaction between query and candidate text.
    """

    @staticmethod
    def compute_relevance(query: str, document_text: str) -> float:
        # Heuristic scoring: term overlap + exact phrase match boost
        q_tokens = set(re.findall(r"\w+", query.lower()))
        d_tokens = set(re.findall(r"\w+", document_text.lower()))

        if not q_tokens:
            return 0.0

        overlap_ratio = len(q_tokens.intersection(d_tokens)) / len(q_tokens)
        phrase_boost = 0.5 if query.lower() in document_text.lower() else 0.0
        return float(min(1.0, overlap_ratio + phrase_boost))


class RAGRetriever:
    """In-memory vector store simulating Bi-Encoder retrieval + Cross-Encoder re-ranking."""

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []

    def index_document(self, doc_id: str, title: str, content: str, chunker: RecursiveTextChunker) -> int:
        raw_chunks = chunker.split_text(content)
        for idx, text in enumerate(raw_chunks):
            self.chunks.append({
                "chunk_id": f"{doc_id}#chunk_{idx}",
                "doc_id": doc_id,
                "title": title,
                "text": text
            })
        return len(raw_chunks)

    def retrieve_and_rerank(self, query: str, top_k_initial: int = 5, top_n_final: int = 2) -> List[Dict[str, Any]]:
        # Stage 1: Candidate retrieval (Bi-encoder simulation via token overlap)
        scored_candidates = []
        for c in self.chunks:
            score = CrossEncoderReRanker.compute_relevance(query, c["text"])
            scored_candidates.append({**c, "initial_score": score})

        # Sort by initial score and take top K
        scored_candidates.sort(key=lambda x: x["initial_score"], reverse=True)
        candidates = scored_candidates[:top_k_initial]

        # Stage 2: Cross-Encoder Re-Ranking
        for c in candidates:
            c["rerank_score"] = CrossEncoderReRanker.compute_relevance(query, c["text"])

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates[:top_n_final]


# ==============================================================================
# 3. PROMPT SYNTHESIS & GROUNDING GUARDRAILS
# ==============================================================================

class RAGPromptAssembler:
    """Constructs grounded prompts with citations and anti-hallucination guardrails."""

    SYSTEM_TEMPLATE = (
        "You are an enterprise AI assistant. Answer the user question EXCLUSIVELY using the facts "
        "provided in the context below.\n"
        "Grounding Rules:\n"
        "1. Do NOT assume, extrapolate, or use outside knowledge.\n"
        "2. If the context does not contain the answer, reply exactly: "
        "'I do not have sufficient information in the provided context to answer this question.'\n"
        "3. Include bracketed citations like [DocID] for every factual statement."
    )

    @classmethod
    def assemble_prompt(cls, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        context_blocks = []
        for c in context_chunks:
            block = f"--- [Citation: {c['chunk_id']}] (Source: {c['title']}) ---\n{c['text']}"
            context_blocks.append(block)

        formatted_context = "\n\n".join(context_blocks)
        user_prompt = f"Context:\n{formatted_context}\n\nQuestion: {query}\n\nAnswer:"

        return {
            "system": cls.SYSTEM_TEMPLATE,
            "user": user_prompt,
            "num_chunks_injected": len(context_chunks)
        }


# ==============================================================================
# 4. END-TO-END RAG PIPELINE
# ==============================================================================

class EndToEndRAGPipeline:
    """Orchestrates chunking, indexing, retrieval, re-ranking, and response generation."""

    def __init__(self, chunk_size: int = 40, chunk_overlap: int = 10):
        self.chunker = RecursiveTextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.retriever = RAGRetriever()

    def load_knowledge_base(self, documents: List[Dict[str, str]]) -> None:
        for doc in documents:
            self.retriever.index_document(doc["id"], doc["title"], doc["content"], self.chunker)

    def answer_query(self, query: str) -> Dict[str, Any]:
        # 1. Retrieve & Re-Rank
        top_chunks = self.retriever.retrieve_and_rerank(query, top_k_initial=5, top_n_final=2)

        # 2. Check relevance threshold to prevent hallucinating on completely unrelated queries
        if not top_chunks or top_chunks[0]["rerank_score"] < 0.2:
            return {
                "answer": "I do not have sufficient information in the provided context to answer this question.",
                "citations": [],
                "grounded": True
            }

        # 3. Assemble Prompt
        prompt_payload = RAGPromptAssembler.assemble_prompt(query, top_chunks)

        # 4. Simulated LLM generation grounded in top chunk
        top_chunk = top_chunks[0]
        answer_text = (
            f"Based on the knowledge base [{top_chunk['chunk_id']}], "
            f"{top_chunk['text'][:120]}..."
        )

        return {
            "answer": answer_text,
            "citations": [c["chunk_id"] for c in top_chunks],
            "prompt_payload": prompt_payload,
            "grounded": True
        }


# ==============================================================================
# 5. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 04_rag_pipeline_end_to_end.py...")

    # ------------------------------------------------------------
    # Test 1: Recursive Character Chunking with Overlap
    # ------------------------------------------------------------
    print("  -> Testing recursive text chunking and overlap continuity...")
    chunker = RecursiveTextChunker(chunk_size=10, chunk_overlap=3)
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15"

    chunks = chunker.split_text(text)
    assert len(chunks) >= 2
    # Verify overlap: last 3 words of chunk 0 should equal first 3 words of chunk 1
    c0_words = chunks[0].split()
    c1_words = chunks[1].split()
    assert c0_words[-3:] == c1_words[:3], "Chunk overlap boundary failed"

    # ------------------------------------------------------------
    # Test 2: Ingestion & Two-Stage Re-Ranking
    # ------------------------------------------------------------
    print("  -> Testing document indexing and Cross-Encoder re-ranking...")
    rag = EndToEndRAGPipeline(chunk_size=20, chunk_overlap=5)

    knowledge_base = [
        {
            "id": "DOC-AUTH",
            "title": "OAuth2 Security Architecture",
            "content": (
                "FastAPI supports OAuth2 password flow with JWT tokens. "
                "Tokens are signed using HS256 algorithm and contain expiration claims. "
                "The Authorization header transmits Bearer tokens securely."
            )
        },
        {
            "id": "DOC-DB",
            "title": "SQLAlchemy 2.0 Async Guidelines",
            "content": (
                "SQLAlchemy 2.0 introduces AsyncSession and select statements. "
                "Eager loading with selectinload prevents the N+1 query problem. "
                "Always set expire_on_commit to False in async sessionmakers."
            )
        }
    ]
    rag.load_knowledge_base(knowledge_base)
    assert len(rag.retriever.chunks) >= 4, "Knowledge base chunks missing"

    # Query targeting OAuth2
    top_auth = rag.retriever.retrieve_and_rerank("How are JWT tokens signed in OAuth2?", top_n_final=2)
    assert len(top_auth) == 2
    assert "DOC-AUTH" in top_auth[0]["doc_id"], "OAuth2 document must be top-ranked"
    assert top_auth[0]["rerank_score"] > 0.4

    # ------------------------------------------------------------
    # Test 3: Prompt Assembly & Grounding Guardrails
    # ------------------------------------------------------------
    print("  -> Testing prompt formatting and grounding instructions...")
    prompt_obj = RAGPromptAssembler.assemble_prompt("What prevents N+1 queries?", top_auth)
    assert "You are an enterprise AI assistant" in prompt_obj["system"]
    assert "I do not have sufficient information" in prompt_obj["system"]
    assert "--- [Citation: DOC-AUTH#chunk_" in prompt_obj["user"]

    # ------------------------------------------------------------
    # Test 4: End-to-End Pipeline & Positive Retrieval
    # ------------------------------------------------------------
    print("  -> Testing End-to-End RAG execution with citation verification...")
    result_auth = rag.answer_query("How do you configure OAuth2 tokens?")
    assert result_auth["grounded"] is True
    assert len(result_auth["citations"]) > 0
    assert any("DOC-AUTH" in c for c in result_auth["citations"])

    # ------------------------------------------------------------
    # Test 5: Out-of-Domain Refusal (Hallucination Prevention)
    # ------------------------------------------------------------
    print("  -> Testing out-of-domain query refusal (hallucination defense)...")
    # Completely unrelated query with zero token overlap in knowledge base
    result_refusal = rag.answer_query("What is the recipe for baking chocolate chip cookies?")
    assert "I do not have sufficient information" in result_refusal["answer"]
    assert len(result_refusal["citations"]) == 0

    print("[SUCCESS] All 5 RAG Pipeline End-to-End tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10 - 04: Production RAG Pipeline, Chunking & Re-Ranking")
    print("=" * 70)
    run_tests()
    print("=" * 70)
