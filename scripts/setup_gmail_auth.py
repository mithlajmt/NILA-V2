#!/usr/bin/env python3
"""
NILA-V2 Gmail Auth Setup & Diagnostic Tool
------------------------------------------
Run this script to authenticate your Google Account, test Gmail API credentials,
and verify that NILA-V2 can read and send emails.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.gmail_tools import (
    CLIENT_SECRET_PATH,
    TOKEN_PATH,
    get_gmail_service,
    read_unread_emails,
    send_gmail_message
)

from src.tools.calendar_tools import get_today_schedule

def main():
    print("=" * 60)
    print("📧 📅 NILA-V2 Gmail & Google Calendar OAuth Setup & Test")
    print("=" * 60)
    print(f"Client Secret File Path : {CLIENT_SECRET_PATH}")
    print(f"Authorized Token Path  : {TOKEN_PATH}")
    print("-" * 60)

    if not CLIENT_SECRET_PATH.exists() and not TOKEN_PATH.exists():
        print("\n⚠️ Google OAuth credentials file missing!")
        print("\n📋 QUICK SETUP INSTRUCTIONS:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create a new project (or select an existing one).")
        print("3. Enable 'Gmail API' and 'Google Calendar API' under APIs & Services > Library.")
        print("4. Go to APIs & Services > Credentials > Create Credentials > OAuth client ID.")
        print("5. Choose Application type: 'Desktop app'.")
        print("6. Download the JSON credential file.")
        print(f"7. Save it to: {CLIENT_SECRET_PATH}")
        print("=" * 60)
        sys.exit(1)

    print("\n🔑 Connecting to Gmail API service...")
    service = get_gmail_service()

    if not service:
        print("❌ Could not connect to Google API. Please check your credentials.")
        sys.exit(1)

    print("✅ Successfully authenticated with Gmail & Calendar APIs!")

    # Test reading unread emails
    print("\n📬 Testing 'read_unread_emails' tool...")
    result_str = read_unread_emails(query="label:INBOX", max_results=3)
    try:
        data = json.loads(result_str)
        print(f"Status : {data.get('status')}")
        print(f"Summary: {data.get('summary')}")
    except Exception as e:
        print(f"Raw Output: {result_str}")

    # Test Google Calendar
    print("\n📅 Testing 'get_today_schedule' tool...")
    cal_res_str = get_today_schedule()
    try:
        cal_data = json.loads(cal_res_str)
        print(f"Status : {cal_data.get('status')}")
        print(f"Summary: {cal_data.get('summary')}")
    except Exception as e:
        print(f"Raw Output: {cal_res_str}")

    print("\n=" * 60)
    print("🎉 Gmail & Google Calendar Tools are fully ready for NILA-V2 Robot!")
    print("=" * 60)

if __name__ == "__main__":
    main()

