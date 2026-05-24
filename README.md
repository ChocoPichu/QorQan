# QorQan — Empowering Safety

QorQan is a **crisis intervention system** designed for safe, anonymous communication between teenagers and a team of professional operators. Unlike simple chatbots, it's a hybrid infrastructure with a dedicated **Web Dashboard** ("The Vault") for operators.

> **Built for:** School projects, crisis hotlines, anonymous support services

---

## Features

- **Multi-Operator Support** — Manage operators via `admins.json`
- **Dynamic Queueing** — Real-time wait-time calculation based on online operators
- **Media Support** — Handle text and photo evidence
- **Language Localization** — Full RU, KZ, and EN support
- **Session Auditing** — SQLite3 database with full chat history
- **Blacklist** — Ban abusive users from the dashboard
- **Unread Badges** — Dashboard shows unread messages per ticket

## Screenshots

*(Add screenshots here — Telegram bot menu, Dashboard login, Ticket queue)*

---

## Quick Start

### Prerequisites

- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/ChocoPichu/QorQan.git
cd QorQan

# 2. Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your BOT_TOKEN and FLASK_SECRET
```

### Configuration

Create a `.env` file in the project root:

```env
BOT_TOKEN="your_telegram_bot_token_here"
FLASK_SECRET="your_random_secret_key_here"
```

### Running

The system has two components that run **simultaneously**:

```bash
# Terminal 1 — Telegram Bot
python main.py

# Terminal 2 — Web Dashboard (http://localhost:5000)
python dashboard.py
```

Or use the convenience script:

```bash
start.bat
```

### Operator Setup

Add operator accounts in `admins.json`:

```json
[
    {
        "username": "operator1",
        "password": "secure_password",
        "display_name": "Alice"
    }
]
```

Login at `http://localhost:5000` with these credentials.

---

## Project Structure

```
QorQan/
├── main.py           # Telegram Bot entry point
├── dashboard.py      # Operator Web Dashboard (Flask)
├── config.py         # Environment config loader
├── database.py       # SQLite3 data access layer
├── handlers.py       # Telegram bot message handlers
├── keyboards.py      # Reply & inline keyboard builders
├── states.py         # FSM state definitions
├── texts.py          # RU/KZ/EN localization strings
├── admins.json       # Operator credentials
├── static/           # Dashboard frontend (CSS, JS)
├── templates/        # Dashboard HTML templates
├── .env              # Sensitive tokens (not committed)
└── requirements.txt  # Python dependencies
```

---

## API Endpoints (Dashboard)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Operator login |
| GET | `/api/tickets` | List tickets (with heartbeat) |
| POST | `/api/ticket/accept` | Accept a waiting ticket |
| POST | `/api/ticket/close` | Close an active ticket |
| GET | `/api/messages/<id>` | Get session messages |
| POST | `/api/messages/send` | Send message to user |
| POST | `/api/messages/mark_read` | Mark messages as read |
| GET | `/api/blacklist` | List banned users |
| POST | `/api/user/ban` | Ban a user |
| POST | `/api/user/unban` | Unban a user |

---

## Tech Stack

- **Bot Framework:** aiogram 3.x (async Telegram Bot API)
- **Dashboard:** Flask 3.x + Jinja2
- **Database:** SQLite3
- **Async HTTP:** aiohttp
- **Validation:** pydantic
- **Auth:** Werkzeug password hashing

---

## FAQ

**Q: Why does the dashboard show "no operators online"?**  
A: Operators must be logged into the dashboard — their presence is tracked every 3 seconds.

**Q: Can I use PostgreSQL instead of SQLite?**  
A: The current implementation uses SQLite. Swap the connection in `database.py` for production.

**Q: Is this safe for production use?**  
A: This is a school project. For production, add HTTPS, rate limiting, and a proper database.

---

## License

Apache-2.0