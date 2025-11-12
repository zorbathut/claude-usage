#!/usr/bin/env python3
"""
Claude Code Usage Stats - Python Script
Fetches and displays usage statistics from Claude Code API
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import time

# Configuration
API_URL = 'https://api.anthropic.com/api/oauth/usage'
TOKEN_REFRESH_URL = 'https://console.anthropic.com/v1/oauth/token'
CLIENT_ID = '9d1c250a-e61b-44d9-88ed-5944d1962f5e'
ANTHROPIC_BETA = 'oauth-2025-04-20'
TOKEN_REFRESH_BUFFER_MS = 300000  # Refresh 5 minutes before expiration


def get_config_dir():
    """Get the Claude config directory"""
    return Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home() / '.claude'))


def get_oauth_data_from_file():
    """Get OAuth data from credentials file"""
    creds_path = get_config_dir() / '.credentials.json'

    if not creds_path.exists():
        return None

    try:
        with open(creds_path, 'r') as f:
            data = json.load(f)
            return data.get('claudeAiOauth')
    except (json.JSONDecodeError, IOError):
        return None


def get_oauth_token_from_file():
    """Get OAuth token from credentials file"""
    oauth_data = get_oauth_data_from_file()
    return oauth_data.get('accessToken') if oauth_data else None


def get_oauth_token_from_keychain():
    """Get OAuth token from macOS Keychain"""
    if sys.platform != 'darwin':
        return None

    try:
        service = '@anthropic-ai/claude-code-credentials'
        account = os.environ.get('USER', os.getlogin())

        cmd = ['security', 'find-generic-password', '-a', account, '-w', '-s', service]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if result.stdout:
            data = json.loads(result.stdout.strip())
            return data.get('claudeAiOauth', {}).get('accessToken')
    except (subprocess.CalledProcessError, json.JSONDecodeError, Exception):
        pass

    return None


def get_api_key():
    """Get API key from environment or credentials"""
    # Check environment variable first
    if 'ANTHROPIC_API_KEY' in os.environ:
        return os.environ['ANTHROPIC_API_KEY']

    # Check credentials file
    creds_path = get_config_dir() / '.credentials.json'

    if creds_path.exists():
        try:
            with open(creds_path, 'r') as f:
                data = json.load(f)
                return data.get('apiKey')
        except (json.JSONDecodeError, IOError):
            pass

    return None


def is_token_expired(expires_at):
    """Check if token is expired or about to expire (within 5 minutes)"""
    if expires_at is None:
        return False

    current_time_ms = int(time.time() * 1000)
    return current_time_ms + TOKEN_REFRESH_BUFFER_MS >= expires_at


def refresh_oauth_token(refresh_token):
    """Refresh OAuth token using refresh token"""
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID
    }

    data = json.dumps(payload).encode('utf-8')
    req = Request(
        TOKEN_REFRESH_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'claude-usage-script/1.0'
        }
    )

    try:
        with urlopen(req, timeout=10) as response:
            result = json.loads(response.read())

            # Calculate expiration time
            expires_at = int(time.time() * 1000) + (result['expires_in'] * 1000)

            return {
                'accessToken': result['access_token'],
                'refreshToken': result.get('refresh_token', refresh_token),
                'expiresAt': expires_at,
                'scope': result.get('scope', '')
            }
    except HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f'Token refresh failed (status {e.code}): {error_body}')
    except URLError as e:
        raise RuntimeError(f'Token refresh request failed: {e.reason}')
    except Exception as e:
        raise RuntimeError(f'Token refresh error: {e}')


def save_oauth_data(oauth_data):
    """Save OAuth data to credentials file"""
    creds_path = get_config_dir() / '.credentials.json'

    try:
        # Read existing data
        existing_data = {}
        if creds_path.exists():
            with open(creds_path, 'r') as f:
                existing_data = json.load(f)

        # Update OAuth data
        existing_data['claudeAiOauth'] = oauth_data

        # Write back
        with open(creds_path, 'w') as f:
            json.dump(existing_data, f, indent=2)

        return True
    except Exception as e:
        print(f'Warning: Failed to save refreshed token: {e}', file=sys.stderr)
        return False


def ensure_valid_oauth_token():
    """Ensure OAuth token is valid, refresh if necessary"""
    oauth_data = get_oauth_data_from_file()

    if not oauth_data:
        return None

    # Check if token needs refresh
    if not oauth_data.get('refreshToken') or not oauth_data.get('expiresAt'):
        # Token doesn't have refresh capability, just return access token
        return oauth_data.get('accessToken')

    if is_token_expired(oauth_data['expiresAt']):
        try:
            # Refresh the token
            new_oauth_data = refresh_oauth_token(oauth_data['refreshToken'])

            # Preserve additional fields
            new_oauth_data['scopes'] = oauth_data.get('scopes', [])
            new_oauth_data['subscriptionType'] = oauth_data.get('subscriptionType')

            # Save the new token
            save_oauth_data(new_oauth_data)

            return new_oauth_data['accessToken']
        except RuntimeError as e:
            print(f'Warning: Token refresh failed: {e}', file=sys.stderr)
            print('Please run "claude login" to re-authenticate', file=sys.stderr)
            return None

    return oauth_data['accessToken']


def get_auth_headers():
    """Get authentication headers"""
    # Try OAuth first (with automatic refresh)
    oauth_token = (
        os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') or
        get_oauth_token_from_keychain() or
        ensure_valid_oauth_token()
    )

    if oauth_token:
        return {
            'Authorization': f'Bearer {oauth_token}',
            'anthropic-beta': ANTHROPIC_BETA,
            'Content-Type': 'application/json',
            'User-Agent': 'claude-usage-script/1.0'
        }

    # Fall back to API key
    api_key = get_api_key()

    if api_key:
        return {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'claude-usage-script/1.0'
        }

    return None


def format_reset_time(reset_date_str):
    """Format date in human-readable form"""
    if not reset_date_str:
        return 'N/A'

    try:
        reset_date = datetime.fromisoformat(reset_date_str.replace('Z', '+00:00'))
        now = datetime.now(reset_date.tzinfo)
        diff = reset_date - now

        if diff.total_seconds() < 0:
            return 'expired'

        hours = int(diff.total_seconds() // 3600)
        minutes = int((diff.total_seconds() % 3600) // 60)

        if hours > 24:
            days = hours // 24
            return f"in {days} day{'s' if days != 1 else ''}"

        if hours > 0:
            return f"in {hours}h {minutes}m"

        return f"in {minutes}m"
    except (ValueError, AttributeError):
        return reset_date_str


def create_progress_bar(percentage, width=50):
    """Create a progress bar"""
    percentage = max(0, min(100, percentage))
    filled = int((percentage / 100) * width)
    empty = width - filled

    return '█' * filled + '░' * empty


def format_limit(title, limit_data, verbose=False):
    """Format usage limit display"""
    if not limit_data or limit_data.get('utilization') is None:
        return None

    percentage = int(limit_data['utilization'])
    bar = create_progress_bar(percentage)
    reset_time = format_reset_time(limit_data.get('resets_at'))

    if verbose:
        return f"{title}:\n  {bar} {percentage}% used\n  Resets {reset_time}\n"
    else:
        return f"{title}: [{bar}] {percentage}% (resets {reset_time})"


def fetch_usage():
    """Fetch usage data from API"""
    headers = get_auth_headers()

    if not headers:
        raise RuntimeError(
            'No authentication credentials found. '
            'Please log in to Claude Code first or set ANTHROPIC_API_KEY.'
        )

    req = Request(API_URL, headers=headers)

    try:
        with urlopen(req, timeout=5) as response:
            data = response.read()
            return json.loads(data)
    except HTTPError as e:
        raise RuntimeError(f'API returned status {e.code}: {e.read().decode()}')
    except URLError as e:
        raise RuntimeError(f'Request failed: {e.reason}')
    except Exception as e:
        raise RuntimeError(f'Unexpected error: {e}')


def display_usage(json_output=False, verbose=False):
    """Display usage stats"""
    try:
        usage = fetch_usage()

        if json_output:
            print(json.dumps(usage, indent=2))
            return

        print('Claude Code Usage Statistics\n')

        limits = [
            ('Current session (5 hours)', usage.get('five_hour')),
            ('Current week (all models)', usage.get('seven_day')),
            ('Current week (Opus)', usage.get('seven_day_opus'))
        ]

        has_data = False
        for title, limit_data in limits:
            formatted = format_limit(title, limit_data, verbose)
            if formatted:
                print(formatted)
                has_data = True

        if not has_data:
            print('No usage data available. This may be because:')
            print('  - You are using an API key instead of a subscription')
            print('  - /usage is only available for subscription plans')

    except RuntimeError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Claude Code Usage Stats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Authentication:
  This script looks for credentials in the following order:
  1. CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY environment variable
  2. macOS Keychain (macOS only)
  3. ~/.claude/.credentials.json file

Note: Usage stats are only available for Claude subscription plans,
      not for API key users.
        '''
    )

    parser.add_argument('--json', action='store_true',
                        help='Output raw JSON response')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output with more formatting')

    args = parser.parse_args()

    display_usage(json_output=args.json, verbose=args.verbose)


if __name__ == '__main__':
    main()
