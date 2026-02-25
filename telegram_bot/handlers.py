"""
Telegram Bot Handlers.
Command and message handlers for the bot using pyTelegramBotAPI.
"""
import asyncio
import json
from io import BytesIO
import httpx
from typing import Any
from telebot import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.database.models import TelegramSession
from telegram_bot.config import bot_settings
import logging

logger = logging.getLogger(__name__)

NO_PROJECT_EN = "No project is linked to this chat yet. Use /newproject first."
NO_PROJECT_AR = "لا يوجد مشروع مربوط بهذه المحادثة بعد. استخدم /newproject أولاً."

MENU_NEW_PROJECT_AR = "➕ مشروع جديد"
MENU_PROJECTS_AR = "📁 المشاريع"
MENU_SRS_NOW_AR = "📄 توليد SRS"
MENU_HELP_AR = "❓ مساعدة"

MENU_NEW_PROJECT_EN = "➕ New Project"
MENU_PROJECTS_EN = "📁 Projects"
MENU_SRS_NOW_EN = "📄 Generate SRS"
MENU_HELP_EN = "❓ Help"

# Bot instance (will be set from bot.py)
bot = None
_session_fallback: dict[int, int] = {}
_auth_token: str | None = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance


from backend.database.connection import async_session_maker

def set_chat_project(chat_id: int, project_id: int) -> None:
    async def _do():
        try:
            async with async_session_maker() as db:
                stmt = select(TelegramSession).where(TelegramSession.chat_id == chat_id)
                existing = await db.scalar(stmt)
                if existing:
                    existing.project_id = project_id
                else:
                    new_session = TelegramSession(chat_id=chat_id, project_id=project_id)
                    db.add(new_session)
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to set telegram session in DB: %s", exc)
            _session_fallback[int(chat_id)] = int(project_id)
    asyncio.run(_do())


def get_chat_project(chat_id: int) -> int | None:
    async def _do():
        try:
            async with async_session_maker() as db:
                stmt = select(TelegramSession).where(TelegramSession.chat_id == chat_id)
                session = await db.scalar(stmt)
                if session:
                    return session.project_id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read telegram session from DB: %s", exc)
        return _session_fallback.get(int(chat_id))
    return asyncio.run(_do())


def _detect_language(text: str) -> str:
    value = str(text or "")
    ar = sum(1 for ch in value if "\u0600" <= ch <= "\u06FF")
    en = sum(1 for ch in value if ("a" <= ch.lower() <= "z"))
    return "ar" if ar >= en else "en"


def _login_headers(force_refresh: bool = False) -> dict:
    global _auth_token
    if _auth_token and not force_refresh:
        return {"Authorization": f"Bearer {_auth_token}"}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{bot_settings.api_base_url}/auth/login",
            json={
                "email": bot_settings.bot_api_email,
                "password": bot_settings.bot_api_password,
            },
        )
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
        _auth_token = str(payload.get("token") or "").strip() or None

    if not _auth_token:
        raise RuntimeError("Telegram bot login failed: empty token")
    return {"Authorization": f"Bearer {_auth_token}"}


def _api_post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=60.0) as client:
        headers = _login_headers()
        response = client.post(
            f"{bot_settings.api_base_url}{path}",
            headers=headers,
            json=payload,
        )
        if response.status_code == 401:
            headers = _login_headers(force_refresh=True)
            response = client.post(
                f"{bot_settings.api_base_url}{path}",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        return response.json()


def _api_post_file(path: str, files: dict, data: dict = None) -> dict:
    with httpx.Client(timeout=120.0) as client:
        headers = _login_headers()
        response = client.post(
            f"{bot_settings.api_base_url}{path}",
            headers=headers,
            files=files,
            data=data,
        )
        if response.status_code == 401:
            headers = _login_headers(force_refresh=True)
            response = client.post(
                f"{bot_settings.api_base_url}{path}",
                headers=headers,
                files=files,
                data=data,
            )
        response.raise_for_status()
        return response.json()


def _api_get_json(path: str) -> dict:
    with httpx.Client(timeout=60.0) as client:
        headers = _login_headers()
        response = client.get(f"{bot_settings.api_base_url}{path}", headers=headers)
        if response.status_code == 401:
            headers = _login_headers(force_refresh=True)
            response = client.get(f"{bot_settings.api_base_url}{path}", headers=headers)
        response.raise_for_status()
        data = response.json() if response.content else {}
        return data if isinstance(data, dict) else {}


def _api_get_raw(path: str) -> tuple[bytes, str | None]:
    with httpx.Client(timeout=120.0) as client:
        headers = _login_headers()
        response = client.get(f"{bot_settings.api_base_url}{path}", headers=headers)
        if response.status_code == 401:
            headers = _login_headers(force_refresh=True)
            response = client.get(f"{bot_settings.api_base_url}{path}", headers=headers)
        response.raise_for_status()
        return response.content, response.headers.get("content-disposition")


def create_new_project(name: str, description: str = "Created from Telegram bot") -> dict:
    payload = {
        "name": str(name).strip(),
        "description": str(description or "").strip(),
    }
    return _api_post("/projects/", payload)


def _build_create_project_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(text="➕ إنشاء مشروع جديد", callback_data="project:new"))
    return markup


