# Telegram MCP Server

MCP server for Telegram User API access via Telethon. Lets Claude read, write, and search your personal Telegram messages.

## Setup

### 1. Get Telegram API credentials

Go to [my.telegram.org](https://my.telegram.org) → API Development Tools → Create application. Note your `api_id` and `api_hash`.

### 2. Install dependencies

```bash
cd /Users/goncaloreis/Projects/telegram-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Generate session string

```bash
python3 generate_session.py
```

This will prompt for your API ID, API hash, phone number, and verification code. Copy the session string it outputs.

### 4. Create .env

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 5. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "/Users/goncaloreis/Projects/telegram-mcp/venv/bin/python",
      "args": ["/Users/goncaloreis/Projects/telegram-mcp/server.py"]
    }
  }
}
```

### 6. Configure Claude Code

Add to `~/.claude/settings.json` under `mcpServers`:

```json
{
  "telegram": {
    "command": "/Users/goncaloreis/Projects/telegram-mcp/venv/bin/python",
    "args": ["/Users/goncaloreis/Projects/telegram-mcp/server.py"]
  }
}
```

## Tools (Phase 1)

| Tool | Description |
|---|---|
| `telegram_list_chats` | List DMs/groups/channels with pagination |
| `telegram_get_chat_info` | Get chat details (title, type, members, description) |
| `telegram_read_messages` | Read messages from a chat (newest first) |
| `telegram_search_messages` | Search within a chat or globally |
| `telegram_read_thread` | Read replies to a specific message |
| `telegram_send_message` | Send a message (supports reply_to, parse_mode) |
| `telegram_edit_message` | Edit a sent message |
| `telegram_delete_message` | Delete a message |
| `telegram_search_contacts` | Search contacts by name/username |
| `telegram_get_user_info` | Get user profile info |

## Security

The session string is equivalent to being logged into your Telegram account. Never commit `.env` to git.
