import os
import sys
import httpx
from urllib.parse import quote

# Assuming running locally on 8080 with admin:admin
client = httpx.Client(base_url="http://localhost:8080", auth=("admin", "admin"))
dags = client.get("/api/v1/dags").json()
print("DAGs:", [d["dag_id"] for d in dags.get("dags", [])])

for dag_id in ["youtube_daily_extraction_dag", "sentiment_analysis_dag", "analytics_dag"]:
    try:
        runs = client.get(f"/api/v1/dags/{dag_id}/dagRuns?limit=1&order_by=-start_date").json()
        if not runs.get("dag_runs"):
            print(f"No runs for {dag_id}")
            continue
        run = runs["dag_runs"][0]
        run_id = run["run_id"]
        print(f"\n{dag_id} run_id: {run_id}")
        
        # 1. Unencoded
        try:
            r1 = client.get(f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances")
            print("Unencoded taskInstances status:", r1.status_code)
            if r1.status_code == 200:
                print("Tasks:", len(r1.json().get("task_instances", [])))
            else:
                print("Error:", r1.text[:100])
        except Exception as e:
            print("Unencoded error:", str(e))
            
        # 2. Encoded
        try:
            r2 = client.get(f"/api/v1/dags/{dag_id}/dagRuns/{quote(run_id)}/taskInstances")
            print("Encoded taskInstances status:", r2.status_code)
            if r2.status_code == 200:
                print("Tasks:", len(r2.json().get("task_instances", [])))
            else:
                print("Error:", r2.text[:100])
        except Exception as e:
            print("Encoded error:", str(e))
            
    except Exception as e:
        print(f"Error on {dag_id}:", str(e))
