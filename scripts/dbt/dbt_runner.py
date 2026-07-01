import os
import subprocess
import sys
from dotenv import load_dotenv
from pathlib import Path

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if credentials file exists
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if cred_path and not os.path.exists(cred_path):
        print(f"Warning: GOOGLE_APPLICATION_CREDENTIALS path does not exist: {cred_path}")
    
    # Change to transform directory
    root_dir = Path(__file__).resolve().parent.parent.parent
    transform_dir = root_dir / "transform"
    os.chdir(transform_dir)
    
    # Run dbt with arguments passed to this script
    args = sys.argv[1:]
    if not args:
        args = ['debug']
    
    print(f"Running dbt {' '.join(args)}...")
    result = subprocess.run(['dbt'] + args)
    sys.exit(result.returncode)
