"""
🧭 Semantic Router — Customer Support Query Classifier
Uses Fennec's SemanticRouter to route queries to the right handler.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from fennec.router import SemanticRouter, Route, RouterConfig

logger = logging.getLogger("semantic_router")


@dataclass
class RouteResult:
    route: str
    confidence: float
    matched_route: Optional[str] = None


class SupportRouter:
    """
    Routes customer queries to one of 6 support categories:
    ┌─────────────────────────────────────────────────────┐
    │  faq        → General frequently asked questions    │
    │  orders     → Order tracking, status, changes       │
    │  complaints → Issues, frustrations, escalations     │
    │  technical  → App/website/account technical issues  │
    │  returns    → Returns, refunds, exchanges           │
    │  general    → Greetings, out-of-scope, chitchat     │
    └─────────────────────────────────────────────────────┘
    """

    def __init__(self):
        config = RouterConfig(
            similarity_threshold=0.55,  # lower = more permissive routing
            similarity_metric="cosine",
            use_cache=True,
            cache_ttl=600,
            top_k_alternatives=2,
        )
        self._router = SemanticRouter(config=config)
        self._register_routes()
        logger.info("🧭 Semantic Router initialized with 6 support routes")

    def _register_routes(self):
        """Register all customer support routes with training examples."""

        self._router.add_route(Route(
            name="faq",
            description="General FAQs about products, services, policies, pricing",
            handler=lambda q, **kw: q,
            examples=[
                "What are your business hours?",
                "Do you ship internationally?",
                "What payment methods do you accept?",
                "Is there a loyalty program?",
                "What is your privacy policy?",
                "How does your subscription work?",
                "Do you offer discounts for students?",
                "What currencies do you support?",
                "Are your products eco-friendly?",
                # Arabic examples
                "ما هي ساعات العمل؟",
                "هل تشحنون دولياً؟",
                "ما طرق الدفع المتاحة؟",
                "هل هناك برنامج ولاء؟",
            ],
        ))

        self._router.add_route(Route(
            name="orders",
            description="Order tracking, status, modifications, delivery questions",
            handler=lambda q, **kw: q,
            examples=[
                "Where is my order?",
                "Track my package",
                "When will my order arrive?",
                "I want to change my delivery address",
                "Can I add items to my order?",
                "My order is delayed",
                "I didn't receive a confirmation email",
                "What is my order status?",
                "How do I cancel my order?",
                # Arabic
                "أين طلبي؟",
                "كيف أتابع شحنتي؟",
                "متى يصل طلبي؟",
                "أريد تغيير عنوان التسليم",
            ],
        ))

        self._router.add_route(Route(
            name="complaints",
            description="Complaints, bad experiences, escalations, frustrations",
            handler=lambda q, **kw: q,
            examples=[
                "I am very unhappy with my purchase",
                "This product is defective",
                "I want to complain about the service",
                "Your customer service is terrible",
                "I've been waiting weeks and nothing",
                "This is unacceptable, I want a manager",
                "I'm going to leave a bad review",
                "I received a damaged item",
                "Nobody is responding to my emails",
                # Arabic
                "أنا غير راضٍ عن الخدمة",
                "المنتج معطوب",
                "هذا أمر غير مقبول",
                "أريد التحدث مع مدير",
            ],
        ))

        self._router.add_route(Route(
            name="technical",
            description="Technical issues with app, website, account, login, payments",
            handler=lambda q, **kw: q,
            examples=[
                "I can't log in to my account",
                "The app keeps crashing",
                "Payment is not going through",
                "How do I reset my password?",
                "The website is not loading",
                "I can't update my profile",
                "I'm getting an error message",
                "Two-factor authentication is not working",
                "I forgot my email address",
                # Arabic
                "لا أستطيع تسجيل الدخول",
                "التطبيق لا يعمل",
                "كيف أغير كلمة المرور؟",
                "يظهر خطأ عند الدفع",
            ],
        ))

        self._router.add_route(Route(
            name="returns",
            description="Returns, refunds, exchanges, warranty claims",
            handler=lambda q, **kw: q,
            examples=[
                "I want to return this item",
                "How do I get a refund?",
                "Can I exchange for a different size?",
                "The item doesn't match the description",
                "I want to return a gift",
                "How long does a refund take?",
                "My return was rejected, why?",
                "What is the return window?",
                "I want to claim warranty",
                # Arabic
                "أريد إرجاع المنتج",
                "كيف أسترد أموالي؟",
                "ما هي سياسة الاسترجاع؟",
                "أريد الاستبدال",
            ],
        ))

        self._router.add_route(Route(
            name="general",
            description="Greetings, general questions, chitchat, out of scope",
            handler=lambda q, **kw: q,
            examples=[
                "Hello",
                "Hi there",
                "Good morning",
                "Thank you",
                "Goodbye",
                "Can you help me?",
                "I need assistance",
                "مرحباً",
                "أهلاً",
                "شكراً جزيلاً",
                "مع السلامة",
                "هل يمكنك مساعدتي؟",
            ],
        ))

    def route(self, query: str) -> RouteResult:
        """Route a query to the most appropriate support category."""
        try:
            result = self._router.route(query)
            if result and hasattr(result, "route_name"):
                return RouteResult(
                    route=result.route_name,
                    confidence=result.similarity_score,
                    matched_route=result.route_name,
                )
            # Fallback: return general
            return RouteResult(route="general", confidence=0.5)
        except Exception as e:
            logger.warning(f"Router error: {e} — defaulting to 'general'")
            return RouteResult(route="general", confidence=0.5)
