import time
from jira import JIRA
import json
from dotenv import load_dotenv

load_dotenv()
# Setup
jira = JIRA(os.getenv('JIRA_URL'), basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_TOKEN')))
seen_tasks = set()

print("Monitoring Jira for new tasks... (Press Ctrl+C to stop)")

# Initialize: Add existing tasks to 'seen_tasks' so you don't get 100 alerts at startup
initial_tasks = jira.search_issues('assignee = currentUser()')
for issue in initial_tasks:
    seen_tasks.add(issue)
print(f"Seen tasks: {str(seen_tasks)}")

try:
    while True:
        # Search for tasks assigned to you
        current_tasks = jira.search_issues('assignee = currentUser()')
        
        for issue in current_tasks:
            if issue.key not in seen_tasks:
                # --- THIS IS YOUR NOTIFICATION ---
                print(f"🔔 NEW TASK DETECTED: [{issue.key}] {issue.fields.summary}")
                full_data = json.dumps(issue.raw['fields'], indent=4)
                print(f"--- FULL DATA FOR {issue.key} ---")
                print(full_data)
                # ----------------------------------
                seen_tasks.add(issue.key)
        
        # Wait for 60 seconds before checking again
        time.sleep(60) 
except KeyboardInterrupt:
    print("Program stopped.")