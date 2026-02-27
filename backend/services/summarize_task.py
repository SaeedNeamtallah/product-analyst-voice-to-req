import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.models import ChatMessage
from backend.providers.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)

async def summarize_old_messages(messages: List[ChatMessage], language: str = "ar") -> str:
    """Takes a list of old ChatMessages and uses standard LLM to generate a rolling context summary."""
    if not messages:
        return ""

    provider = LLMProviderFactory.create_provider()
    
    lines = []
    for msg in messages:
        role = "Client" if msg.role == "user" else "BA"
        lines.append(f"{role}: {str(msg.content)[:500]}...")
        
    conversation = "\n".join(lines)
    
    if language == "ar":
        prompt = f"""قم بتلخيص المحادثة السابقة بين العميل (Client) ومحلل الأعمال (BA) في فقرة واحدة مركزة.
ركز فقط على المتطلبات، القرارات، والسياق المفيد لتكملة المقابلة.
لا تذكر التحيات أو الكلام العرضي.

المحادثة:
{conversation}

الملخص:"""
    else:
        prompt = f"""Summarize the following past conversation between the Client and the Business Analyst (BA) into one concise paragraph.
Focus only on requirements, decisions, and context useful for continuing the interview.
Skip greetings and small talk.

Conversation:
{conversation}

Summary:"""

    try:
        summary = await provider.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=600
        )
        return summary.strip()
    except Exception as e:
        logger.error(f"Rolling summary failed: {e}")
        return ""
