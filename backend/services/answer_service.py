"""
Answer Generation Service.
Handles generating AI-powered answers using LLM.
"""
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.providers.llm.factory import LLMProviderFactory
import json
import logging

logger = logging.getLogger(__name__)


class AnswerService:
    """Service for generating answers from context."""
    
    def __init__(self):
        """Initialize answer service."""
        self.llm_provider = LLMProviderFactory.create_provider()
        logger.info("Answer service initialized")
    
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
            context_chunks: List of relevant chunks
            language: Response language ('ar' or 'en')
            include_sources: Whether to include source references
            
        Returns:
            Dict with 'answer' and optional 'sources'
        """
        try:
            # Build context from chunks
            context = self._build_context(context_chunks)
            
            # Build prompt
            prompt = self._build_prompt(query, context, language, project_context)
            
            # Generate answer
            answer = await self.llm_provider.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=25000
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
            context = self._build_context(context_chunks)
            prompt = self._build_prompt(query, context, language, project_context)

            async for token in self.llm_provider.generate_text_stream(
                prompt=prompt,
                temperature=0.7,
                max_tokens=25000,
            ):
                yield token

        except Exception as e:
            logger.error(f"Error streaming answer: {str(e)}")
            raise
    
    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Build context string from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Formatted context string
        """
        context_parts = []
        seen_parents = set()

        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            doc_name = metadata.get('document_name', 'Unknown')
            parent_content = metadata.get('parent_content')
            parent_key = None

            if parent_content:
                parent_key = (metadata.get('asset_id'), metadata.get('parent_index'))
                if parent_key in seen_parents:
                    continue
                seen_parents.add(parent_key)
                content = parent_content
            else:
                content = chunk.get('content', '')

            source_index = len(context_parts) + 1
            context_parts.append(f"[مصدر {source_index} - {doc_name}]\n{content}")
        
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
1) Prioritize document context, then use project/SRS profile if available.
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
            answer = await self.llm_provider.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=25000,
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
            async for token in self.llm_provider.generate_text_stream(
                prompt=prompt,
                temperature=0.7,
                max_tokens=25000,
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
        """Build prompt for LLM-only mode (no document context available)."""
        project_profile = AnswerService._build_project_profile(project_context)
        response_style = AnswerService._response_style_from_query(query=query, language=language)
        if language == "ar":
            return f"""أنت مساعد مؤسسي للمشاريع البرمجية. لا توجد مستندات مرفوعة حاليًا، لذا اعتمد على المعرفة العامة + بروفايل المشروع فقط.
القواعد:
1) كن عمليًا ومباشرًا وقدم إجابة تخدم المشروع.
2) لا تدّع وجود مصادر أو استشهادات.
3) إذا كانت المعلومة غير مؤكدة، اذكر ذلك مع افتراض واضح.
4) اختم بخطوة تنفيذية تالية واحدة على الأقل.

بروفايل المشروع:
{project_profile}

أسلوب الإجابة المطلوب:
{response_style}

السؤال:
{query}

الإجابة:"""
        return f"""You are an enterprise project assistant. No documents are currently available, so answer using general knowledge + project profile only.
Rules:
1) Be practical and project-serving.
2) Do not claim sources or citations.
3) If uncertain, state assumptions clearly.
4) End with at least one actionable next step.

Project profile:
{project_profile}

Preferred response style:
{response_style}

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
