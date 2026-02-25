import asyncio
import json
import os
from pprint import pprint

from backend.database.models import ChatMessage
from backend.services.live_patch_service import LivePatchService, LivePatchExtraction

async def main():
    messages = [
        ChatMessage(role="assistant", content="تمام، فهمت إنك محتاج موقع لمطعمك. عشان أقدر أطون معاك، إيه الهدف الأساسي للمطعم؟"),
        ChatMessage(role="user", content='''عشان تبني مشروع مطعم ناجح، المتطلبات بتنقسم لكذا جانب أساسي:
1. القانونية: السجل التجاري والبطاقة الضريبية.
2. التشغيلية: معدات المطبخ، نظام POS، كراسي مريحة.
3. البشرية: الشيف العمومي، طاقم الصالة.
4. الجودة: نظام HACCP، سيستم توريد.
5. التسويق: الهوية البصرية، إنستجرام وفيسبوك، طلبات.''')
    ]
    
    print("Testing extraction...")
    result = await LivePatchService.build_from_messages(
        language="ar",
        messages=messages,
        last_summary={},
        last_coverage={},
    )
    
    print("\n--- EXTRACTED RESULT ---")
    pprint(result)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
