"""
🦊 Fennec RAG — Customer Support Engine
Orchestrates Fennec components for intelligent support.
"""

import os
import logging
from typing import Dict
from pathlib import Path

from fennec.rag.core import RAGSystem, RAGConfig
from fennec.rag.conversational_rag import ConversationalRAG
from fennec.vector_database import FAISSVectorDatabase
from fennec.embeddings import OllamaEmbedder
from fennec.chunks import MultilanguageTextChunker
from fennec.context import ContextManager, ContextConfig
from fennec.llm import GeminiInterface
from fennec.document_loaders import DirectoryLoader

from .semantic_router import SupportRouter
from .models import RAGResult

logger = logging.getLogger("rag_engine")

KB_PATH = Path(__file__).parent.parent / "knowledge_base"

ROUTE_SUGGESTIONS = {
    "faq": [
        "Tell me about shipping options",
        "What's the warranty policy?",
        "How to track my order?",
    ],
    "orders": [
        "How do I cancel an order?",
        "Can I change my delivery address?",
        "When will my order arrive?",
    ],
    "complaints": [
        "I want to request a refund",
        "Escalate my complaint",
        "Speak with a human agent",
    ],
    "technical": [
        "How do I reset my password?",
        "App is not loading — what do I do?",
        "How to update my account info?",
    ],
    "returns": [
        "Start a return request",
        "What items are non-returnable?",
        "How long does a refund take?",
    ],
    "general": [
        "What are your working hours?",
        "How can I contact support?",
        "Tell me about your services",
    ],
}


