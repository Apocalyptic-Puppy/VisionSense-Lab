# puppy

1. on 1366 x 768 resolution, 125% scale
2. go to top left corner of the map before 'Load Entities', if unable to load put a white background layered below the minimap
3. use vs code window to block anything below minimap
4. click 'Load Entities', press control

---

## Discord webhook configuration (secure)

This project no longer hardcodes Discord webhooks in code. To keep your webhook secret and allow other machines to run the project safely, place the webhook URL in one of these locations (in order of precedence):

1. Environment variable: DISCORD_WEBHOOK_URL
2. config.json in the project root (ignored by git)
3. .env file in the project root (ignored by git)

Examples

- Linux / macOS (Bash):

  export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/...."
  python3 gameMonitor.py

- Windows (PowerShell):

  $env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
  python gameMonitor.py

config.json example (do NOT commit):

{
  "discord_webhook_url": "https://discord.com/api/webhooks/..."
}

.env example (do NOT commit):

DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

Security notes

- Ensure config.json and .env are not committed. These filenames are already added to .gitignore.
- If a webhook was previously leaked, rotate it in Discord and replace it in your local config.

How to use on another computer

1. Clone the repo:

   git clone https://github.com/Brad-99/maple.git
   cd maple

2. Get the changes branch (if the maintainer pushed it) or apply the patch included in the repo:

   # If branch exists remotely:
   git fetch origin
   git checkout local-config-webhook || git checkout -b local-config-webhook origin/local-config-webhook

   # If branch is only local to your other machine, apply the patch file (if provided):
   git apply patches/gameMonitor-webhook-fix.patch

3. Configure your webhook using one of the methods above.

4. Run the program and verify notifications:

   python3 gameMonitor.py

Getting Copilot (CLI) help on the other machine

If you installed the GitHub Copilot CLI on the other machine, you can ask it to help set up env/config files and push your changes. Examples of prompts to give Copilot CLI:

- "Set DISCORD_WEBHOOK_URL environment variable for Bash and PowerShell"
- "Create a config.json with my webhook and ensure it's ignored by git" 
- "Push current branch to remote as local-config-webhook"

When asking Copilot CLI to run commands that change git history or push to remotes, be explicit (e.g., "force push to origin master"), since those operations are destructive.

---

