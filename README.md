# Telegram MCP Server

This server gives Claude direct access to your Telegram account — read messages, search conversations, send messages, and more. Once installed, you can ask Claude things like "what did Daniel say in the Stellar group today?" or "send a message to [person] saying [thing]".

**10 tools** for full Telegram access. Built by Gonçalo.

---

## What you'll need before starting

- A Mac (these instructions are for macOS)
- Python 3.10 or higher (check with `python3 --version` in Terminal)
- Claude Desktop app installed ([download here](https://claude.ai/download) if you don't have it)
- Your Telegram account (with the app installed on your phone for verification)
- About 15 minutes

---

## Installation — step by step

### Step 1: Open Terminal

Press `Cmd + Space`, type "Terminal", and hit Enter.

### Step 2: Check that Python is installed

```bash
python3 --version
```

You should see something like `Python 3.11.4`. If you get "command not found":
- Go to https://www.python.org/downloads/
- Download and install the latest version for macOS
- Close and reopen Terminal, then try again

### Step 3: Create a folder for MCP servers

```bash
mkdir -p ~/Projects
```

### Step 4: Download the code

```bash
cd ~/Projects
git clone https://github.com/goncaloreis/telegram-mcp.git
cd telegram-mcp
```

If you get "git: command not found", run `xcode-select --install` first, then try again.

### Step 5: Set up the Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Wait for all packages to install.

### Step 6: Get your Telegram API credentials

1. Go to https://my.telegram.org on your browser
2. Log in with your phone number (the one linked to your Telegram)
3. Click **"API development tools"**
4. Fill in the form:
   - **App title**: anything (e.g., "Claude MCP")
   - **Short name**: anything (e.g., "claudemcp")
   - **Platform**: Desktop
   - **Description**: leave blank or put anything
5. Click **Create application**
6. You'll see your **API ID** (a number) and **API Hash** (a long string). Keep this page open — you'll need both values.

### Step 7: Generate your session string

Make sure you're in the project folder with the virtual environment active:

```bash
cd ~/Projects/telegram-mcp
source venv/bin/activate
python3 generate_session.py
```

It will ask you for:
1. **API ID** — paste the number from Step 6
2. **API Hash** — paste the hash from Step 6
3. **Phone number** — your Telegram phone number (with country code, e.g., +351912345678)
4. **Verification code** — Telegram will send you a code in the app, enter it here

After that, it will print a long string starting with something like `1BVtsO...`. **Copy this entire string** — this is your session string.

⚠️ **This session string is like a password to your Telegram account. Never share it with anyone.**

### Step 8: Create the .env file

```bash
cp .env.example .env
```

Now open the `.env` file in a text editor:

```bash
open -a TextEdit .env
```

Replace the placeholder values with your real ones:

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_SESSION_STRING=1BVtsO...your_long_session_string_here...
```

Save and close.

### Step 9: Test that it works

```bash
python3 server.py
```

If you see the server start without errors, it's working. Press `Ctrl + C` to stop it.

### Step 10: Connect it to Claude Desktop

Open the Claude config file:

```bash
open -a TextEdit ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

If you already have the Google Workspace MCP installed, your file will look something like this. **Add the telegram section** inside `mcpServers`:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "cd $HOME/Projects/google-workspace-mcp && source venv/bin/activate && python server.py"
      ]
    },
    "telegram": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "cd $HOME/Projects/telegram-mcp && source venv/bin/activate && python server.py"
      ]
    }
  }
}
```

If this is your only MCP, use:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "cd $HOME/Projects/telegram-mcp && source venv/bin/activate && python server.py"
      ]
    }
  }
}
```

Save and close.

### Step 11: Restart Claude Desktop

Quit Claude Desktop completely (`Cmd + Q`) and reopen it.

### Step 12: Verify it works

Click the tools icon (🔨) at the bottom of the chat input in Claude. You should see tools like `telegram_list_chats`, `telegram_read_messages`, `telegram_send_message`, etc.

Try asking Claude: **"List my 5 most recent Telegram chats"**

If it works, you're done! 🎉

---

## Troubleshooting

**"I don't see Telegram tools in Claude"**
- Check the config file for typos (especially commas between MCP entries)
- Make sure the JSON is valid — you can paste it into https://jsonlint.com to check
- Restart Claude Desktop fully (`Cmd + Q`, then reopen)

**"Session string error" or "auth key not found"**
- Your session string may have been copied incorrectly. Run `python3 generate_session.py` again

**"FloodWaitError"**
- Telegram rate-limits login attempts. Wait the indicated time and try again

**"Python not found" or "venv not found"**
- Make sure Python 3.10+ is installed
- Use `python3` instead of `python`

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

## Security note

The `.env` file contains your Telegram session string, which is equivalent to being logged in to your Telegram account. **Never share this file or commit it to git.** The `.gitignore` is already configured to exclude it.
