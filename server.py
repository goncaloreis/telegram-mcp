#!/usr/bin/env python3
"""
Telegram MCP Server (v1 - Phase 1)

10 TOOLS - CORE TELEGRAM USER API ACCESS

Tools:
  - Chat Management (2):
    * telegram_list_chats - List DMs/groups/channels with pagination
    * telegram_get_chat_info - Get chat details (title, type, members, description)

  - Reading Messages (3):
    * telegram_read_messages - Read messages from a chat (reverse chronological)
    * telegram_search_messages - Search within a chat or globally
    * telegram_read_thread - Read replies to a specific message

  - Writing Messages (3):
    * telegram_send_message - Send a message (with optional reply_to, parse_mode)
    * telegram_edit_message - Edit a sent message
    * telegram_delete_message - Delete a message

  - Contacts & Users (2):
    * telegram_search_contacts - Search contacts by name/username
    * telegram_get_user_info - Get user profile info

INSTALLATION:
1. Get API credentials from https://my.telegram.org
2. Run: python3 generate_session.py
3. Copy session string to .env
4. Run: python3 server.py
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    User, Chat, Channel,
    MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage,
    MessageMediaGeo, MessageMediaContact, MessageMediaPoll,
    PeerUser, PeerChat, PeerChannel,
    UserStatusOnline, UserStatusOffline, UserStatusRecently,
    UserStatusLastWeek, UserStatusLastMonth,
)
from telethon.tl.functions.contacts import SearchRequest
from telethon.errors import (
    ChatAdminRequiredError, ChannelPrivateError,
    MessageNotModifiedError, MessageAuthorRequiredError,
)

# Load .env from the same directory as server.py
SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram credentials from environment
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
SESSION_STRING = os.environ.get("TELEGRAM_SESSION_STRING")


# ==================== HELPERS ====================

def resolve_chat_id(chat_id_raw):
    """Convert chat_id from string/int to the appropriate type for Telethon."""
    if isinstance(chat_id_raw, str):
        # Try to parse as int, otherwise treat as username
        try:
            return int(chat_id_raw)
        except ValueError:
            # Username — strip leading @ if present
            return chat_id_raw.lstrip("@")
    return chat_id_raw


def format_timestamp(dt):
    """Format a datetime to a readable UTC string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def get_media_type(message):
    """Get a human-readable media type string from a message."""
    media = message.media
    if media is None:
        return None
    if isinstance(media, MessageMediaPhoto):
        return "photo"
    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc:
            for attr in doc.attributes:
                attr_type = type(attr).__name__
                if attr_type == "DocumentAttributeVideo":
                    return "video"
                if attr_type == "DocumentAttributeAudio":
                    if getattr(attr, "voice", False):
                        return "voice"
                    return "audio"
                if attr_type == "DocumentAttributeSticker":
                    return "sticker"
                if attr_type == "DocumentAttributeAnimated":
                    return "gif"
            return "document"
    if isinstance(media, MessageMediaWebPage):
        return "webpage"
    if isinstance(media, MessageMediaGeo):
        return "location"
    if isinstance(media, MessageMediaContact):
        return "contact"
    if isinstance(media, MessageMediaPoll):
        return "poll"
    return "other"


def get_user_status(user):
    """Get a human-readable online status from a User object."""
    if user is None or not hasattr(user, "status") or user.status is None:
        return "unknown"
    status = user.status
    if isinstance(status, UserStatusOnline):
        return "online"
    if isinstance(status, UserStatusOffline):
        return f"offline (last seen {format_timestamp(status.was_online)})"
    if isinstance(status, UserStatusRecently):
        return "recently"
    if isinstance(status, UserStatusLastWeek):
        return "last week"
    if isinstance(status, UserStatusLastMonth):
        return "last month"
    return "unknown"


def get_sender_name(sender):
    """Get a display name from a sender entity."""
    if sender is None:
        return "Unknown"
    if isinstance(sender, User):
        parts = [sender.first_name or "", sender.last_name or ""]
        name = " ".join(p for p in parts if p)
        return name or sender.username or str(sender.id)
    if isinstance(sender, (Chat, Channel)):
        return sender.title or str(sender.id)
    return str(getattr(sender, "id", "Unknown"))