def _build_persistent_menu_markup(language: str = "ar") -> types.ReplyKeyboardMarkup:
    is_en = language == "en"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=2)
    markup.row(MENU_NEW_PROJECT_EN if is_en else MENU_NEW_PROJECT_AR, MENU_PROJECTS_EN if is_en else MENU_PROJECTS_AR)
    markup.row(MENU_SRS_NOW_EN if is_en else MENU_SRS_NOW_AR, MENU_HELP_EN if is_en else MENU_HELP_AR)
    return markup


def _resolve_menu_action(text: str) -> str | None:
    value = str(text or "").strip()
    if value in {MENU_NEW_PROJECT_AR, MENU_NEW_PROJECT_EN}:
        return "newproject"
    if value in {MENU_PROJECTS_AR, MENU_PROJECTS_EN}:
        return "projects"
    if value in {MENU_SRS_NOW_AR, MENU_SRS_NOW_EN}:
        return "srsnow"
    if value in {MENU_HELP_AR, MENU_HELP_EN}:
        return "help"
    return None


def _build_srs_actions_markup(language: str) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    label = "📄 Download SRS PDF" if language == "en" else "📄 تنزيل ملف SRS PDF"
    markup.add(types.InlineKeyboardButton(text=label, callback_data="srs:now"))
    return markup


def _resolve_user_language(text_hint: str, telegram_language_code: str | None) -> str:
    hinted = _detect_language(text_hint)
    if hinted in {"ar", "en"}:
        return hinted

    code = str(telegram_language_code or "").strip().lower()
    if code.startswith("ar"):
        return "ar"
    return "en"


def _filename_from_content_disposition(header_value: str | None, fallback: str) -> str:
    raw = str(header_value or "")
    marker = "filename="
    if marker not in raw:
        return fallback
    candidate = raw.split(marker, 1)[1].strip().strip('"').strip("'")
    if not candidate:
        return fallback
    return candidate


def _extract_draft_state(draft_payload: dict | None) -> tuple[dict, dict]:
    if not isinstance(draft_payload, dict):
        return {}, {}
    draft = draft_payload.get("draft") if isinstance(draft_payload.get("draft"), dict) else {}
    summary = draft.get("summary") if isinstance(draft.get("summary"), dict) else {}
    coverage = draft.get("coverage") if isinstance(draft.get("coverage"), dict) else {}
    return summary, coverage


def _no_project_text(language: str) -> str:
    return NO_PROJECT_EN if language == "en" else NO_PROJECT_AR


def _reply_no_project(message, language: str, welcome_prefix: bool = False) -> None:
    body = _no_project_text(language)
    if welcome_prefix and language != "en":
        body = "مرحباً! " + body
    bot.reply_to(message, body, reply_markup=_build_persistent_menu_markup(language))


def _assistant_fallback_text(language: str) -> str:
    return (
        "I need a bit more context to continue."
        if language == "en"
        else "محتاج شوية تفاصيل إضافية علشان أكمل معاك بشكل أدق."
    )


def _srs_refresh_language(language: str) -> str:
    return language if language in {"ar", "en"} else "ar"


