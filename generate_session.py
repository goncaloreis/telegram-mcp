#!/usr/bin/env python3
"""
One-time script to generate a Telethon StringSession.

Run this interactively:
    python3 generate_session.py

It will prompt for your phone number and verification code.
The output is a session string to paste into your .env file.
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 32212130
API_HASH = "97ef16305b9be03e9cb8281f54ca0eb6"


async def main():
    print("=== Telegram Session Generator ===\n")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        phone = input("Enter your phone number (with country code, e.g. +351...): ")
        await client.send_code_request(phone)
        code = input("Enter the code Telegram sent you: ")

        try:
            await client.sign_in(phone, code)
        except Exception:
            # 2FA password required
            password = input("Enter your 2FA password: ")
            await client.sign_in(password=password)

    session_string = client.session.save()
    await client.disconnect()

    print(f"\n=== Your session string (add to .env) ===\n")
    print(f"TELEGRAM_SESSION_STRING={session_string}")
    print(f"\nDone! You can now run the MCP server.")


if __name__ == "__main__":
    asyncio.run(main())
