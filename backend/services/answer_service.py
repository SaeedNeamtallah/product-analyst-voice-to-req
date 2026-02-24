"""
Answer Generation Service.
Handles generating AI-powered answers using LLM.
"""
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.providers.llm.factory import LLMProviderFactory
from backend.services.resilience_service import run_with_failover, circuit_breakers
from backend.runtime_config import get_runtime_value
from backend.config import settings
import json
import logging

logger = logging.getLogger(__name__)

_ANSWER_SYSTEM_PROMPT = """\
أنت مهندس برمجيات استشاري (Consulting Software Engineer).
مهمتك هي الإجابة على أسئلة العميل حول تفاصيل مشروعه الحالي بوضوح واحترافية.

## الذاكرة الحالية للمشروع (SRS Snapshot):
{srs_snapshot}

## قواعد الإجابة الصارمة (Zero Hallucination Policy):
1. التقيد التام بالذاكرة: إجاباتك يجب أن تُستمد حصرياً من (SRS Snapshot) المرفق أعلاه.
2. منع التأليف: يُمنع منعاً باتاً اختراع، افتراض، أو اقتراح ميزات أو أرقام أو قيود غير موجودة صراحة في الذاكرة الحالية.
3. التعامل مع المجهول: إذا سأل العميل عن تفصيلة غير موجودة في الـ Snapshot، يجب أن تجيبه بوضوح: "هذا المتطلب لم نقم بتحديده أو مناقشته حتى الآن ضمن نطاق المشروع. هل تود أن نضيفه الآن؟".
4. الإيجاز والمهنية: كن مباشراً في إجابتك، واستخدم أسلوباً احترافياً يعكس خبرتك الهندسية.
5. لغة العميل: أجب بنفس اللغة التي استخدمها العميل في سؤاله.
"""

_ANSWER_SYSTEM_PROMPT_EN = """\
You are a consulting software engineer.
Your task is to answer the client's questions about the current project clearly and professionally.

## Current project memory (SRS Snapshot):
{srs_snapshot}

## Strict answer rules (Zero Hallucination Policy):
1. Memory-only answers: your response must be derived exclusively from the SRS Snapshot above.
2. No fabrication: do not invent assumptions, features, numbers, or constraints that are not explicitly in memory.
3. Unknown handling: if the user asks about a detail not found in memory, respond clearly with: "This requirement has not been defined or discussed yet within the current project scope. Would you like us to add it now?"
4. Concise professionalism: keep answers direct and technically professional.
5. User language: answer in the same language as the user question.
"""