def _srs_need_more_details_text(language: str, detail: str) -> str:
    if language == "en":
        base = (
            "⚠️ I need more details before generating SRS. "
            "Please continue the conversation with business requirements, workflows, users, constraints, and goals."
        )
        return f"{base}\n\nDetails: {detail}" if detail else base

    base = (
        "⚠️ محتاج تفاصيل أكتر قبل توليد الـSRS. "
        "كمّل المحادثة بمتطلبات البيزنس، سير العمل، المستخدمين، القيود، والأهداف."
    )
    return f"{base}\n\nالتفاصيل: {detail}" if detail else base


def _srs_parse_error_text(language: str, detail: str) -> str:
    if language == "en":
        base = (
            "⚠️ SRS generation failed due to invalid AI output format (JSON parsing error). "
            "Please retry now; if it repeats, switch the AI provider/model from settings."
        )
        return f"{base}\n\nDetails: {detail}" if detail else base

    base = (
        "⚠️ تعذّر توليد SRS بسبب مخرجات AI غير صالحة بصيغة JSON (JSON parsing error). "
        "جرّب مرة أخرى الآن، وإذا تكرر الخطأ غيّر مزوّد/موديل الذكاء من الإعدادات."
    )
    return f"{base}\n\nالتفاصيل: {detail}" if detail else base


def _is_srs_parse_error(detail: str) -> bool:
    value = str(detail or "").strip().lower()
    if not value:
        return False
    markers = [
        "failed to parse srs json",
        "json parsing",
        "json decode",
        "invalid json",
    ]
    return any(marker in value for marker in markers)


def _safe_http_error_detail(response) -> str:
    if response is None:
        return ""
    try:
        payload = response.json() if response.content else {}
        return str(payload.get("detail") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _refresh_srs_or_explain(project_id: int, user_lang: str) -> str | None:
    try:
        _api_post(
            f"/projects/{project_id}/srs/refresh",
            {"language": _srs_refresh_language(user_lang)},
        )
        return None
    except httpx.HTTPStatusError as refresh_exc:
        response = refresh_exc.response
        if response is not None and response.status_code == 400:
            detail = _safe_http_error_detail(response)
            if _is_srs_parse_error(detail):
                return _srs_parse_error_text(user_lang, detail)
            return _srs_need_more_details_text(user_lang, detail)
        raise


def _save_interview_draft(project_id: int, result: dict, language: str) -> None:
    if not isinstance(result, dict):
        return

    payload = {
        "summary": result.get("summary") if isinstance(result.get("summary"), dict) else {},
        "coverage": result.get("coverage") if isinstance(result.get("coverage"), dict) else {},
        "signals": result.get("signals") if isinstance(result.get("signals"), dict) else {},
        "livePatch": result.get("live_patch") if isinstance(result.get("live_patch"), dict) else {},
        "cycleTrace": result.get("cycle_trace") if isinstance(result.get("cycle_trace"), dict) else {},
        "topicNavigation": result.get("topic_navigation") if isinstance(result.get("topic_navigation"), dict) else {},
        "stage": str(result.get("stage") or "discovery"),
        "mode": False,
        "lastAssistantQuestion": str(result.get("question") or ""),
        "lang": language if language in {"ar", "en"} else "ar",
    }
    _api_post(f"/projects/{project_id}/interview/draft", payload)


def _run_interview_turn(project_id: int, query: str, language: str, source: str) -> str:
    msg_metadata = {"source": source, "language": language}
    if source == "telegram_voice":
        msg_metadata["transcript_confirmed"] = True
    _api_post(
        f"/projects/{project_id}/messages",
        {
            "messages": [
                {
                    "role": "user",
                    "content": query,
                    "metadata": msg_metadata,
                }
            ]
        },
    )

    draft_payload = _api_get_json(f"/projects/{project_id}/interview/draft")
    last_summary, last_coverage = _extract_draft_state(draft_payload)
    result = _api_post(
        f"/projects/{project_id}/interview/next",
        {
            "language": language,
            "last_summary": last_summary,
            "last_coverage": last_coverage,
        },
    )

    _save_interview_draft(project_id=project_id, result=result, language=language)

    assistant_text = str(result.get("question") or "").strip() or _assistant_fallback_text(language)

    _api_post(
        f"/projects/{project_id}/messages",
        {
            "messages": [
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "metadata": {"source": "telegram", "language": language},
                }
            ]
        },
    )
    return assistant_text


