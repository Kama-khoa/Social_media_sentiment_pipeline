import os
import sys
import uuid
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

# Reconfigure stdout to use UTF-8 to prevent encoding errors on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

PROJECT_ID = os.environ.get('GCP_PROJECT_ID')
DATASET = os.environ.get('BQ_DATASET')

def run() -> None:
    if not PROJECT_ID or not DATASET:
        print("Error: GCP_PROJECT_ID and BQ_DATASET must be set in .env")
        sys.exit(1)

    print(f"Connecting to BigQuery. Project: {PROJECT_ID}, Dataset: {DATASET}")
    client = bigquery.Client(project=PROJECT_ID)

    # 1. Fetch active products from dim_products
    # dim_products is in <dataset>_marts dataset
    marts_dataset = f"{DATASET}_marts"
    dim_products_table = f"{PROJECT_ID}.{marts_dataset}.dim_products"
    
    print(f"Reading active products from {dim_products_table}...")
    q_products = f"""
        SELECT product_id, product_name 
        FROM `{dim_products_table}`
        WHERE is_active = TRUE
    """
    try:
        products = list(client.query(q_products).result())
        print(f"Found {len(products)} active products in dim_products.")
    except Exception as e:
        print(f"Error reading products from dim_products: {e}")
        print("Falling back to reading from product_config in raw dataset...")
        q_products_fallback = f"""
            SELECT product_id, product_name 
            FROM `{PROJECT_ID}.{DATASET}.product_config`
            WHERE is_active = TRUE
        """
        try:
            products = list(client.query(q_products_fallback).result())
            print(f"Found {len(products)} active products in product_config (fallback).")
        except Exception as ex:
            print(f"Fallback also failed: {ex}")
            sys.exit(1)

    # 2. Fetch existing keywords from keyword_config
    keyword_config_table = f"{PROJECT_ID}.{DATASET}.keyword_config"
    print(f"Reading existing keywords from {keyword_config_table}...")
    q_keywords = f"""
        SELECT keyword_id, keyword_text, search_cluster, is_active
        FROM `{keyword_config_table}`
    """
    try:
        keywords = list(client.query(q_keywords).result())
        print(f"Found {len(keywords)} total keywords in keyword_config.")
    except Exception as e:
        print(f"Error reading keywords: {e}")
        sys.exit(1)

    # 3. Identify missing keywords
    # A keyword is missing if there is no active keyword in keyword_config with:
    # search_cluster == product_id AND keyword_text.lower() == product_name.lower()
    missing_products = []
    for p in products:
        p_id = p.product_id
        p_name = p.product_name.strip()
        
        has_keyword = any(
            k.search_cluster == p_id and 
            k.keyword_text.strip().lower() == p_name.lower() and 
            k.is_active
            for k in keywords
        )
        if not has_keyword:
            missing_products.append(p)

    print(f"\nTotal products missing their canonical name keyword: {len(missing_products)}")
    if not missing_products:
        print("All products already have their canonical keywords. Nothing to do!")
        return

    # 4. Create new keyword records to insert
    now_iso = datetime.now(timezone.utc).isoformat()
    rows_to_insert = []
    
    print("\nPreparing keywords to insert:")
    for p in missing_products:
        keyword_id = f"kw_{uuid.uuid4().hex[:8]}"
        p_name = p.product_name.strip()
        p_id = p.product_id
        
        row = {
            "keyword_id": keyword_id,
            "keyword_text": p_name,
            "search_cluster": p_id,
            "is_active": True,
            "needs_backfill": True,
            "created_at": now_iso,
            "last_updated_at": now_iso
        }
        rows_to_insert.append(row)
        print(f"  - Generated ID: {keyword_id} | Text: '{p_name}' | Cluster: '{p_id}'")

    # 5. Insert rows into keyword_config using DML INSERT with query parameters in batches
    batch_size = 50
    total_inserted = 0
    print(f"\nInserting {len(missing_products)} keywords into {keyword_config_table} in batches of {batch_size}...")
    
    for i in range(0, len(missing_products), batch_size):
        batch = missing_products[i:i + batch_size]
        query_parts = []
        params = []
        
        for idx, p in enumerate(batch):
            keyword_id = f"kw_{uuid.uuid4().hex[:8]}"
            p_name = p.product_name.strip()
            p_id = p.product_id
            
            query_parts.append(f"(@id_{idx}, @text_{idx}, @cluster_{idx}, TRUE, TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())")
            params.extend([
                bigquery.ScalarQueryParameter(f"id_{idx}", "STRING", keyword_id),
                bigquery.ScalarQueryParameter(f"text_{idx}", "STRING", p_name),
                bigquery.ScalarQueryParameter(f"cluster_{idx}", "STRING", p_id)
            ])
            
        query = f"""
            INSERT INTO `{keyword_config_table}` 
            (keyword_id, keyword_text, search_cluster, is_active, needs_backfill, created_at, last_updated_at)
            VALUES {", ".join(query_parts)}
        """
        
        try:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            client.query(query, job_config=job_config).result()
            total_inserted += len(batch)
            print(f"  Inserted batch {i // batch_size + 1}: +{len(batch)} keywords (Total: {total_inserted}/{len(missing_products)})")
        except Exception as e:
            print(f"Error inserting batch starting at index {i}: {e}")
            sys.exit(1)
            
    print(f"\nSuccessfully added {total_inserted} product keywords to keyword_config!")

if __name__ == "__main__":
    run()