class AnswerService:
    """Service for generating answers from transcript context."""
    
    def __init__(self):
        """Initialize answer service."""
        self.llm_provider = LLMProviderFactory.create_provider()
        logger.info("Answer service initialized")

    @staticmethod
    def _candidate_llm_providers() -> List[str]:
        preferred = [
            "openrouter-gemini-2.0-flash",
            "groq-llama-3.3-70b-versatile",
            "cerebras-llama-3.3-70b",
            "cerebras-llama-3.1-8b",
            "openrouter-free",
            "gemini",
            "gemini-2.5-flash",
            "gemini-2.5-lite-flash",
        ]
        available = set(LLMProviderFactory.get_available_providers())
        if not available:
            return []

        selected = str(get_runtime_value("llm_provider", settings.llm_provider) or "").strip().lower()
        ordered: List[str] = []

        if selected in available:
            ordered.append(selected)

        for name in preferred:
            if name in available and name not in ordered:
                ordered.append(name)

        for name in sorted(available):
            if name not in ordered:
                ordered.append(name)

        return ordered

    async def _generate_text_resilient(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        providers = self._candidate_llm_providers()
        if not providers:
            return await self.llm_provider.generate_text(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        provider_calls = []
        for provider_name in providers:
            provider_calls.append((
                provider_name,
                lambda pn=provider_name: self._provider_generate_text(
                    provider_name=pn,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            ))

        result, _ = await run_with_failover(
            provider_calls,
            breaker_prefix="answer_text",
            failure_threshold=2,
            cooldown_seconds=45,
        )
        return str(result)

    @staticmethod
    async def _provider_generate_text(
        *,
        provider_name: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        provider = LLMProviderFactory.create_provider(provider_name)
        return await provider.generate_text(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _generate_stream_resilient(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        providers = self._candidate_llm_providers()
        if not providers:
            async for token in self.llm_provider.generate_text_stream(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield token
            return

        last_error: Exception | None = None
        for provider_name in providers:
            key = f"answer_stream:{provider_name}"
            if await circuit_breakers.is_open(key):
                continue

            provider = LLMProviderFactory.create_provider(provider_name)
            started = False
            try:
                async for token in provider.generate_text_stream(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    started = True
                    yield token
                await circuit_breakers.record_success(key)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                await circuit_breakers.record_failure(key, threshold=2, cooldown_seconds=45)
                if started:
                    raise
                continue

        if last_error is not None:
            raise last_error
        raise RuntimeError("No available providers for answer streaming")
    
    async def generate_answer(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        language: str = "ar",  # Default to Arabic
        include_sources: bool = True,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate answer from query and context.
        
        Args:
            query: User question
            context_chunks: List of relevant transcript context blocks
            language: Response language ('ar' or 'en')
            include_sources: Whether to include source references
            
        Returns:
            Dict with 'answer' and optional 'sources'
        """
        try:
            # Build context from transcript blocks
            context = self._build_context(context_chunks, language)

            # Build prompt
            prompt = self._build_prompt(query, context, language, project_context)
            
            # Generate answer
            answer = await self._generate_text_resilient(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Format response
            response = {
                'answer': answer.strip(),
                'context_used': len(context_chunks)
            }
            
            if include_sources:
                response['sources'] = self._extract_sources(context_chunks)
            
            logger.info(f"Generated answer (length={len(answer)})")
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise

    async def generate_answer_stream(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        language: str = "ar",
        project_context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream answer tokens from LLM.

        Yields raw text tokens as they arrive from the provider.
        """
        try:
            context = self._build_context(context_chunks, language)
            prompt = self._build_prompt(query, context, language, project_context)

            async for token in self._generate_stream_resilient(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
            ):
                yield token

        except Exception as e:
            logger.error(f"Error streaming answer: {str(e)}")
            raise
    
    def _build_context(self, chunks: List[Dict[str, Any]], language: str = "ar") -> str:
        """
        Build context string from transcript blocks.

        Args:
            chunks: List of context dictionaries
            language: 'ar' or 'en' — controls source label language

        Returns:
            Formatted context string
        """
        context_parts = []

        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            doc_name = metadata.get('document_name', 'Unknown')
            content = chunk.get('content', '')

            source_index = len(context_parts) + 1
            label = f"مصدر {source_index}" if language == "ar" else f"Source {source_index}"
            context_parts.append(f"[{label} - {doc_name}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(
        self,
        query: str,
        context: str,
        language: str,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build prompt for LLM.
        
        Args:
            query: User question
            context: Context text
            language: Response language
            
        Returns:
            Formatted prompt
        """
        response_style = self._response_style_from_query(query=query, language=language)
        project_profile = self._build_project_profile(project_context)

        if language == "ar":
            system_prompt = """أنت مستشار تقني/أعمال احترافي بمستوى مؤسسي (Industry-grade) للمشاريع البرمجية.
الهدف: تقديم إجابة عملية قابلة للتنفيذ وتخدم سياق المشروع الحالي.

قواعد إلزامية:
1) اعتمد على سياق المستندات أولًا، ثم على ملف المشروع/SRS إن توفر.
2) إذا كانت معلومة غير موجودة في السياق، صرّح بذلك بوضوح ولا تختلق.
3) اربط كل نقطة مهمة باستشهاد داخل النص مثل (مصدر 1).
4) اجعل الإجابة مهنية وقابلة للتنفيذ: قرارات، خطوات، أو معايير واضحة.
5) لا تكرّر نصوص عامة؛ خصّص الإجابة على المشروع المطلوب.

تنسيق الإخراج:
- إجابة مباشرة أولًا (2-4 سطور).
- ثم نقاط تنفيذية قصيرة عند الحاجة مع الاستشهادات.
- ثم بند "مخاطر/افتراضات" إذا كانت البيانات ناقصة."""

            prompt = f"""{system_prompt}

بروفايل المشروع:
{project_profile}

أسلوب الإجابة المطلوب:
{response_style}

السياق:
{context}

السؤال:
{query}

الإجابة:"""
        else:
            system_prompt = """You are an enterprise solution assistant (industry-grade) for software projects.
Goal: deliver project-serving, execution-ready answers.

Mandatory rules:
1) Prioritize provided interview transcript context, then use project/SRS profile if available.
2) If evidence is missing, say it clearly and avoid fabrication.
3) Cite key claims inline as (Source 1), (Source 2), etc.
4) Keep outputs implementation-oriented: decisions, steps, and criteria.
5) Avoid generic boilerplate; tailor to this project.