def _transcribe_message_media(message) -> str:
    voice = getattr(message, "voice", None)
    audio = getattr(message, "audio", None)
    media = voice or audio
    if media is None:
        return ""

    file_info = bot.get_file(media.file_id)
    downloaded = bot.download_file(file_info.file_path)

    filename = "voice.ogg" if voice is not None else (getattr(audio, "file_name", None) or "audio.mp3")
    mime = "audio/ogg" if voice is not None else "audio/mpeg"

    stt_payload = _api_post_file(
        "/stt/transcribe",
        files={"file": (filename, downloaded, mime)},
        data={"language": "auto"},
    )
    return str(stt_payload.get("text") or "").strip()


def _welcome_after_project_created(project_name: str, project_id: int, language: str) -> str:
    safe_name = str(project_name or "مشروع جديد").strip() or "مشروع جديد"
    if language == "en":
        return (
            "🎉 Welcome to Tawasul AI!\n\n"
            f"✅ Project ready: {safe_name}\n"
            f"🆔 Project ID: {int(project_id)}\n\n"
            "I’m Tawasul Chat. I turn your words into clear business requirements.\n"
            "I can help you define scope, priorities, and key user needs step by step.\n\n"
            "💡 What’s your idea?"
        )

    return (
        "🎉 أهلاً بيك في شات تواصل!\n\n"
        f"✅ مشروعك جاهز: {safe_name}\n"
        f"🆔 رقم المشروع: {int(project_id)}\n\n"
        "أنا شات تواصل، بحوّل كلامك إلى Business Requirements واضحة ومنظمة.\n"
        "هنشتغل معًا على تحديد نطاق المشروع، ترتيب الأولويات، وتجميع احتياجات المستخدم بشكل عملي.\n\n"
        "💡 إيه هي فكرتك؟"
    )


def projects_command(message):
    """Handle /projects command as a create-project CTA (no project listing)."""
    bot.reply_to(
        message,
        "اختر أمرًا من الأزرار بالأسفل. يمكنك إنشاء مشروع جديد فورًا.",
        reply_markup=_build_persistent_menu_markup("ar"),
    )


