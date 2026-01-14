from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Dict
import random

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import Message

from app.config import settings
from app.db import load_lead, reset_lead, save_lead
from app.lead_logic import decide_reply, Q1, FINAL
from app.llm import llm
from app.models import LeadState

_reminders: Dict[int, asyncio.Task] = {}


async def human_delay():
    # 10–15 seconds random pause
    await asyncio.sleep(random.randint(10, 15))


def is_admin(m: Message) -> bool:
    """If ADMIN_USER_ID is set, only that user can run admin/debug commands."""
    if settings.ADMIN_USER_ID is None:
        return True
    return bool(m.from_user) and m.from_user.id == settings.ADMIN_USER_ID


def build_bot() -> Bot:
    # aiogram 3.7+ removed parse_mode from Bot initializer
    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher(bot: Bot) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(F.text == "/id")
    async def cmd_id(m: Message):
        if not is_admin(m):
            return
        uid = m.from_user.id if m.from_user else None
        await m.answer(f"chat_id={m.chat.id}\nuser_id={uid}")

    @dp.message(F.text.in_({"/test_leads", "/test_manager"}))
    async def cmd_test_leads(m: Message):
        if not is_admin(m):
            await m.answer("Нет доступа.")
            return
        try:
            await bot.send_message(settings.LEADS_CHAT_ID, "✅ Test lead destination (/test_leads)")
            await m.answer("Ок — смог отправить тестовое сообщение в LEADS_CHAT_ID.")
        except Exception as e:
            await m.answer(
                "Не смог отправить сообщение в LEADS_CHAT_ID. Проверь:\n"
                "1) LEADS_CHAT_ID (для группы/канала обычно отрицательный id вида -100...)\n"
                "2) бот добавлен в группу/канал и имеет право писать\n"
                "3) если LEADS_CHAT_ID = user_id человека — человек должен нажать /start у бота\n\n"
                f"Ошибка: {type(e).__name__}: {e}"
            )

    @dp.message(F.text == "/start")
    async def start(m: Message):
        await reset_lead(m.chat.id)
        _cancel_reminder(m.chat.id)
        await human_delay()
        await m.answer(Q1)

    @dp.message(F.text == "/reset")
    async def reset(m: Message):
        await reset_lead(m.chat.id)
        _cancel_reminder(m.chat.id)
        await human_delay()
        await m.answer(Q1)

    @dp.message(F.voice | F.audio | F.video_note)
    async def handle_voice(m: Message):
        # Voice -> transcribe -> treat as text
        if not settings.ENABLE_VOICE:
            await m.answer("Пожалуйста, напишите текстом 😊")
            return
        if not settings.OPENAI_API_KEY:
            await m.answer("Распознавание голоса недоступно. Напишите, пожалуйста, текстом 😊")
            return

        media = m.voice or m.audio or m.video_note
        if not media:
            await m.answer("Не получилось прочитать аудио. Напишите, пожалуйста, текстом 😊")
            return

        tg_file = await bot.get_file(media.file_id)
        with tempfile.TemporaryDirectory() as td:
            _, ext = os.path.splitext(tg_file.file_path or "")
            ext = ext if ext else ".ogg"
            in_path = os.path.join(td, "in" + ext)

            await bot.download_file(tg_file.file_path, in_path)

            text = llm.transcribe(in_path)
            if not text:
                await m.answer("Не смог распознать. Можете написать текстом?")
                return

            await _handle_text_like(m, text.strip(), bot)

    @dp.message(F.text)
    async def handle_text(m: Message):
        text = (m.text or "").strip()

        # Treat "start" text as a reset + first question
        if text.lower() in {"start", "старт", "начать"}:
            await reset_lead(m.chat.id)
            _cancel_reminder(m.chat.id)
            await human_delay()
            await m.answer(Q1)
            return

        await _handle_text_like(m, text, bot)

    async def _handle_text_like(m: Message, text: str, bot: Bot):
        _cancel_reminder(m.chat.id)

        lead = await load_lead(m.chat.id)
        if lead is None:
            lead = LeadState(
                chat_id=m.chat.id,
                user_id=m.from_user.id if m.from_user else m.chat.id,
                username=m.from_user.username if m.from_user else None,
                first_name=m.from_user.first_name if m.from_user else None,
            )

        # If already paused/handoffed — stay polite
        if getattr(lead, "paused", False) or getattr(lead, "handoff_sent", False):
            await m.answer(FINAL)
            return

        # ✅ AUTO-START: if user wrote anything but dialog hasn't started yet, ask Q1 immediately
        # (Do NOT treat this first message as an answer — reduces "botty" behavior)
        if not lead.last_question:
            lead.last_question = Q1
            await save_lead(lead)
            await human_delay()
            await m.answer(Q1)
            return

        reply, next_q, do_handoff, _pause_flag = decide_reply(lead, text)

        if do_handoff and not lead.handoff_sent:
            ok = await send_lead_to_manager(bot, lead)
            if ok:
                lead.handoff_sent = True
                lead.paused = True
            else:
                lead.handoff_sent = False
                lead.paused = False
                reply = (
                    "Я собрал данные, но не смог отправить менеджеру (техническая ошибка). "
                    "Пожалуйста, напишите /test_leads.\n\n" + (next_q or Q1)
                )

        await save_lead(lead)
        await human_delay()
        await m.answer(reply)

        # Reminder while collecting
        if settings.REMINDER_MINUTES and settings.REMINDER_MINUTES > 0 and next_q and not lead.handoff_sent:
            _reminders[m.chat.id] = asyncio.create_task(
                remind_if_no_response(bot, lead.chat_id, settings.REMINDER_MINUTES)
            )

    return dp


def _cancel_reminder(chat_id: int) -> None:
    t = _reminders.pop(chat_id, None)
    if t and not t.done():
        t.cancel()


async def remind_if_no_response(bot: Bot, chat_id: int, minutes: int) -> None:
    try:
        await asyncio.sleep(minutes * 60)
        lead = await load_lead(chat_id)
        if not lead or lead.handoff_sent or lead.paused:
            return
        if lead.last_question:
            await bot.send_message(chat_id, "Напомню 😊 " + lead.last_question)
    except asyncio.CancelledError:
        return


def lead_card_text(lead: LeadState) -> str:
    parts = ["🟢 <b>НОВЫЙ ЛИД</b>"]

    if lead.people_count:
        parts.append(f"👥 <b>Кол-во человек:</b> {lead.people_count}")
    if lead.move_in:
        parts.append(f"📦 <b>Заселение:</b> {lead.move_in}")
    if lead.employment:
        parts.append(f"💼 <b>Кем работает/статус:</b> {lead.employment}")
    if getattr(lead, "showing_text", None):
        parts.append(f"🕒 <b>Показ (как написал клиент):</b> {lead.showing_text}")
    if getattr(lead, "showing_time", None):
        parts.append(f"🧭 <b>Показ (нормализовано):</b> {lead.showing_time}")

    if lead.username:
        parts.append(f"🔗 <b>Ссылка на клиента:</b> https://t.me/{lead.username}")
    parts.append(f"🆔 <b>tg://user?id=</b>{lead.user_id}")
    return "\n".join(parts)


async def send_lead_to_manager(bot: Bot, lead: LeadState) -> bool:
    try:
        await bot.send_message(settings.LEADS_CHAT_ID, lead_card_text(lead))
        return True
    except Exception as e:
        print(f"[manager_send_error] {type(e).__name__}: {e}")
        return False