Output format:
- Direct answer first (2-4 lines).
- Then concise action bullets when useful, with citations.
- Add "Risks/Assumptions" when data is incomplete."""

            prompt = f"""{system_prompt}

Project profile:
{project_profile}

Preferred response style:
{response_style}

Context:
{context}

Question:
{query}

Answer:"""
        
        return prompt
    
    def _extract_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract source information from chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            List of source information
        """
        sources = []
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            sources.append({
                'document_name': metadata.get('document_name', 'Unknown'),
                'chunk_index': metadata.get('chunk_index', 0),
                'similarity': chunk.get('similarity', 0.0),
                'asset_id': chunk.get('asset_id')
            })

        return sources

    # ------------------------------------------------------------------
    # No-context fallback (LLM-only mode when no documents are uploaded)
    # ------------------------------------------------------------------

    async def generate_answer_no_context(
        self,
        query: str,
        language: str = "ar",
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate answer using LLM general knowledge when no documents exist."""
        try:
            prompt = self._build_no_context_prompt(query, language, project_context)
            answer = await self._generate_text_resilient(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
            )
            return {
                'answer': answer.strip(),
                'sources': [],
                'context_used': 0,
            }
        except Exception as e:
            logger.error(f"Error generating no-context answer: {str(e)}")
            raise

    async def generate_answer_no_context_stream(
        self,
        query: str,
        language: str = "ar",
        project_context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream answer tokens using LLM general knowledge when no documents exist."""
        try:
            prompt = self._build_no_context_prompt(query, language, project_context)
            async for token in self._generate_stream_resilient(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
            ):
                yield token
        except Exception as e:
            logger.error(f"Error streaming no-context answer: {str(e)}")
            raise

    @staticmethod
    def _build_no_context_prompt(
        query: str,
        language: str,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build strict memory-only prompt for no-RAG answer mode."""
        snapshot = "{}"
        if isinstance(project_context, dict):
            srs = project_context.get("srs")
            if isinstance(srs, dict):
                content = srs.get("content")
                if isinstance(content, dict) and content:
                    snapshot = json.dumps(content, ensure_ascii=False)

        if language == "ar":
            base = _ANSWER_SYSTEM_PROMPT.format(srs_snapshot=snapshot)
            return f"""{base}

السؤال:
{query}

الإجابة:"""

        base = _ANSWER_SYSTEM_PROMPT_EN.format(srs_snapshot=snapshot)
        return f"""{base}

Question:
{query}

Answer:"""

    @staticmethod
    def _build_project_profile(project_context: Optional[Dict[str, Any]]) -> str:
        if not project_context:
            return "N/A"

        profile: Dict[str, Any] = {
            "project_name": project_context.get("project_name") or "",
            "project_description": project_context.get("project_description") or "",
        }

        srs = project_context.get("srs")
        if isinstance(srs, dict):
            profile["srs_version"] = srs.get("version")
            profile["srs_status"] = srs.get("status")
            content = srs.get("content") if isinstance(srs.get("content"), dict) else {}
            if content:
                profile["srs_snapshot"] = content

        serialized = json.dumps(profile, ensure_ascii=False)
        return serialized[:4000] + ("…" if len(serialized) > 4000 else "")

    @staticmethod
    def _response_style_from_query(query: str, language: str) -> str:
        q = (query or "").lower()
        is_ar = language == "ar"

        if any(k in q for k in ["قارن", "فرق", "مقارنة", "compare", "difference", "vs"]):
            return (
                "قدّم مقارنة مختصرة بجدول/نقاط: خيارات، مزايا، مخاطر، وتوصية نهائية."
                if is_ar else
                "Provide a compact comparison: options, pros, risks, and a final recommendation."
            )
        if any(k in q for k in ["خطوة", "خطوات", "plan", "roadmap", "implement", "تنفيذ"]):
            return (
                "أعط خطة تنفيذ مرتبة زمنيًا مع أولويات واضحة ومعيار نجاح لكل خطوة."
                if is_ar else
                "Provide a sequenced implementation plan with priorities and success criteria per step."
            )
        if any(k in q for k in ["template", "صيغة", "نموذج", "format"]):
            return (
                "قدّم قالبًا جاهزًا للاستخدام مع حقول قابلة للتعبئة سريعًا."
                if is_ar else
                "Provide a ready-to-use template with fillable fields."
            )
        return (
            "أجب بإيجاز احترافي أولًا ثم نقاط تنفيذية عملية مرتبطة بالمشروع."
            if is_ar else
            "Answer with concise professional summary first, then practical project-specific action bullets."
        )