async def format_message(message):
    """Format a Telethon message into a dict for JSON output."""
    sender = await message.get_sender()
    sender_name = get_sender_name(sender)
    sender_id = sender.id if sender else None

    result = {
        "id": message.id,
        "sender_name": sender_name,
        "sender_id": sender_id,
        "date": format_timestamp(message.date),
        "text": message.text or "",
    }

    if message.reply_to:
        result["reply_to_msg_id"] = message.reply_to.reply_to_msg_id

    media_type = get_media_type(message)
    if media_type:
        result["media_type"] = media_type

    if message.forward:
        result["forwarded"] = True

    return result


def get_chat_type(dialog_or_entity):
    """Determine chat type from a dialog or entity."""
    entity = getattr(dialog_or_entity, "entity", dialog_or_entity)
    if isinstance(entity, Channel):
        if entity.megagroup:
            return "group"
        return "channel"
    if isinstance(entity, Chat):
        return "group"
    if isinstance(entity, User):
        if entity.bot:
            return "bot"
        return "user"
    return "unknown"


# ==================== CLIENT WRAPPER ====================

class TelegramClientWrapper:
    """Wrapper around Telethon's TelegramClient for the MCP server."""

    def __init__(self):
        self.client: Optional[TelethonClient] = None

    async def connect(self) -> bool:
        """Connect to Telegram using StringSession."""
        try:
            if not API_ID or not API_HASH or not SESSION_STRING:
                logger.error("Missing TELEGRAM_API_ID, TELEGRAM_API_HASH, or TELEGRAM_SESSION_STRING")
                return False

            self.client = TelethonClient(
                StringSession(SESSION_STRING),
                int(API_ID),
                API_HASH,
            )
            await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.error("Session is not authorized. Re-run generate_session.py")
                return False

            me = await self.client.get_me()
            logger.info(f"Connected as {me.first_name} (@{me.username})")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client:
            await self.client.disconnect()


telegram = TelegramClientWrapper()
server = Server("telegram-mcp")


# ==================== TOOL DEFINITIONS ====================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        # ==================== CHAT MANAGEMENT ====================
        Tool(
            name="telegram_list_chats",
            description="List all chats (DMs, groups, channels) with pagination. Returns chat ID, title, unread count, type, and last message preview.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max chats to return (default 20)", "default": 20},
                    "chat_type": {"type": "string", "description": "Filter by type: 'user', 'group', 'channel', 'bot' (optional)", "enum": ["user", "group", "channel", "bot"]},
                    "offset_id": {"type": "integer", "description": "Offset dialog ID for pagination (optional)"},
                },
                "required": []
            }
        ),
        Tool(
            name="telegram_get_chat_info",
            description="Get detailed info about a specific chat. Returns title, type, member count, description, pinned message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID (integer) or @username (string)"},
                },
                "required": ["chat_id"]
            }
        ),

        # ==================== READING MESSAGES ====================
        Tool(
            name="telegram_read_messages",
            description="Read messages from a chat in reverse chronological order (newest first). Returns message ID, sender, timestamp, text, media type, reply info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID (integer) or @username (string)"},
                    "limit": {"type": "integer", "description": "Max messages to return (default 20)", "default": 20},
                    "offset_id": {"type": "integer", "description": "Return messages older than this message ID (for pagination)"},
                    "min_date": {"type": "string", "description": "Only messages after this date (YYYY-MM-DD)"},
                    "max_date": {"type": "string", "description": "Only messages before this date (YYYY-MM-DD)"},
                },
                "required": ["chat_id"]
            }
        ),
        Tool(
            name="telegram_search_messages",
            description="Search messages within a specific chat or globally across all chats. Returns matching messages with context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text"},
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID to search in (optional — omit for global search)"},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                    "from_user": {"type": ["integer", "string"], "description": "Filter by sender ID or @username (optional)"},
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="telegram_read_thread",
            description="Read replies to a specific message (thread). Returns the parent message and all replies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID (integer) or @username (string)"},
                    "message_id": {"type": "integer", "description": "ID of the parent message to read replies for"},
                    "limit": {"type": "integer", "description": "Max replies to return (default 20)", "default": 20},
                },
                "required": ["chat_id", "message_id"]
            }
        ),

        # ==================== WRITING MESSAGES ====================
        Tool(
            name="telegram_send_message",
            description="Send a message to a chat. Supports reply_to and parse_mode (markdown/html).",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID (integer) or @username (string)"},
                    "text": {"type": "string", "description": "Message text to send"},
                    "reply_to": {"type": "integer", "description": "Message ID to reply to (optional)"},
                    "parse_mode": {"type": "string", "description": "Parse mode: 'markdown' or 'html' (optional)", "enum": ["markdown", "html"]},
                },
                "required": ["chat_id", "text"]
            }
        ),
        Tool(
            name="telegram_edit_message",
            description="Edit a previously sent message. You can only edit your own messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID (integer) or @username (string)"},
                    "message_id": {"type": "integer", "description": "ID of the message to edit"},
                    "new_text": {"type": "string", "description": "New text for the message"},
                    "parse_mode": {"type": "string", "description": "Parse mode: 'markdown' or 'html' (optional)", "enum": ["markdown", "html"]},
                },
                "required": ["chat_id", "message_id", "new_text"]
            }
        ),
        Tool(
            name="telegram_delete_message",
            description="Delete a message. You can delete your own messages in any chat, or any message in groups where you're an admin.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": ["integer", "string"], "description": "Chat ID (integer) or @username (string)"},
                    "message_id": {"type": "integer", "description": "ID of the message to delete"},
                },
                "required": ["chat_id", "message_id"]
            }
        ),

        # ==================== CONTACTS & USERS ====================
        Tool(
            name="telegram_search_contacts",
            description="Search your Telegram contacts by name or username.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (name or username)"},
                    "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="telegram_get_user_info",
            description="Get detailed profile info for a Telegram user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": ["integer", "string"], "description": "User ID (integer) or @username (string)"},
                },
                "required": ["user_id"]
            }
        ),
    ]


