import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from layer_0_config.init_config_tables import run as run_layer_0
from layer_1_raw.init_raw_tables import run as run_layer_1
from layer_2_staging.init_staging_tables import run as run_layer_2
from layer_3_intermediate.init_intermediate_tables import run as run_layer_3
from layer_4_marts.init_marts_tables import run as run_layer_4


def ensure_dataset_exists() -> None:
    project_id = os.environ["GCP_PROJECT_ID"]
    dataset_id = os.environ["BQ_DATASET"]

    client = bigquery.Client(project=project_id)
    dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset_ref.location = "US"

    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset {dataset_id}: OK\n")


def run() -> None:
    print("=== Social Media Sentiment Pipeline — Schema Init ===\n")

    ensure_dataset_exists()

    print("--- Layer 0: Config + Operational (5 tables) ---")
    run_layer_0()

    print("\n--- Layer 1: Raw External Tables (2 tables) ---")
    run_layer_1()

    print("\n--- Layer 2: Staging (2 tables) ---")
    run_layer_2()

    print("\n--- Layer 3: Intermediate (3 tables) ---")
    run_layer_3()

    print("\n--- Layer 4: Marts (4 tables) ---")
    run_layer_4()

    print("\n=== Done: 16/16 tables initialized. ===")


if __name__ == "__main__":
    run()
