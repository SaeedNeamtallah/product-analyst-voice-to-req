"""
Answer Generation Service.
Handles generating AI-powered answers using LLM.
"""
from typing import List, Dict, Any, Optional
from backend.providers.llm.factory import LLMProviderFactory
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
        include_sources: bool = True
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
            prompt = self._build_prompt(query, context, language)
            
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
    
    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Build context string from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            doc_name = metadata.get('document_name', 'Unknown')
            
            context_parts.append(f"[مصدر {i} - {doc_name}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str, language: str) -> str:
        """
        Build prompt for LLM.
        
        Args:
            query: User question
            context: Context text
            language: Response language
            
        Returns:
            Formatted prompt
        """
        if language == "ar":
            system_prompt = """أنت مساعد ذكي متخصص في الإجابة على الأسئلة بناءً على المحتوى المقدم.
قم بتحليل السياق المقدم وأجب على السؤال بدقة واحترافية.
إذا لم تجد الإجابة في السياق، قل ذلك بوضوح.
استخدم اللغة العربية الفصحى في إجاباتك."""

            prompt = f"""{system_prompt}

السياق:
{context}

السؤال: {query}

الإجابة:"""
        else:
            system_prompt = """You are an intelligent assistant specialized in answering questions based on provided content.
Analyze the given context and answer the question accurately and professionally.
If you cannot find the answer in the context, state that clearly."""

            prompt = f"""{system_prompt}

Context:
{context}

Question: {query}

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
