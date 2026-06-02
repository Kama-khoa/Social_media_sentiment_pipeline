"""Create product catalog tables before rebuilding dbt marts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from elt.seed_data.seed_loader import sync_product_spec_templates, sync_products
from schema.layer_0_config.init_config_tables import (
    create_product_aliases,
    create_product_config,
    create_product_detail_change_requests,
    create_product_details,
    create_product_resolution_candidates,
    create_product_spec_templates,
    create_video_product_overrides,
    create_sentence_product_target_overrides,
    get_client,
)


def run() -> None:
    client = get_client()
    create_product_config(client)
    create_product_aliases(client)
    create_product_details(client)
    create_product_spec_templates(client)
    create_product_resolution_candidates(client)
    create_video_product_overrides(client)
    create_sentence_product_target_overrides(client)
    create_product_detail_change_requests(client)
    product_result = sync_products(client)
    template_count = sync_product_spec_templates(client)
    print(f"Catalog migration complete: {product_result['products']} products, {product_result['aliases']} aliases, {template_count} templates.")
    print("Next: rebuild dbt models with --full-refresh.")


if __name__ == "__main__":
    run()
