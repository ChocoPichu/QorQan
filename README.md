#==================================================
#           QORQAN - EMPOWERING SAFETY
#==================================================

Project Description:
QorQan is crisis intervention system. 
Unlike simple chatbots, this is a hybrid infrastructure 
designed to facilitate safe, anonymous communication 
between teenagers and a team of professional operators.

Our journey began with a simple bridge but evolved into 
 a full-scale multi-operator system. We realized that 
traditional Telegram group-based support is cluttered 
and unsafe. QorQan solves this by moving operators 
to a dedicated, secure Web Dashboard (The Vault), 
ensuring that kid identities remain protected while 
allowing multiple specialists to manage tickets 
simultaneously.

Core Features:
1. Multi-Operator Support: Managed via admins.json.
2. Dynamic Queueing: Real-time wait time calculation.
3. Media Support: Handling of text and photo evidence.
4. Language Localization: Full RU, KZ, and EN support.
5. Session Auditing: Database-driven chat history.

Key Configuration Files:
- TOKENS.txt: Contains the BOT_TOKEN and the FLASK_SECRET_KEY. 
  This file is highly sensitive and should never be shared.
- admins.json: The brain of the operator team. Add or 
  remove Telegram IDs here to grant operator access 
  to the Web Dashboard.

Structure:
- /main.py         : Entry point for the Telegram Bot.
- /app.py          : Entry point for the Operator Dashboard (Flask).
- /database.py     : Centralized SQLite3 management.
- /handlers.py     : Telegram interaction logic and state management.
- /texts.py        : Multilingual library for all user-facing strings.
- /static/ & /templates/ & /dashboard.py : The frontend + flask backend for the Operator ui.

Setup Instructions:
1. Install Python 3.x.
2. Install dependencies: pip install -r requirements.txt.
3. Populate TOKENS.txt with your API keys.
4. Add operator Telegram IDs to admins.json.
5. Run main.py and dashboard.py concurrently.

Note: The database (qorgan.db) initializes automatically. 
Always backup qorgan.db for legal and auditing purposes.
==================================================