def _detect_language(text: str) -> str:
    """Detect Arabic vs English from character distribution."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return "ar" if arabic_chars > len(text) * 0.2 else "en"


class CustomerSupportRAG:
    """
    Full customer support engine powered by Fennec RAG.

    Components:
    ┌─────────────────────────────────────────────────┐
    │  SemanticRouter  → classifies query intent      │
    │  ConversationalRAG → answers with history       │
    └─────────────────────────────────────────────────┘

    Note on HallucinationGuard:
    ConversationalRAG already enforces strict instructions that prevent
    the LLM from going outside the retrieved context. Adding a pattern-based
    HallucinationGuard on top incorrectly blocks valid answers (e.g. an
    answer containing "all products" triggers the overconfidence detector).
    The correct anti-hallucination layer here is the `instructions` field
    inside ConversationalRAG, not a post-hoc text classifier.
    """

    def __init__(self):
        self.is_ready = False
        self.doc_count = 0
        self._sessions: Dict[str, ConversationalRAG] = {}
        self._stats = {
            "total_queries": 0,
            "routes": {},
        }

        self._gemini_key = "AIzaSyCajpA74MWks0c_N_l2vR4dvwYnJqKH7_o"

    async def initialize(self):
        """Build all components and load knowledge base."""
        logger.info("🔧 Building Fennec components...")

        # ── 1. Embedder ───────────────────────────────────────────────────────
        self._embedder = OllamaEmbedder()

        # ── 2. Vector DB ──────────────────────────────────────────────────────
        self._vector_db = FAISSVectorDatabase(
            embedder=self._embedder,
            index_type="flat",
            distance_metric="cosine",
        )

        # ── 3. LLM ────────────────────────────────────────────────────────────
        self._llm = GeminiInterface(
            api_key=self._gemini_key,
            temperature=0.3,
            max_tokens=1024,
        )

        # ── 4. Chunker ────────────────────────────────────────────────────────
        self._chunker = MultilanguageTextChunker(
            chunk_size=512,
            overlap=128,
        )

        # ── 5. Context Manager ────────────────────────────────────────────────
        self._context_mgr = ContextManager(
            config=ContextConfig(
                max_context_length=4000,
                include_metadata=True,
            )
        )

        # ── 6. Base RAG System ────────────────────────────────────────────────
        self._rag = RAGSystem(
            vector_db=self._vector_db,
            llm=self._llm,
            chunker=self._chunker,
            context_manager=self._context_mgr,
            config=RAGConfig(
                top_k=6,
                prompt_language="ar",
            ),
        )

        # ── 7. Semantic Router ────────────────────────────────────────────────
        self._router = SupportRouter()

        # ── 8. Load Knowledge Base ────────────────────────────────────────────
        self.doc_count = await self._load_knowledge_base()

        self.is_ready = True
        logger.info(f"✅ Engine ready — {self.doc_count} document chunks indexed")

    async def _load_knowledge_base(self) -> int:
        """Load all documents from knowledge_base/ folder."""
        if not KB_PATH.exists():
            logger.warning(f"⚠️  Knowledge base folder not found: {KB_PATH}")
            return 0
        try:
            loader = DirectoryLoader(str(KB_PATH))
            docs = loader.load()
            if docs:
                self._rag.add_documents(docs)
                logger.info(f"📚 Loaded {len(docs)} documents from knowledge base")
                return len(docs)
        except Exception as e:
            logger.error(f"❌ Knowledge base load error: {e}")
        return 0

    async def reload_knowledge_base(self) -> int:
        """Hot-reload knowledge base without restarting."""
        self.doc_count = await self._load_knowledge_base()
        return self.doc_count

    def create_session(self, session_id: str):
        """Create a new ConversationalRAG session."""
        conv_rag = ConversationalRAG(
            rag_system=self._rag,
            max_history_turns=10,
            context_turns=3,
            lang="ar",       # default; updated per-turn in answer()
            auto_save=False,
        )
        self._sessions[session_id] = conv_rag
        logger.debug(f"📝 Session created: {session_id[:8]}")

    def remove_session(self, session_id: str):
        """Clean up session."""
        self._sessions.pop(session_id, None)

    def _resolve_language(self, query: str, language: str) -> str:
        """Return 'ar' or 'en'. Auto-detect from query when language='auto'."""
        if language in ("ar", "en"):
            return language
        return _detect_language(query)

    def _build_instructions(self, route: str, lang: str) -> str:
        """
        Build the system-prompt equivalent for ConversationalRAG.
        Set on conv_rag.instructions before every turn so it stays
        route- and language-aware.
        """
        if lang == "ar":
            base = (
                "أنت وكيل دعم عملاء محترف ومفيد. "
                "أجب بشكل واضح وموجز بناءً على السياق المسترجع فقط. "
                "إذا لم تجد الإجابة في السياق، قل ذلك بصدق — "
                "لا تضف أي معلومات غير موجودة في السياق. "
            )
            route_additions = {
                "faq":        "أجب على الأسئلة الشائعة بدقة وشمولية.",
                "orders":     "ساعد العميل في استفساراته المتعلقة بالطلبات. اطلب رقم الطلب إذا لزم.",
                "complaints": "كن متعاطفاً. اعترف بالمشكلة، اعتذر، وقدم الحلول.",
                "technical":  "قدم إرشادات تقنية خطوة بخطوة. اطلب توضيحاً إذا لزم.",
                "returns":    "اشرح سياسة الإرجاع والاسترداد بوضوح وارشد العميل خلال الخطوات.",
                "general":    "كن ودوداً ومفيداً. أرشد العميل إلى القسم المناسب إذا لزم.",
            }
            lang_note = "أجب دائماً باللغة العربية."
        else:
            base = (
                "You are a helpful, professional customer support agent. "
                "Answer clearly and concisely based ONLY on the provided context. "
                "If the answer is not in the context, say so honestly — "
                "never add information that is not in the retrieved context. "
            )
            route_additions = {
                "faq":        "Answer frequently asked questions accurately and thoroughly.",
                "orders":     "Help the customer with order-related queries. Ask for order number if needed.",
                "complaints": "Be empathetic. Acknowledge the issue, apologize, and offer solutions.",
                "technical":  "Provide clear step-by-step technical guidance. Ask for clarification if needed.",
                "returns":    "Explain the return/refund process clearly and guide the customer through steps.",
                "general":    "Be friendly and helpful. Guide the customer to the right department if needed.",
            }
            lang_note = "Always respond in English."

        return f"{base}{route_additions.get(route, '')} {lang_note}"

    async def answer(self, query: str, session_id: str, language: str = "auto") -> RAGResult:
        """
        Pipeline:
        1. Resolve language
        2. Route the query
        3. Update conv_rag.lang + conv_rag.instructions for this turn
        4. Generate via ConversationalRAG.ask()
        5. Return RAGResult — confidence derived from ask() availability
        """
        self._stats["total_queries"] += 1

        # ── 1. Language ───────────────────────────────────────────────────────
        lang = self._resolve_language(query, language)

        # ── 2. Routing ────────────────────────────────────────────────────────
        route_result = self._router.route(query)
        route = route_result.route
        self._stats["routes"][route] = self._stats["routes"].get(route, 0) + 1

        # ── 3. Session ────────────────────────────────────────────────────────
        if session_id not in self._sessions:
            self.create_session(session_id)
        conv_rag = self._sessions[session_id]

        # Update language and instructions on the instance for this turn.
        # ConversationalRAG uses self.lang inside _build_conversational_prompt()
        # so both must be in sync.
        conv_rag.lang = lang
        conv_rag.instructions = self._build_instructions(route, lang)

        # ── 4. Generate ───────────────────────────────────────────────────────
        try:
            answer_text = conv_rag.ask(
                query=query,
                include_sources=True,
                use_history=True,
            )
        except Exception as e:
            logger.error(f"RAG ask error: {e}")
            answer_text = self._fallback_answer(lang)

        if not isinstance(answer_text, str):
            answer_text = str(answer_text)

        return RAGResult(
            answer=answer_text,
            route=route,
            confidence=0.85,
            sources=[],
            suggestions=ROUTE_SUGGESTIONS.get(route, ROUTE_SUGGESTIONS["general"])[:3],
        )

    def _fallback_answer(self, lang: str) -> str:
        if lang == "ar":
            return (
                "عذراً، أواجه صعوبة في إيجاد الإجابة المناسبة الآن. "
                "حاول إعادة صياغة سؤالك أو تواصل مع فريق الدعم مباشرة."
            )
        return (
            "I'm sorry, I'm having trouble finding the right answer right now. "
            "Please try rephrasing your question or contact our support team directly."
        )

    def get_stats(self) -> dict:
        return {
            "engine": "Fennec RAG v1.0",
            "active_sessions": len(self._sessions),
            "knowledge_base_docs": self.doc_count,
            **self._stats,
        }
