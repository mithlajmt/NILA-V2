"""
NILA-V2 Interactive Setup Script for Personal Telegram User Login
Guides you through signing in once with Telethon MTProto API.
Saves session file 'data/telegram_user.session' and updates .env file.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon import TelegramClient

def update_env_file(key: str, value: str, env_path: str = ".env"):
    """Update or append key=value in .env file"""
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"{key}={value}\n")
        return

    lines = []
    found = False
    with open(env_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


async def main():
    print("=" * 60)
    print("📱 NILA-V2 PERSONAL TELEGRAM USER ACCOUNT SETUP")
    print("=" * 60)
    print("This script will link your personal Telegram account to Nila.")
    print("You only need to do this ONCE. Session file will be saved in 'data/telegram_user.session'.\n")

    api_id_env = os.getenv("TELEGRAM_API_ID", "")
    api_hash_env = os.getenv("TELEGRAM_API_HASH", "")
    phone_env = os.getenv("TELEGRAM_PHONE_NUMBER", "")

    if not api_id_env or api_id_env == "0" or not api_hash_env:
        print("📌 Step 1: Telegram API Credentials (my.telegram.org)")
        print("If you don't have these, visit https://my.telegram.org -> API Development Tools to get them in 1 minute.\n")

        api_id_str = input("Enter your TELEGRAM_API_ID (e.g. 12345678): ").strip()
        api_hash = input("Enter your TELEGRAM_API_HASH (e.g. a1b2c3d4e5f6...): ").strip()
        phone = input("Enter your Phone Number with country code (e.g. +919876543210): ").strip()

        try:
            api_id = int(api_id_str)
        except ValueError:
            print("❌ Invalid API ID. Must be a number.")
            sys.exit(1)

        # Save to .env
        update_env_file("TELEGRAM_API_ID", str(api_id))
        update_env_file("TELEGRAM_API_HASH", api_hash)
        update_env_file("TELEGRAM_PHONE_NUMBER", phone)
        print("✅ Saved Telegram credentials to .env\n")
    else:
        api_id = int(api_id_env)
        api_hash = api_hash_env
        phone = phone_env
        print(f"✅ Found existing credentials in .env (API ID: {api_id})")

    os.makedirs("data", exist_ok=True)
    session_path = "data/telegram_user"

    print("📡 Connecting to Telegram MTProto Servers...")
    client = TelegramClient(session_path, api_id, api_hash)

    await client.connect()

    if not await client.is_user_authorized():
        print(f"\n📲 Sending login code via Telegram / SMS to {phone}...")
        await client.send_code_request(phone)
        code = input("🔑 Enter the Telegram login code you received: ").strip()

        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "password" in str(e).lower() or "2fa" in str(e).lower():
                two_fa_pass = input("🔐 Enter your Telegram 2FA Cloud Password: ").strip()
                await client.sign_in(password=two_fa_pass)
            else:
                print(f"❌ Login failed: {e}")
                sys.exit(1)

    me = await client.get_me()
    print("\n" + "=" * 60)
    print(f"🎉 SUCCESS! Logged in as: {me.first_name} (@{me.username or 'No username'})")
    print(f"Phone: +{me.phone}")
    print("=" * 60)
    print("✅ Permanent session saved to 'data/telegram_user.session'.")
    print("Nila is now fully authorized to send and read messages from your account!\n")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
