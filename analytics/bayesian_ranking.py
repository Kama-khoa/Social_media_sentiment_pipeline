import sys
import subprocess
from pathlib import Path

def main():
    print("Bayesian Ranking calculation is processed natively via dbt SQL.")
    project_root = Path(__file__).parent.parent
    runner_path = project_root / "scripts/dbt/dbt_runner.py"
    cmd = [sys.executable, str(runner_path), "run", "--select", "agg_daily_product_ranking"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