# ==================== TOOL DISPATCHER ====================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if not telegram.client or not telegram.client.is_connected():
        return [TextContent(type="text", text="Not connected to Telegram. Please restart the server.")]

    try:
        # Chat Management
        if name == "telegram_list_chats":
            return await handle_list_chats(arguments)
        elif name == "telegram_get_chat_info":
            return await handle_get_chat_info(arguments)

        # Reading Messages
        elif name == "telegram_read_messages":
            return await handle_read_messages(arguments)
        elif name == "telegram_search_messages":
            return await handle_search_messages(arguments)
        elif name == "telegram_read_thread":
            return await handle_read_thread(arguments)

        # Writing Messages
        elif name == "telegram_send_message":
            return await handle_send_message(arguments)
        elif name == "telegram_edit_message":
            return await handle_edit_message(arguments)
        elif name == "telegram_delete_message":
            return await handle_delete_message(arguments)

        # Contacts & Users
        elif name == "telegram_search_contacts":
            return await handle_search_contacts(arguments)
        elif name == "telegram_get_user_info":
            return await handle_get_user_info(arguments)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except ChatAdminRequiredError:
        return [TextContent(type="text", text="Error: Admin privileges required for this action.")]
    except ChannelPrivateError:
        return [TextContent(type="text", text="Error: This channel/group is private or you're not a member.")]
    except MessageNotModifiedError:
        return [TextContent(type="text", text="Error: Message content is the same — nothing to update.")]
    except MessageAuthorRequiredError:
        return [TextContent(type="text", text="Error: You can only edit/delete your own messages.")]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ==================== TOOL HANDLERS ====================

# --- Chat Management ---

async def handle_list_chats(args: dict) -> list[TextContent]:
    limit = args.get("limit", 20)
    chat_type_filter = args.get("chat_type")
    offset_id = args.get("offset_id", 0)

    dialogs = await telegram.client.get_dialogs(limit=limit, offset_id=offset_id)

    results = []
    for d in dialogs:
        ctype = get_chat_type(d)

        if chat_type_filter and ctype != chat_type_filter:
            continue

        chat_info = {
            "id": d.id,
            "title": d.title or d.name,
            "type": ctype,
            "unread_count": d.unread_count,
        }

        # Last message preview
        if d.message and d.message.text:
            chat_info["last_message"] = d.message.text[:100]
            chat_info["last_message_date"] = format_timestamp(d.message.date)

        results.append(chat_info)

    return [TextContent(type="text", text=json.dumps(results, indent=2, ensure_ascii=False))]


