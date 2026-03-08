# Mail Sync Server

Dockerized mail sync service to continuously perform mail operations (like syncing two mailboxes) at specific time intervals or with a REST API for manual triggers via a command line script on-demand.

This container extends the (gilleslamiral/imapsync)[https://hub.docker.com/r/gilleslamiral/imapsync/] docker image to provide scheduling at regular intervals.

This project was created because (Gmail is discontinuing Gmailify)[https://support.google.com/mail/answer/16604719] which means you can no longer rely on Gmail to download mail to your inbox automatically. You will likely just want to sync your inbox and spam folders (turn your spam filters back on at the origin mail provider if you disabled them) to get a similar experience to what you had before.

## Features

- 🔄 Automatic mail sync every 15 minutes (configurable)
- 🚀 Manual sync trigger via REST API
- 🔐 API key authentication
- 🛡️ Startup validation prevents using default passwords
- 👥 Multi-account support (sync multiple mailboxes)
- 📊 Health check endpoint
- 📝 Convenience scripts for Bash and PowerShell
- 🔧 Based on [imapsync](https://imapsync.lamiral.info/) - battle-tested email migration tool

## Quick Start

### 1. Configure API Key

```bash
cp .env.example .env
nano .env
```

Set a strong API key:
```env
API_KEY=your-super-secret-api-key-here
SYNC_INTERVAL_MINUTES=15
```

### 2. Configure Sync Jobs

Edit `config.json` and add your sync configurations. Arguments are passed directly to imapsync:

```json
{
  "syncs": [
    {
      "syncName": "Sync Work Email to Gmail",
      "enabled": true,
      "schedule": "*/15 * * * *",
      "arguments": [
        "--host1", "mail.someprovider.com",
        "--port1", "993",
        "--ssl1",
        "--user1", "john@example.com",
        "--password1", "YOUR_SOURCE_PASSWORD",
        "--host2", "imap.gmail.com",
        "--port2", "993",
        "--ssl2",
        "--user2", "example@gmail.com",
        "--password2", "YOUR_GMAIL_APP_PASSWORD",
        "--folder", "Inbox",
        "--folder", "Spam",
        "--delete1",
        "--syncinternaldates",
        "--addheader",
        "--nofoldersizes",
        "--nofoldersizesatend",
        "--no-modulesversion",
        "--nocheckfoldersexist",
        "--nocheckselectable",
        "--nochecknoabletosearch"
      ]
    }
  ]
}
```

**Configuration fields:**
- `syncName`: Unique identifier for this sync (used in API calls)
- `enabled`: Set to `false` to temporarily disable this sync
- `schedule`: Cron expression for when to run (optional, uses global interval if omitted)
- `arguments`: Array of arguments passed directly to imapsync command

**Cron schedule examples:**
```
*/15 * * * *     # Every 15 minutes (default)
*/5 * * * *      # Every 5 minutes
0 * * * *        # Every hour at :00
0 9,17 * * *     # 9 AM and 5 PM daily
0 0 * * *        # Once daily at midnight
0 */6 * * *      # Every 6 hours
```

**Copy arguments from imapsync docs:**
You can copy examples directly from [imapsync documentation](https://imapsync.lamiral.info/#doc) - just convert the command-line format to a JSON array:

```bash
# From imapsync docs:
imapsync --host1 test.com --user1 me --password1 pass1 --host2 imap.gmail.com

# To config.json:
"arguments": [
  "--host1", "test.com",
  "--user1", "me",
  "--password1", "pass1",
  "--host2", "imap.gmail.com"
]
```

## Important for Gmail

1. **Enable IMAP** in Gmail settings:
   - Go to Gmail settings (gear icon) → "See all settings"
   - Navigate to "Forwarding and POP/IMAP" tab
   - Enable IMAP
   - Save changes

2. **Set up App Password**:
   - Enable 2-Step Verification on your Google account first
   - Generate App Password at: https://myaccount.google.com/apppasswords
   - Select "Other (Custom name)" and name it "imapsync"
   - **CRITICAL**: Remove all spaces from the generated App Password before using it
     - Google includes spaces in the displayed password, but they will cause authentication failures
     - Example: `abcd efgh ijkl mnop` should be entered as `abcdefghijklmnop`

3. **Workspace/Group Accounts**: May require XOAUTH2 instead of App Passwords

## ⚠️ Security Notice:
The service will **NOT start** if default passwords are detected. You must replace all placeholder passwords (`YOUR_SOURCE_PASSWORD_HERE`, `YOUR_GMAIL_APP_PASSWORD_HERE`) and the default API key (`change-me-please`) with actual credentials before the container will run.

**Common imapsync flags:**
- `--host1`, `--user1`, `--password1`: Source IMAP server
- `--host2`, `--user2`, `--password2`: Destination IMAP server
- `--port1`, `--port2`: IMAP ports (usually 993 for SSL)
- `--ssl1`, `--ssl2`: Enable SSL/TLS
- `--folder`: Sync specific folder (can specify multiple times)
- `--delete1`: Delete from source after sync (creates a move operation)
- `--dry`: Test mode - don't make actual changes
- `--justlogin`: Test authentication only

See [imapsync documentation](https://imapsync.lamiral.info/#doc) for all available options.

### 3. Deploy

#### Option A: Portainer (Recommended)

1. Upload this folder to your Ubuntu server
2. In Portainer: **Stacks** → **Add Stack**
3. Choose **Upload** and select `docker-compose.yml`
4. Add environment variables (or use .env file)
5. Click **Deploy**

#### Option B: Docker Compose CLI

```bash
# Make scripts executable
chmod +x mailsync.sh

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Set Environment Variables for Scripts

#### Bash (Linux/Mac)
Add to your `~/.bashrc` or `~/.bash_profile`:
```bash
export MAILSYNC_API_URL="http://your-server:5000"
export MAILSYNC_API_KEY="your-super-secret-api-key-here"
```

#### PowerShell (Windows)
Add to your PowerShell profile (`$PROFILE`):
```powershell
$env:MAILSYNC_API_URL = "http://your-server:5000"
$env:MAILSYNC_API_KEY = "your-super-secret-api-key-here"
```

Or set permanently:
```powershell
[Environment]::SetEnvironmentVariable("MAILSYNC_API_URL", "http://your-server:5000", "User")
[Environment]::SetEnvironmentVariable("MAILSYNC_API_KEY", "your-super-secret-api-key-here", "User")
```

## Manual Sync Triggers

### Bash Script (Linux/Mac/WSL)

```bash
# Trigger sync named "MyMailSync"
./mailsync.sh MyMailSync
```

### PowerShell Script (Windows)

```powershell
# Trigger sync named "MyMailSync"
.\mailsync.ps1 -SyncName "MyMailSync"
```

### Direct API Call (curl)

```bash
curl -X POST http://localhost:5000/sync \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-super-secret-api-key-here" \
  -d '{"syncName": "MyMailSync"}'
```

### Direct API Call (PowerShell)

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = "your-super-secret-api-key-here"
}
$body = @{ syncName = "MyMailSync" } | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/sync" -Method Post -Headers $headers -Body $body
```

## API Endpoints

### `GET /health`
Health check endpoint (no authentication required)

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-26T10:30:00.123456"
}
```

### `GET /syncs`
List all configured sync configurations (requires API key)

```bash
curl -H "X-API-Key: your-api-key" http://localhost:5000/syncs
```

Response:
```json
{
  "syncs": [
    {
      "syncName": "MyMailSync",
      "enabled": true,
      "schedule": "*/15 * * * *",
      "user1": "john@example.com",
      "user2": "john@gmail.com"
    }
  ]
}
```

### `POST /sync`
Trigger manual sync for a specific sync configuration (requires API key)

```bash
curl -X POST http://localhost:5000/sync \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"syncName": "MyMailSync"}'
```

Success Response (200):
```json
{
  "status": "success",
  "syncName": "MyMailSync",
  "timestamp": "2026-02-26T10:35:00.123456",
  "message": "Sync completed successfully"
}
```

Error Response (404):
```json
{
  "error": "Sync configuration not found: unknown_sync"
}
```

## Customizing Sync Behavior

Modify the `arguments` array to customize sync behavior:

### Keep Original Messages (Don't Delete from Source)
Remove `"--delete1"` from the arguments:
```json
"arguments": [
  "--host1", "mail.example.com",
  "--user1", "me@example.com",
  "--password1", "pass1",
  "--host2", "imap.gmail.com",
  "--user2", "me@gmail.com",
  "--password2", "pass2",
  "--folder", "Inbox"
]
```

### Sync All Folders
Remove all `"--folder"` arguments to sync everything:
```json
"arguments": [
  "--host1", "mail.example.com",
  "--user1", "me@example.com",
  "--password1", "pass1",
  "--host2", "imap.gmail.com"
]
```

### Exclude Certain Folders
Add `--exclude` arguments:
```json
"arguments": [
  "--host1", "mail.example.com",
  "--exclude", "Trash",
  "--exclude", "Junk",
  "--exclude", "Spam"
]
```

### Skip Large Messages
Skip messages larger than 50MB:
```json
"arguments": [
  "--host1", "mail.example.com",
  "--maxsize", "52428800"
]
```

### Dry Run (Test Without Changes)
Add `"--dry"` to test without making changes:
```json
"arguments": [
  "--dry",
  "--host1", "mail.example.com"
]
```

### Different Schedules for Different Syncs
```json
{
  "syncs": [
    {
      "syncName": "urgent-email",
      "schedule": "*/5 * * * *",
      "arguments": ["--host1", "mail.example.com", "--folder", "Urgent"]
    },
    {
      "syncName": "daily-backup",
      "schedule": "0 2 * * *",
      "arguments": ["--host1", "mail.example.com"]
    }
  ]
}
```

After making changes, restart the container:
```bash
docker-compose restart
```

## Adding Multiple Sync Configurations

Edit `config.json` and add more sync configurations to the array:

```json
{
  "syncs": [
    {
      "syncName": "personal-email",
      "enabled": true,
      "schedule": "*/15 * * * *",
      "arguments": [
        "--host1", "mail.personal.com",
        "--user1", "me@personal.com",
        "--password1", "password1",
        "--host2", "imap.gmail.com",
        "--user2", "me@gmail.com",
        "--password2", "apppassword"
      ]
    },
    {
      "syncName": "work-email",
      "enabled": true,
      "schedule": "*/5 * * * *",
      "arguments": [
        "--host1", "mail.company.com",
        "--user1", "me@company.com",
        "--password1", "password2",
        "--host2", "imap.gmail.com",
        "--user2", "work@gmail.com",
        "--password2", "apppassword2",
        "--folder", "Inbox",
        "--folder", "Important"
      ]
    },
    {
      "syncName": "archive-old-mail",
      "enabled": true,
      "schedule": "0 3 * * *",
      "arguments": [
        "--host1", "mail.oldprovider.com",
        "--user1", "old@email.com",
        "--password1", "password3",
        "--host2", "imap.gmail.com",
        "--user2", "archive@gmail.com",
        "--password2", "apppassword3"
      ]
    }
  ]
}
```

Restart the container:
```bash
docker-compose restart
```

## Monitoring

### View Logs
```bash
# Live logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Filter for sync events
docker-compose logs | grep "sync"
```

### Check Container Status
```bash
docker-compose ps
```

## Adjusting Sync Schedules

### Per-Sync Schedules (Recommended)
Set individual schedules for each sync in `config.json`:
```json
{
  "syncs": [
    {
      "syncName": "urgent",
      "schedule": "*/5 * * * *",
      "arguments": [...]
    },
    {
      "syncName": "normal",
      "schedule": "*/15 * * * *",
      "arguments": [...]
    },
    {
      "syncName": "daily",
      "schedule": "0 2 * * *",
      "arguments": [...]
    }
  ]
}
```

### Global Default Interval
Edit `.env` to set the default interval for syncs without a `schedule` field:
```env
SYNC_INTERVAL_MINUTES=15  # Default: 15 minutes
```

Then restart:
```bash
docker-compose restart
```

**Recommended schedules:**
- `*/5 * * * *` (Every 5 min): Time-critical emails, low volume
- `*/15 * * * *` (Every 15 min): Good balance for most use cases (default)
- `0 * * * *` (Every hour): High-volume mailboxes or resource-constrained systems
- `0 */6 * * *` (Every 6 hours): Periodic backups
- `0 2 * * *` (Daily at 2 AM): Archive/backup operations

**Cron format:** `minute hour day month day_of_week`
- Use `*` for "any"
- Use `*/N` for "every N"
- Use `0,15,30,45` for specific values

**Note**: Gmail doesn't publish official rate limits for IMAP, but syncing too frequently with large mailboxes may trigger temporary throttling. If you experience connection issues, increase the interval.

## Security Best Practices

1. **Strong API Key**: Use a long random string (32+ characters)
   ```bash
   # Generate a secure API key
   openssl rand -base64 32
   ```

2. **Network Security**:
   - Don't expose port 5000 to the internet
   - Use a reverse proxy with HTTPS if remote access is needed
   - Consider using a VPN or SSH tunnel

3. **Credentials**:
   - Never commit `config.json` or `.env` to git
   - Use Gmail App Passwords, not your main password
   - **Remove all spaces** from Gmail App Passwords (Google displays them with spaces but they don't work that way)
   - Regularly rotate passwords
   - The startup validation prevents using default passwords

4. **File Permissions**:
   ```bash
   chmod 600 config.json .env
   ```

## Troubleshooting

### Container Won't Start
```bash
docker-compose logs mailsync
```

Check for Python errors or missing dependencies.

### Container Exits with "Configuration validation failed"

The service validates credentials on startup and will refuse to start if default passwords are detected.

**Error message:**
```
Configuration validation failed. Default passwords detected.
```

**Solution:**
1. Edit `config.json` and replace all `YOUR_SOURCE_PASSWORD_HERE` and `YOUR_GMAIL_APP_PASSWORD_HERE` placeholders with actual credentials
2. Edit `.env` and change `API_KEY` from `change-me-please` to a strong unique key
3. Make sure no passwords are empty
4. Restart the container: `docker-compose restart`

Generate a secure API key:
```bash
openssl rand -base64 32
```

### API Returns 401 Unauthorized
- Verify API key matches in `.env` and your script
- Check `X-API-Key` header is being sent

### Sync Fails
- Check credentials in `config.json`
- Verify Gmail App Password is correct and **has no spaces**
  - Gmail displays App Passwords with spaces like `abcd efgh ijkl mnop`
  - You must remove the spaces: `abcdefghijklmnop`
- Ensure 2-Step Verification is enabled on your Gmail account
- Verify IMAP is enabled in Gmail settings
- Test connection manually:
  ```bash
  docker-compose exec mailsync imapsync \
    --host1 mail.example.com --user1 user@example.com \
    --password1 "password" --justlogin --ssl1
  ```

  Or test with `--dry` flag to see what would happen without making changes:
  ```bash
  docker-compose exec mailsync imapsync \
    --host1 mail.example.com --user1 user@example.com \
    --password1 "password" --host2 imap.gmail.com \
    --user2 user@gmail.com --password2 "apppassword" --dry
  ```

### Gmail Authentication Errors
**Error:** "Too many login failures" or "Invalid credentials"

**Common causes:**
1. Spaces in the App Password (remove them!)
2. 2-Step Verification not enabled
3. IMAP not enabled in Gmail settings
4. Using regular password instead of App Password
5. App Password was revoked or expired

**Solution:**
- Delete the old App Password in Google Account settings
- Generate a new App Password
- Remove all spaces from it
- Update `config.json` with the space-free password
- Restart: `docker-compose restart`

### Scheduled Sync Not Running
- Check logs for errors: `docker-compose logs -f`
- Verify `SYNC_INTERVAL_MINUTES` is set correctly
- Container might have crashed - check `docker-compose ps`

## Windows Task Scheduler Migration

If migrating from Windows Task Scheduler, you can disable the old task:

```powershell
# Disable Windows scheduled task
Disable-ScheduledTask -TaskName "Sync External Mailbox to Gmail"
```

## Accessing from Remote Machines

If your Ubuntu server is at `192.168.1.100`, use the convenience scripts from any machine:

```bash
# Bash
export MAILSYNC_API_URL="http://192.168.1.100:5000"
export MAILSYNC_API_KEY="your-api-key"
./mailsync.sh MyMailSync
```

```powershell
# PowerShell
$env:MAILSYNC_API_URL = "http://192.168.1.100:5000"
$env:MAILSYNC_API_KEY = "your-api-key"
.\mailsync.ps1 -SyncName "MyMailSync"
```

## About imapsync

This project uses the [imapsync](https://github.com/imapsync/imapsync) tool by Gilles LAMIRAL.

### Docker Image
- Base image: [`gilleslamiral/imapsync`](https://hub.docker.com/r/gilleslamiral/imapsync/)
- Updates: The Docker image is regularly updated. To update:
  ```bash
  docker-compose pull
  docker-compose up -d
  ```

### Additional Resources
- [imapsync Gmail FAQ](https://imapsync.lamiral.info/FAQ.d/FAQ.Gmail_imapsync_online.html)
- [imapsync Docker FAQ](https://imapsync.lamiral.info/FAQ.d/FAQ.Docker.txt)
- [Official imapsync site](https://imapsync.lamiral.info/)

## Backward Compatibility

The new `arguments` array format is the recommended approach, but the legacy structured format is still supported:

**New format (recommended):**
```json
{
  "syncs": [
    {
      "syncName": "test",
      "schedule": "*/15 * * * *",
      "arguments": [
        "--host1", "mail.example.com",
        "--user1", "me@example.com",
        "--password1", "pass1",
        "--host2", "imap.gmail.com"
      ]
    }
  ]
}
```

**Legacy format (still works):**
```json
{
  "accounts": [
    {
      "syncName": "test",
      "host1": "mail.example.com",
      "port1": 993,
      "ssl1": true,
      "user1": "me@example.com",
      "password1": "pass1",
      "host2": "imap.gmail.com",
      "folders": ["Inbox"],
      "options": ["--delete1"]
    }
  ]
}
```

**Why use the new format?**
- Direct mapping to imapsync CLI - copy examples from docs
- Per-sync cron schedules for flexible timing
- Any new imapsync feature works immediately
- Simpler code, easier to maintain
- Less configuration boilerplate
