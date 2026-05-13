import os
import time
from jira import JIRA
import json
import redis
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables relative to the file directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Redis connection for notifications
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
try:
    redis_client = redis.from_url(redis_url, decode_responses=True)
    print(f"Connected to Redis at {redis_url}")
except Exception as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None

# Setup JIRA
try:
    jira = JIRA(os.getenv('JIRA_URL'), basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_TOKEN')))
except Exception as e:
    print(f"Error connecting to Jira: {e}")
    exit(1)

seen_tasks = set()

print("Monitoring Jira for new tasks... (Press Ctrl+C to stop)")

# Initialize: Add existing tasks to 'seen_tasks' so you don't get 100 alerts at startup
try:
    initial_tasks = jira.search_issues('assignee = currentUser()')
    for issue in initial_tasks:
        seen_tasks.add(issue.key)
    print(f"Seen tasks: {str(seen_tasks)}")
except Exception as e:
    print(f"Failed to fetch initial tasks: {e}")

try:
    while True:
        # Search for tasks assigned to you
        try:
            current_tasks = jira.search_issues('assignee = currentUser()')
            
            for issue in current_tasks:
                if issue.key not in seen_tasks:
                    # --- THIS IS YOUR NOTIFICATION ---
                    print(f"🔔 NEW TASK DETECTED: [{issue.key}] {issue.fields.summary}")
                    full_data = {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "description": issue.fields.description or "No description",
                        "url": issue.permalink()
                    }
                    print(f"--- DATA FOR {issue.key} ---")
                    print(json.dumps(full_data, indent=2))
                    
                    if redis_client:
                        try:
                            redis_client.publish('jira_notifications', json.dumps(full_data))
                            print(f"Published {issue.key} notification to Redis 'jira_notifications'")
                        except Exception as redis_err:
                            print(f"Failed to publish notification: {redis_err}")

                    # ----------------------------------
                    seen_tasks.add(issue.key)
        except Exception as search_err:
            print(f"Error searching JIRA: {search_err}")
        
        # Wait for 60 seconds before checking again
        time.sleep(60) 
except KeyboardInterrupt:
    print("Program stopped.")