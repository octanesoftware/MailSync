#!/usr/bin/env python3
"""
Mail Sync API Server
Provides REST API endpoint for manual mail sync triggers and runs scheduled syncs
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load configuration
CONFIG_FILE = os.getenv('CONFIG_FILE', '/app/config.json')
API_KEY = os.getenv('API_KEY', 'change-me-please')
SYNC_INTERVAL_MINUTES = int(os.getenv('SYNC_INTERVAL_MINUTES', '15'))

def load_config():
    """Load sync configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Support both 'syncs' (new) and 'accounts' (legacy) keys
            if 'syncs' not in config and 'accounts' in config:
                config['syncs'] = config['accounts']
            return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {"syncs": []}

def extract_passwords_from_arguments(arguments):
    """Extract password values from arguments array"""
    passwords = []
    i = 0
    while i < len(arguments):
        arg = arguments[i]
        if arg in ['--password1', '--password2'] and i + 1 < len(arguments):
            passwords.append(arguments[i + 1])
        i += 1
    return passwords

def validate_configuration():
    """Validate that default passwords have been changed"""
    errors = []

    # Check API key
    default_api_keys = ['change-me-please', 'your-secure-api-key-here', 'your-super-secret-api-key-here']
    if API_KEY.lower() in [k.lower() for k in default_api_keys]:
        errors.append("API_KEY is still set to default value. Please change it in .env file.")

    # Check sync passwords
    config = load_config()
    default_passwords = [
        'YOUR_SOURCE_PASSWORD_HERE',
        'YOUR_GMAIL_APP_PASSWORD_HERE',
        'YOUR_GMAIL_APP_PASSWORD_HERE_NO_SPACES',
        'YOUR_SOURCE_PASSWORD',
        'YOUR_GMAIL_APP_PASSWORD',
        'PASSWORD_HERE',
        'change-me-please',
        'password'
    ]

    for sync in config.get('syncs', []):
        sync_name = sync.get('syncName', 'unknown')

        # Check if using new arguments format
        if 'arguments' in sync:
            passwords = extract_passwords_from_arguments(sync['arguments'])

            for idx, password in enumerate(passwords, 1):
                if not password:
                    errors.append(f"Sync '{sync_name}': password{idx} is empty.")
                elif password.upper() in [p.upper() for p in default_passwords]:
                    errors.append(f"Sync '{sync_name}': password{idx} is still set to default value.")
        else:
            # Legacy format support
            password1 = sync.get('password1', '')
            password2 = sync.get('password2', '')

            # Check if passwords are in default list (case-insensitive)
            if password1.upper() in [p.upper() for p in default_passwords]:
                errors.append(f"Sync '{sync_name}': password1 is still set to default value.")

            if password2.upper() in [p.upper() for p in default_passwords]:
                errors.append(f"Sync '{sync_name}': password2 is still set to default value.")

            # Check for empty passwords
            if not password1:
                errors.append(f"Sync '{sync_name}': password1 is empty.")

            if not password2:
                errors.append(f"Sync '{sync_name}': password2 is empty.")

    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ValueError(
            "Configuration validation failed. Default passwords detected. "
            "Please update config.json and .env with your actual credentials."
        )

    logger.info("Configuration validation passed")

