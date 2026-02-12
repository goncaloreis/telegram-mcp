# Telegram MCP Server

This server gives Claude direct access to your Telegram account — read messages, search conversations, send messages, and more. Once installed, you can ask Claude things like "what did Daniel say in the Stellar group today?" or "send a message to [person] saying [thing]".

**10 tools** for full Telegram access. Built by Gonçalo.

---

## What you'll need before starting

- Python 3.10 or higher
- Claude Desktop app installed ([download here](https://claude.ai/download))
- Claude Code installed (see below)
- Your Telegram account (with the app on your phone for verification)
- About 15 minutes

---

## Installation

### Step 1: Install Claude Code

If you don't have Claude Code yet, open your terminal (Terminal on Mac, Command Prompt or PowerShell on Windows) and run:

```bash
npm install -g @anthropic-ai/claude-code
```

If you don't have `npm`, install Node.js first from https://nodejs.org (download the LTS version, run the installer, then try the command above again).

### Step 2: Get your Telegram API credentials

Before starting the installation, you need to get API credentials from Telegram:

1. Go to https://my.telegram.org on your browser
2. Log in with your phone number (the one linked to your Telegram)
3. Click **"API development tools"**
4. Fill in the form:
   - **App title**: anything (e.g., "Claude MCP")
   - **Short name**: anything (e.g., "claudemcp")
   - **Platform**: Desktop
   - **Description**: leave blank or put anything
5. Click **Create application**
6. You'll see your **API ID** (a number) and **API Hash** (a long string). Keep this page open.

### Step 3: Let Claude Code do the rest

Open your terminal and run:

```bash
claude
```

Then paste this prompt:

---

**Prompt to paste into Claude Code:**

```
I need you to install a Telegram MCP server on my machine. Here's what to do:

1. Check that Python 3.10+ is installed (run python3 --version on Mac/Linux, or python --version on Windows)

2. Create a Projects folder in my home directory if it doesn't exist

3. Clone the repo:
   cd ~/Projects (or %USERPROFILE%\Projects on Windows)
   git clone https://github.com/goncaloreis/telegram-mcp.git
   cd telegram-mcp

4. Set up Python virtual environment:
   python3 -m venv venv (or python -m venv venv on Windows)
   Activate it and install requirements: pip install -r requirements.txt

5. Run the session generator:
   python3 generate_session.py (or python generate_session.py on Windows)
   
   This will ask me for:
   - API ID (I have it ready)
   - API Hash (I have it ready)  
   - Phone number (my Telegram number with country code)
   - Verification code (Telegram will send it to my phone)
   
   Wait for me at each prompt. After it completes, it will print a session string — save this.

6. Create the .env file by copying .env.example:
   cp .env.example .env (or copy .env.example .env on Windows)
   
   Then edit .env and fill in:
   - TELEGRAM_API_ID=<my API ID>
   - TELEGRAM_API_HASH=<my API hash>
   - TELEGRAM_SESSION_STRING=<the session string from step 5>

7. Test the server by running: python server.py
   If it starts without errors, Ctrl+C to stop it.

8. Configure Claude Desktop by editing the config file:
   - Mac: ~/Library/Application Support/Claude/claude_desktop_config.json
   - Windows: %APPDATA%\Claude\claude_desktop_config.json
   
   Add this to the mcpServers section (adapt paths for my OS):
   
   On Mac:
   {
     "mcpServers": {
       "telegram": {
         "command": "/bin/bash",
         "args": ["-c", "cd $HOME/Projects/telegram-mcp && source venv/bin/activate && python server.py"]
       }
     }
   }
   
   On Windows:
   {
     "mcpServers": {
       "telegram": {
         "command": "cmd",
         "args": ["/c", "cd /d %USERPROFILE%\\Projects\\telegram-mcp && venv\\Scripts\\activate && python server.py"]
       }
     }
   }

   If the file already has other MCP servers (like google-workspace), merge this into the existing mcpServers object — don't overwrite them.

9. Tell me to restart Claude Desktop (Cmd+Q on Mac, or close fully on Windows) and reopen it.

Start by checking my OS and Python version, then proceed step by step. Ask me if anything is unclear.
```

---

### Step 4: Verify it works

After restarting Claude Desktop, click the tools icon (🔨) at the bottom of the chat input. You should see tools like `telegram_list_chats`, `telegram_read_messages`, `telegram_send_message`, etc.

Try asking Claude: **"List my 5 most recent Telegram chats"**

If it works, you're done! 🎉

---

## Troubleshooting

**"FloodWaitError" during session generation**
Telegram rate-limits login attempts. Wait the indicated time and try again.

**"Session string error" or "auth key not found"**
The session string was probably copied incorrectly. Run `python3 generate_session.py` again.

**Tools don't show up in Claude Desktop**
- Check the config file for typos (especially commas between MCP entries)
- Paste the config into https://jsonlint.com to check it's valid JSON
- Restart Claude Desktop fully

**Any other error**
Paste the error message to Gonçalo on Slack.

---

## What can it do?

Once installed, you can ask Claude things like:

- "What are my most recent Telegram messages?"
- "Search my Telegram for messages about [topic]"
- "What did [person] say in [group] today?"
- "Send a message to [person] saying [thing]"
- "Read the last 10 messages in the Stellar group"
- "Find my conversation with [person]"

Claude will use the tools automatically — you just ask in plain language.

---

## Security notes

- The `.env` file contains your Telegram session string, which is equivalent to being logged in to your account. **Never share this file.**
- The `.gitignore` is configured to exclude `.env` and session files from git.