async def handle_get_chat_info(args: dict) -> list[TextContent]:
    chat_id = resolve_chat_id(args["chat_id"])
    entity = await telegram.client.get_entity(chat_id)

    info = {
        "id": entity.id,
        "type": get_chat_type(entity),
    }

    if isinstance(entity, User):
        info["first_name"] = entity.first_name
        info["last_name"] = entity.last_name
        info["username"] = entity.username
        info["phone"] = entity.phone
        info["bot"] = entity.bot
        info["status"] = get_user_status(entity)
    elif isinstance(entity, (Chat, Channel)):
        info["title"] = entity.title
        if isinstance(entity, Channel):
            info["username"] = entity.username
            info["megagroup"] = entity.megagroup
        if hasattr(entity, "participants_count") and entity.participants_count:
            info["member_count"] = entity.participants_count

    # Try to get full info for description/about
    try:
        if isinstance(entity, Channel):
            from telethon.tl.functions.channels import GetFullChannelRequest
            full = await telegram.client(GetFullChannelRequest(entity))
            info["description"] = full.full_chat.about
            if full.full_chat.participants_count:
                info["member_count"] = full.full_chat.participants_count
        elif isinstance(entity, Chat):
            from telethon.tl.functions.messages import GetFullChatRequest
            full = await telegram.client(GetFullChatRequest(entity.id))
            info["description"] = full.full_chat.about
            if full.full_chat.participants_count:
                info["member_count"] = full.full_chat.participants_count
    except Exception:
        pass

    # Get pinned message
    try:
        async for msg in telegram.client.iter_messages(chat_id, filter=None, limit=1):
            if msg.pinned:
                info["pinned_message"] = {
                    "id": msg.id,
                    "text": (msg.text or "")[:200],
                    "date": format_timestamp(msg.date),
                }
                break
    except Exception:
        pass

    return [TextContent(type="text", text=json.dumps(info, indent=2, ensure_ascii=False))]


# --- Reading Messages ---

