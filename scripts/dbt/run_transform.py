import os
import subprocess
from dotenv import load_dotenv
from pathlib import Path

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if variables are loaded
    if not os.environ.get("GCP_PROJECT_ID"):
        print("Error: .env file not found or GCP_PROJECT_ID is missing")
        return

    # Change to transform directory
    root_dir = Path(__file__).resolve().parent.parent.parent
    transform_dir = root_dir / "transform"
    os.chdir(transform_dir)

    print("=== Running dbt seed ===")
    subprocess.run(
        ["dbt", "seed", "--select", "vn_slang_dictionary", "--full-refresh", "--profiles-dir", "."], 
        check=True
    )

    print("\n=== Running dbt run for staging, intermediate, marts ===")
    subprocess.run(
        ["dbt", "run", "--select", "staging", "intermediate", "marts", "--profiles-dir", "."], 
        check=True
    )

    print("\n=== Transformation complete! ===")

if __name__ == "__main__":
    main()