def handle_project_selection(call):
    """Handle inline keyboard callbacks: project:<id>."""
    data = str(call.data or "")
    if data == "project:new":
        try:
            project_name = "مشروع جديد من تيليجرام"
            created = create_new_project(project_name)
            created_name = str(created.get("name") or project_name)
            project_id = int(created.get("id"))
            user_lang = _resolve_user_language(
                text_hint=created_name,
                telegram_language_code=getattr(call.from_user, "language_code", None),
            )
            set_chat_project(int(call.message.chat.id), project_id)
            bot.answer_callback_query(call.id, "Done ✅" if user_lang == "en" else "تم إنشاء المشروع وربطه ✅")
            bot.edit_message_text(
                _welcome_after_project_created(created_name, project_id, user_lang),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to create telegram project from callback: %s", exc)
            bot.answer_callback_query(call.id, "تعذّر إنشاء مشروع جديد")
        return

    if not data.startswith("project:"):
        return

    try:
        project_id = int(data.split(":", 1)[1])
        set_chat_project(int(call.message.chat.id), project_id)
        bot.answer_callback_query(call.id, "تم ربط المشروع بالمحادثة ✅")
        bot.edit_message_text(
            f"✅ تم اختيار المشروع بنجاح (ID: {project_id}).\nأرسل سؤالك الآن.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to bind telegram chat to project: %s", exc)
        bot.answer_callback_query(call.id, "تعذّر ربط المشروع")

def start_command(message):
    """Handle /start command."""
    bot.reply_to(
        message,
        "مرحباً بك في Tawasul Bot! 🤖\n\n"
        "لبداية سريعة، أنشئ مشروعًا جديدًا عبر /newproject\n"
        "أو استخدم الأزرار الثابتة أسفل الشات.",
        reply_markup=_build_persistent_menu_markup("ar"),
    )

def help_command(message):
    """Handle /help command."""
    bot.reply_to(
        message,
        "📚 دليل الاستخدام\n\n"
        "1) استخدم /newproject لإنشاء مشروع جديد سريعاً.\n"
        "2) أو استخدم /projects لإظهار زر إنشاء مشروع جديد.\n"
        "3) استخدم /srsnow لتوليد SRS الآن وتحميل ملف PDF فورًا.\n"
        "4) أرسل سؤالك كتابةً وسيتم توجيهه للمشروع المختار.",
        reply_markup=_build_persistent_menu_markup("ar"),
    )


def newproject_command(message):
    """Create a new project and bind it to current chat.

    Usage:
      /newproject
      /newproject Project Name
    """
    raw = str(getattr(message, "text", "") or "").strip()
    parts = raw.split(maxsplit=1)
    project_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "مشروع جديد من تيليجرام"
    user_lang = _resolve_user_language(
        text_hint=project_name,
        telegram_language_code=getattr(message.from_user, "language_code", None),
    )

    try:
        created = create_new_project(project_name)
        created_name = str(created.get("name") or project_name)
        project_id = int(created.get("id"))
        set_chat_project(int(message.chat.id), project_id)
        bot.reply_to(
            message,
            _welcome_after_project_created(created_name, project_id, user_lang),
            reply_markup=_build_persistent_menu_markup(user_lang),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create project from /newproject: %s", exc)
        bot.reply_to(
            message,
            "❌ تعذّر إنشاء مشروع جديد حالياً. حاول مرة أخرى.",
            reply_markup=_build_persistent_menu_markup(user_lang),
        )


def srsnow_command(message):
    """Generate latest SRS now and send PDF to user for current chat-bound project."""
    chat_id = int(message.chat.id)
    project_id = get_chat_project(chat_id)
    user_lang = _resolve_user_language(
        text_hint=str(getattr(message, "text", "") or ""),
        telegram_language_code=getattr(message.from_user, "language_code", None),
    )

    if not project_id:
        bot.reply_to(message, _no_project_text(user_lang), reply_markup=_build_persistent_menu_markup(user_lang))
        return

    progress_text = (
        "⏳ Generating SRS now and preparing PDF..."
        if user_lang == "en"
        else "⏳ جاري توليد SRS الآن وتجهيز ملف PDF..."
    )
    thinking_msg = bot.reply_to(message, progress_text)

    _generate_and_send_srs_pdf(
        chat_id=message.chat.id,
        project_id=project_id,
        user_lang=user_lang,
        progress_message_id=thinking_msg.message_id,
    )


def _generate_and_send_srs_pdf(*, chat_id: int, project_id: int, user_lang: str, progress_message_id: int) -> None:
    try:
        explain = _refresh_srs_or_explain(project_id, user_lang)
        if explain:
            bot.edit_message_text(explain, chat_id=chat_id, message_id=progress_message_id)
            return

        pdf_bytes, content_disposition = _api_get_raw(f"/projects/{project_id}/srs/export")
        filename = _filename_from_content_disposition(
            content_disposition,
            fallback=f"srs_project_{int(project_id)}.pdf",
        )

        bot.send_document(
            chat_id=chat_id,
            document=BytesIO(pdf_bytes),
            visible_file_name=filename,
            caption=(
                "✅ SRS generated and PDF is ready."
                if user_lang == "en"
                else "✅ تم توليد SRS بنجاح، وده ملف الـ PDF."
            ),
        )

        done_text = (
            "Done. You can run /srsnow any time during the conversation."
            if user_lang == "en"
            else "تم بنجاح. تقدر تستخدم /srsnow في أي وقت أثناء المحادثة."
        )
        bot.edit_message_text(done_text, chat_id=chat_id, message_id=progress_message_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to generate/export SRS from Telegram command: %s", exc)
        error_text = (
            "❌ Could not generate SRS/PDF right now. Please try again in a moment."
            if user_lang == "en"
            else "❌ تعذّر توليد SRS أو ملف PDF حالياً. حاول مرة أخرى بعد قليل."
        )
        bot.edit_message_text(error_text, chat_id=chat_id, message_id=progress_message_id)


def handle_srs_action(call):
    """Handle SRS callbacks (currently: srs:now)."""
    data = str(call.data or "")
    if data != "srs:now":
        return

    chat_id = int(call.message.chat.id)
    project_id = get_chat_project(chat_id)
    user_lang = _resolve_user_language(
        text_hint=str(getattr(call.message, "text", "") or ""),
        telegram_language_code=getattr(call.from_user, "language_code", None),
    )

    if not project_id:
        bot.answer_callback_query(call.id, "No project" if user_lang == "en" else "لا يوجد مشروع")
        bot.send_message(chat_id, _no_project_text(user_lang), reply_markup=_build_persistent_menu_markup(user_lang))
        return

    bot.answer_callback_query(call.id, "Generating SRS..." if user_lang == "en" else "جاري توليد SRS...")
    progress = bot.send_message(
        chat_id,
        "⏳ Generating SRS now and preparing PDF..."
        if user_lang == "en"
        else "⏳ جاري توليد SRS الآن وتجهيز ملف PDF...",
    )
    _generate_and_send_srs_pdf(
        chat_id=chat_id,
        project_id=project_id,
        user_lang=user_lang,
        progress_message_id=progress.message_id,
    )

def handle_message(message):
    """Handle text messages through interview flow (like web chat)."""
    menu_action = _resolve_menu_action(str(getattr(message, "text", "") or ""))
    if menu_action == "newproject":
        newproject_command(message)
        return
    if menu_action == "projects":
        projects_command(message)
        return
    if menu_action == "srsnow":
        srsnow_command(message)
        return
    if menu_action == "help":
        help_command(message)
        return

    # Ignore commands
    raw_text = str(getattr(message, "text", "") or "")
    if raw_text.startswith('/'):
        return

    chat_id = int(message.chat.id)
    project_id = get_chat_project(chat_id)

    if not project_id:
        _reply_no_project(message, "ar", welcome_prefix=True)
        return

    query = str(message.text or "").strip()
    if not query:
        return

    language = _resolve_user_language(
        text_hint=query,
        telegram_language_code=getattr(message.from_user, "language_code", None),
    )
    
    # Send thinking message
    thinking_msg = bot.reply_to(
        message,
        "🤔 Thinking..." if language == "en" else "🤔 جاري تحليل ردك وبناء السؤال التالي...",
    )
    
    try:
        assistant_text = _run_interview_turn(project_id, query, language, source="telegram")

        answer = f"💬 {assistant_text}"
        
        bot.edit_message_text(
            answer,
            chat_id=message.chat.id,
            message_id=thinking_msg.message_id,
            reply_markup=_build_srs_actions_markup(language),
        )
        
    except Exception as e:
        logger.error("Error in telegram interview flow: %s", e)
        bot.edit_message_text(
            "❌ حدث خطأ في معالجة السؤال. حاول مرة أخرى بعد قليل.",
            chat_id=message.chat.id,
            message_id=thinking_msg.message_id
        )


def handle_voice(message):
    """Handle Telegram voice/audio using backend STT endpoint, then continue interview flow."""
    chat_id = int(message.chat.id)
    project_id = get_chat_project(chat_id)
    language = _resolve_user_language(
        text_hint="",
        telegram_language_code=getattr(message.from_user, "language_code", None),
    )

    if not project_id:
        _reply_no_project(message, language)
        return

    if getattr(message, "voice", None) is None and getattr(message, "audio", None) is None:
        bot.reply_to(
            message,
            "No voice/audio file found in this message."
            if language == "en"
            else "لا يوجد ملف صوت في هذه الرسالة.",
        )
        return

    thinking_msg = bot.reply_to(
        message,
        "🎤 Transcribing your voice..."
        if language == "en"
        else "🎤 جاري تفريغ الصوت إلى نص...",
    )

    try:
        query = _transcribe_message_media(message)
        if not query:
            bot.edit_message_text(
                "Could not transcribe this audio. Please try again with clearer voice."
                if language == "en"
                else "لم أستطع تحويل الصوت إلى نص. حاول مرة أخرى بصوت أوضح.",
                chat_id=message.chat.id,
                message_id=thinking_msg.message_id,
            )
            return
        assistant_text = _run_interview_turn(project_id, query, language, source="telegram_voice")

        bot.edit_message_text(
            (
                "📝 You said:\n"
                f"{query}\n\n"
                f"💬 {assistant_text}"
            )
            if language == "en"
            else (
                "📝 أنت قلت:\n"
                f"{query}\n\n"
                f"💬 {assistant_text}"
            ),
            chat_id=message.chat.id,
            message_id=thinking_msg.message_id,
            reply_markup=_build_srs_actions_markup(language),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error in telegram voice flow: %s", exc)
        bot.edit_message_text(
            "❌ Could not process this voice message right now."
            if language == "en"
            else "❌ تعذّر معالجة الرسالة الصوتية حالياً.",
            chat_id=message.chat.id,
            message_id=thinking_msg.message_id,
        )