async def handle_read_messages(args: dict) -> list[TextContent]:
    chat_id = resolve_chat_id(args["chat_id"])
    limit = args.get("limit", 20)
    offset_id = args.get("offset_id", 0)

    kwargs = {"limit": limit, "offset_id": offset_id}

    if args.get("min_date"):
        kwargs["offset_date"] = None  # Telethon uses offset_date differently
        # For min_date filtering, we'll post-filter
    if args.get("max_date"):
        max_dt = datetime.strptime(args["max_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        kwargs["offset_date"] = max_dt

    messages = []
    async for msg in telegram.client.iter_messages(chat_id, **kwargs):
        # Post-filter for min_date
        if args.get("min_date"):
            min_dt = datetime.strptime(args["min_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if msg.date.replace(tzinfo=timezone.utc) < min_dt:
                break

        messages.append(await format_message(msg))

        if len(messages) >= limit:
            break

    result = {
        "chat_id": args["chat_id"],
        "message_count": len(messages),
        "messages": messages,
    }

    if messages:
        result["oldest_message_id"] = messages[-1]["id"]
        result["pagination_hint"] = f"To load older messages, use offset_id={messages[-1]['id']}"

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def handle_search_messages(args: dict) -> list[TextContent]:
    query = args["query"]
    limit = args.get("limit", 20)
    chat_id = resolve_chat_id(args["chat_id"]) if args.get("chat_id") else None

    kwargs = {"search": query, "limit": limit}

    if args.get("from_user"):
        from_entity = await telegram.client.get_entity(resolve_chat_id(args["from_user"]))
        kwargs["from_user"] = from_entity

    messages = []
    entity = chat_id if chat_id else None
    async for msg in telegram.client.iter_messages(entity, **kwargs):
        formatted = await format_message(msg)
        # For global search, include the chat name
        if not chat_id and msg.chat:
            chat = await msg.get_chat()
            formatted["chat_name"] = getattr(chat, "title", None) or get_sender_name(chat)
            formatted["chat_id"] = msg.chat_id
        messages.append(formatted)

    result = {
        "query": query,
        "result_count": len(messages),
        "messages": messages,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def handle_read_thread(args: dict) -> list[TextContent]:
    chat_id = resolve_chat_id(args["chat_id"])
    message_id = args["message_id"]
    limit = args.get("limit", 20)

    # Get the parent message
    parent = await telegram.client.get_messages(chat_id, ids=message_id)
    if not parent:
        return [TextContent(type="text", text=f"Message {message_id} not found.")]

    parent_formatted = await format_message(parent)

    # Get replies
    replies = []
    async for msg in telegram.client.iter_messages(chat_id, reply_to=message_id, limit=limit):
        replies.append(await format_message(msg))

    # Replies come newest-first; reverse to show chronologically
    replies.reverse()

    result = {
        "parent_message": parent_formatted,
        "reply_count": len(replies),
        "replies": replies,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


# --- Writing Messages ---

async def handle_send_message(args: dict) -> list[TextContent]:
    chat_id = resolve_chat_id(args["chat_id"])
    text = args["text"]
    reply_to = args.get("reply_to")
    parse_mode = args.get("parse_mode")

    msg = await telegram.client.send_message(
        chat_id,
        text,
        reply_to=reply_to,
        parse_mode=parse_mode,
    )

    return [TextContent(type="text", text=json.dumps({
        "status": "sent",
        "message_id": msg.id,
        "chat_id": args["chat_id"],
        "date": format_timestamp(msg.date),
    }, indent=2))]


async def handle_edit_message(args: dict) -> list[TextContent]:
    chat_id = resolve_chat_id(args["chat_id"])
    message_id = args["message_id"]
    new_text = args["new_text"]
    parse_mode = args.get("parse_mode")

    msg = await telegram.client.edit_message(
        chat_id,
        message_id,
        new_text,
        parse_mode=parse_mode,
    )

    return [TextContent(type="text", text=json.dumps({
        "status": "edited",
        "message_id": msg.id,
        "chat_id": args["chat_id"],
        "new_text": new_text[:100],
        "date": format_timestamp(msg.date),
    }, indent=2))]


async def handle_delete_message(args: dict) -> list[TextContent]:
    chat_id = resolve_chat_id(args["chat_id"])
    message_id = args["message_id"]

    result = await telegram.client.delete_messages(chat_id, [message_id])

    # result is an AffectedMessages object
    deleted_count = getattr(result[0], "pts_count", 1) if result else 0

    return [TextContent(type="text", text=json.dumps({
        "status": "deleted",
        "message_id": message_id,
        "chat_id": args["chat_id"],
    }, indent=2))]


# --- Contacts & Users ---

async def handle_search_contacts(args: dict) -> list[TextContent]:
    query = args["query"]
    limit = args.get("limit", 10)

    result = await telegram.client(SearchRequest(q=query, limit=limit))

    contacts = []
    for user in result.users:
        contacts.append({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "phone": user.phone,
            "bot": user.bot,
            "status": get_user_status(user),
        })

    return [TextContent(type="text", text=json.dumps({
        "query": query,
        "result_count": len(contacts),
        "contacts": contacts,
    }, indent=2, ensure_ascii=False))]


async def handle_get_user_info(args: dict) -> list[TextContent]:
    user_id = resolve_chat_id(args["user_id"])
    entity = await telegram.client.get_entity(user_id)

    if not isinstance(entity, User):
        return [TextContent(type="text", text=f"Entity {args['user_id']} is not a user (it's a {type(entity).__name__}).")]

    info = {
        "id": entity.id,
        "first_name": entity.first_name,
        "last_name": entity.last_name,
        "username": entity.username,
        "phone": entity.phone,
        "bot": entity.bot,
        "status": get_user_status(entity),
    }

    # Try to get bio via full user info
    try:
        from telethon.tl.functions.users import GetFullUserRequest
        full = await telegram.client(GetFullUserRequest(entity))
        info["bio"] = full.full_user.about
    except Exception:
        pass

    return [TextContent(type="text", text=json.dumps(info, indent=2, ensure_ascii=False))]


# ==================== MAIN ====================

async def main():
    if not await telegram.connect():
        logger.error("Failed to connect to Telegram")
        return

    logger.info("Telegram MCP Server (v1 - Phase 1) starting...")
    logger.info("10 tools: list_chats, get_chat_info, read_messages, search_messages, read_thread, send_message, edit_message, delete_message, search_contacts, get_user_info")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await telegram.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
