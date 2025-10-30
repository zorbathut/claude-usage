# Claude Code Usage Stats Scripts

This directory contains deobfuscated analysis of Claude Code and standalone scripts to fetch usage statistics.

## What I Found

From analyzing the Claude Code NPM package (`@anthropic-ai/claude-code` v2.0.29), I discovered:

### `/usage` Command Implementation

The `/usage` command fetches data from:
- **API Endpoint**: `https://api.anthropic.com/api/oauth/usage`
- **Authentication**: OAuth Bearer token (subscription) or API key
- **Required Header**: `anthropic-beta: oauth-2025-04-20`

### Usage Data Structure

The API returns three rate limit metrics:

```json
{
  "five_hour": {
    "utilization": 25.5,
    "resets_at": "2025-01-15T18:30:00Z"
  },
  "seven_day": {
    "utilization": 45.2,
    "resets_at": "2025-01-20T00:00:00Z"
  },
  "seven_day_opus": {
    "utilization": 60.8,
    "resets_at": "2025-01-20T00:00:00Z"
  }
}
```

- **five_hour**: Current 5-hour session limit
- **seven_day**: Weekly limit across all models
- **seven_day_opus**: Weekly Opus-specific limit

### Authentication Locations

Claude Code looks for credentials in this order:

1. **Environment variables**: `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`
2. **macOS Keychain** (macOS only): Service `@anthropic-ai/claude-code-credentials`
3. **Credentials file**: `~/.claude/.credentials.json`

The credentials file format:
```json
{
  "claudeAiOauth": {
    "accessToken": "...",
    "refreshToken": "...",
    "expiresAt": "...",
    "scopes": ["user:inference"],
    "subscriptionType": "..."
  },
  "apiKey": "sk-ant-..."
}
```

## Usage Scripts

```bash
# Show usage stats
python3 claude-usage.py

# Get raw JSON
python3 claude-usage.py --json

# Verbose output
python3 claude-usage.py --verbose
```

**Features:**
- Works with OAuth tokens (subscription) and API keys
- Automatically finds credentials from keychain or config files
- Pretty progress bars
- Human-readable reset times
- Pure Python 3 with only stdlib dependencies

## Example Output

```
Claude Code Usage Statistics

Current session (5 hours): [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 25% (resets in 3h 45m)
Current week (all models): [██████████████████████░░░░░░░░░░░░░░░░░░░] 45% (resets in 4d)
Current week (Opus): [██████████████████████████████░░░░░░░░░░░░░░] 60% (resets in 4d)
```

## Important Notes

1. **Subscription Required**: Usage stats are only available for Claude subscription plans (Pro/Max), not for API key users
2. **OAuth vs API Key**: The script works with both, but usage data is only returned for subscriptions
3. **Rate Limits**: The three metrics track different usage windows and model types

## Deobfuscation Process

1. **Downloaded package**: `npm pack @anthropic-ai/claude-code`
2. **Extracted**: `tar -xzf anthropic-ai-claude-code-2.0.29.tgz`
3. **Beautified**: `npx js-beautify cli.js` (3,790 lines → 409,145 lines)
4. **Analyzed**: Traced through code to find:
   - API endpoints and authentication
   - Credential storage locations
   - Data structures and display logic

## License

The original Claude Code is proprietary software by Anthropic.
These usage scripts are independent implementations for educational purposes.

## Disclaimer (actally written by a human)

Claude Code wrote this, I had no part in this. Yes, I used Claude Code to deobfuscate itself. Wild, right? I was surprised it was happy to go along with it but it didn't even hesitate.

As far as I'm concerned you can treat this like public domain if you want. I dunno if Anthropic would feel the same way. Y'all want me to take this down, lemme know and I will.
