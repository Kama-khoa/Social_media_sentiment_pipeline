import os
import sys
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# Force standard output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def main():
    project_id = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ["BQ_DATASET"]
    client = bigquery.Client(project=project_id)
    
    with open("scripts/check_iphone_keywords.log", "w", encoding="utf-8") as f:
        f.write("--- Keywords ---\n")
        query = f"SELECT keyword_id, keyword_text, search_cluster FROM `{project_id}.{dataset}.keyword_config`"
        for row in client.query(query).result():
            f.write(f"ID: {row.keyword_id} | Text: {row.keyword_text} | Cluster: {row.search_cluster}\n")
            
        f.write("\n--- Products ---\n")
        try:
            query_prod = f"SELECT product_id, product_name, category FROM `{project_id}.{dataset}.product_config`"
            for row in client.query(query_prod).result():
                f.write(f"Product ID: {row.product_id} | Name: {row.product_name} | Category: {row.category}\n")
        except Exception as e:
            f.write(f"Error querying product_config: {e}\n")

if __name__ == "__main__":
    main()