def require_api_key(f):
    """Decorator to require valid API key in request header"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401
        if api_key != API_KEY:
            return jsonify({"error": "Invalid API key"}), 403
        return f(*args, **kwargs)
    return decorated_function

def run_imapsync(sync_config):
    """Execute imapsync with given configuration"""
    sync_name = sync_config.get('syncName', 'unknown')
    logger.info(f"Starting sync for {sync_name}")

    # Build imapsync command
    cmd = ['imapsync']

    # Check if using new arguments format (pass-through)
    if 'arguments' in sync_config:
        # Pass arguments directly to imapsync
        cmd.extend(sync_config['arguments'])
    else:
        # Legacy structured format
        cmd.extend([
            '--host1', sync_config['host1'],
            '--port1', str(sync_config['port1']),
            '--user1', sync_config['user1'],
            '--password1', sync_config['password1'],
            '--host2', sync_config['host2'],
            '--port2', str(sync_config['port2']),
            '--user2', sync_config['user2'],
            '--password2', sync_config['password2'],
        ])

        # Add SSL flags if specified
        if sync_config.get('ssl1', True):
            cmd.append('--ssl1')
        if sync_config.get('ssl2', True):
            cmd.append('--ssl2')

        # Add folders
        for folder in sync_config.get('folders', ['Inbox']):
            cmd.extend(['--folder', folder])

        # Add additional options
        for option in sync_config.get('options', []):
            cmd.append(option)

    try:
        # Run imapsync
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        success = result.returncode == 0
        if success:
            logger.info(f"Sync completed successfully for {sync_name}")
        else:
            logger.error(f"Sync failed for {sync_name}: {result.stderr}")

        return {
            "success": success,
            "exit_code": result.returncode,
            "stdout": result.stdout[-3000:],  # Last 3000 chars
            "stderr": result.stderr[-3000:] if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Sync timeout for {sync_name}")
        return {
            "success": False,
            "error": "Sync operation timed out"
        }
    except Exception as e:
        logger.error(f"Sync error for {sync_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def create_sync_job(sync_config):
    """Create a scheduler job for a sync configuration"""
    sync_name = sync_config.get('syncName', 'unknown')

    def job():
        logger.info(f"Running scheduled sync for: {sync_name}")
        result = run_imapsync(sync_config)
        if result.get('success'):
            logger.info(f"Scheduled sync completed successfully for: {sync_name}")
        else:
            logger.error(f"Scheduled sync failed for: {sync_name}")

    return job

def setup_scheduler():
    """Set up scheduler with cron jobs for each sync configuration"""
    config = load_config()
    scheduler = BackgroundScheduler()

    for sync in config.get('syncs', []):
        if not sync.get('enabled', True):
            continue

        sync_name = sync.get('syncName', 'unknown')

        # Get schedule: use per-sync schedule or fall back to global interval
        if 'schedule' in sync:
            # Cron expression provided
            cron_expr = sync['schedule']
            try:
                # Parse cron expression: "minute hour day month day_of_week"
                parts = cron_expr.split()
                if len(parts) != 5:
                    logger.error(f"Invalid cron expression for '{sync_name}': {cron_expr}")
                    continue

                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )

                scheduler.add_job(
                    create_sync_job(sync),
                    trigger=trigger,
                    id=f'sync_{sync_name}',
                    name=f'Sync: {sync_name}'
                )
                logger.info(f"Scheduled sync '{sync_name}' with cron: {cron_expr}")
            except Exception as e:
                logger.error(f"Failed to schedule '{sync_name}': {e}")
        else:
            # Use global interval as fallback
            scheduler.add_job(
                create_sync_job(sync),
                'interval',
                minutes=SYNC_INTERVAL_MINUTES,
                id=f'sync_{sync_name}',
                name=f'Sync: {sync_name}',
                next_run_time=datetime.now()  # Run immediately on startup
            )
            logger.info(f"Scheduled sync '{sync_name}' with interval: {SYNC_INTERVAL_MINUTES} minutes")

    return scheduler

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/sync', methods=['POST'])
@require_api_key
def sync():
    """Manual sync trigger endpoint"""
    data = request.get_json()

    if not data or 'syncName' not in data:
        return jsonify({"error": "Missing syncName in request body"}), 400

    sync_name = data['syncName']
    logger.info(f"Manual sync requested for: {sync_name}")

    # Load config and find sync
    config = load_config()
    sync_config = None
    for s in config.get('syncs', []):
        if s.get('syncName') == sync_name:
            sync_config = s
            break

    if not sync_config:
        return jsonify({"error": f"Sync configuration not found: {sync_name}"}), 404

    if not sync_config.get('enabled', True):
        return jsonify({"error": f"Sync configuration is disabled: {sync_name}"}), 400

    # Run sync
    result = run_imapsync(sync_config)

    if result.get('success'):
        return jsonify({
            "status": "success",
            "syncName": sync_name,
            "timestamp": datetime.now().isoformat(),
            "message": "Sync completed successfully"
        }), 200
    else:
        return jsonify({
            "status": "failed",
            "syncName": sync_name,
            "timestamp": datetime.now().isoformat(),
            "error": result.get('error'),
            "stderr": result.get('stderr')
        }), 500

@app.route('/syncs', methods=['GET'])
@require_api_key
def list_syncs():
    """List all configured sync configurations"""
    config = load_config()
    syncs = []
    for sync in config.get('syncs', []):
        sync_info = {
            "syncName": sync.get('syncName'),
            "enabled": sync.get('enabled', True)
        }

        # Add schedule info
        if 'schedule' in sync:
            sync_info['schedule'] = sync['schedule']
        else:
            sync_info['schedule'] = f"*/{SYNC_INTERVAL_MINUTES} * * * *"

        # Try to extract user info from arguments or legacy format
        if 'arguments' in sync:
            args = sync['arguments']
            for i, arg in enumerate(args):
                if arg == '--user1' and i + 1 < len(args):
                    sync_info['user1'] = args[i + 1]
                if arg == '--user2' and i + 1 < len(args):
                    sync_info['user2'] = args[i + 1]
        else:
            sync_info['user1'] = sync.get('user1')
            sync_info['user2'] = sync.get('user2')

        syncs.append(sync_info)
    return jsonify({"syncs": syncs})

if __name__ == '__main__':
    logger.info("Starting Mail Sync API Server")
    logger.info(f"Default sync interval: {SYNC_INTERVAL_MINUTES} minutes")

    # Validate configuration before starting
    try:
        validate_configuration()
    except ValueError as e:
        logger.error(f"Startup failed: {e}")
        exit(1)

    # Initialize scheduler for automatic syncs
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Start Flask API server
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Server stopped")
