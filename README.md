# LeadBot US (Telegram) — warm lead first-touch + handoff to manager

This bot:
- handles **first touch** with warm leads (US market, **USD only**)
- asks **minimal qualifying questions**
- answers basic questions about a listing (based on forwarded post/text you send)
- when enough data is collected (or user asks for a showing) → **sends a lead card to the manager chat** and **pauses** the client conversation

## Tech
- Python 3.10+ (recommended 3.11)
- aiogram v3
- SQLite (aiosqlite)
- Optional: OpenAI for better NLU + voice-to-text

---

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### .env
Required:
- `TELEGRAM_BOT_TOKEN`
- `MANAGER_CHAT_ID` (group/channel/chat id where leads should be sent)

Optional:
- `OPENAI_API_KEY` (for smarter understanding & voice)
- `LLM_MODE=off|on` (default: off)
- `ENABLE_VOICE=0|1` (default: 0)

> Note: if a user has **no @username**, Telegram can't create a `t.me/username` preview card.
> In that case we include a clickable `tg://user?id=...` link in the lead card.

---

## 2) Run

```bash
python main.py
```

---

## 3) Manager chat

1. Create a Telegram group for your managers.
2. Add the bot to the group.
3. Make the bot admin (recommended but not strictly required to send messages).
4. Put that group's numeric id into `MANAGER_CHAT_ID`.

How to find chat id quickly:
- Run the bot, send any message in the group, then look at logs (bot prints updates with chat id).

---

## 4) How it works (high level)

### Client flow
1. Bot asks for a listing: **address / link / forwarded post text**
2. Bot asks minimal questions:
   - People count + occupation
   - Lease term + budget (USD)
   - (optional) pets/children, showing time
3. When ready → sends lead card to manager chat + tells client "manager will contact you" + pauses.

### Listing Q&A
If the client asks things like:
- price / bedrooms
- pets / kids
- broker fee / deposit

Bot answers **only if it sees it in the listing text**; otherwise it says it's not specified and will be clarified by a manager.

---

## 5) Notes
- Channel parsing / ingest is stubbed. For now, bot uses:
  - forwarded post text
  - or any message you mark as listing (address/link)
as the listing context.
