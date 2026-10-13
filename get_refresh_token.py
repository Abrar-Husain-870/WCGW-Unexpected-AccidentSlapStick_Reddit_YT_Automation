#!/usr/bin/env python3
"""
Helper script: Generate a YouTube OAuth refresh token for a new channel.

Usage:
    python get_refresh_token.py

Then paste the printed REFRESH_TOKEN into your .env file.
Uses the same YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE from your .env.
"""
from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import config


def main() -> None:
    if not config.YT_CLIENT_ID or "your_client_id" in config.YT_CLIENT_ID:
        print("❌ Set YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE in .env first!")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    client_config = {
        "installed": {
            "client_id": config.YT_CLIENT_ID,
            "client_secret": config.YT_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("=" * 60)
    print("🔑 YOUTUBE REFRESH TOKEN GENERATOR")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: When the browser opens, sign in with your")
    print("   NEW channel's email address (not your old one)!")
    print()
    print("   Then click 'Continue' to grant access.")
    print()

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    new_token = creds.refresh_token

    print()
    print("=" * 60)
    print("✅ SUCCESS! Here is your new refresh token:")
    print()
    print(f"   {new_token}")
    print()
    print("=" * 60)
    print()

    # Automatically update local .env file
    env_path = config.ROOT / ".env"
    if env_path.exists():
        try:
            content = env_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            new_lines = []
            updated_ref = False
            updated_meme_ref = False
            for line in lines:
                if line.startswith("YT_REFRESH_TOKEN="):
                    new_lines.append(f'YT_REFRESH_TOKEN="{new_token}"')
                    updated_ref = True
                elif line.startswith("YT_MEME_REFRESH_TOKEN="):
                    new_lines.append(f'YT_MEME_REFRESH_TOKEN="{new_token}"')
                    updated_meme_ref = True
                else:
                    new_lines.append(line)
            if not updated_ref:
                new_lines.append(f'YT_REFRESH_TOKEN="{new_token}"')
            if not updated_meme_ref:
                new_lines.append(f'YT_MEME_REFRESH_TOKEN="{new_token}"')
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print("✔ Automatically updated local .env file with new refresh token!")
        except Exception as e:
            print(f"⚠️ Could not auto-update .env file: {e}")

    # Invalidate old cached token so new account is immediately active
    token_file = config.CACHE_DIR / "yt_token.json"
    if token_file.exists():
        try:
            token_file.unlink()
            print("✔ Cleared previous cached YouTube session token.")
        except Exception as e:
            print(f"⚠️ Could not delete old cached token: {e}")

    print()
    print("📌 IMPORTANT: If using GitHub Actions, update GitHub Secrets:")
    print(f'   YT_REFRESH_TOKEN = {new_token}')
    print(f'   YT_MEME_REFRESH_TOKEN = {new_token}')
    print()


if __name__ == "__main__":
    main()