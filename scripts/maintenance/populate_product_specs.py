import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]

def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)

def get_specs_for_product(name: str, category: str, brand: str, release_year: int) -> dict:
    specs = {}
    name_lower = name.lower()
    brand = brand or "unknown"
    release_year = release_year or 2024
    
    # ── ĐIỆN THOẠI ──────────────────────────────────────────────────────────
    if category == "Điện thoại":
        specs["screen_technology"] = "OLED"
        specs["screen_size_inches"] = 6.1
        specs["ram_gb"] = 8
        specs["storage_gb"] = 128
        specs["battery_mah"] = 4000
        specs["chipset"] = "Chipset tiêu chuẩn"
        specs["generation"] = f"{brand} {release_year}"
        specs["release_date"] = f"{release_year}-10"
        
        if brand == "Apple":
            specs["screen_technology"] = "Super Retina XDR OLED"
            if "pro max" in name_lower:
                specs["screen_size_inches"] = 6.9 if release_year >= 2025 else (6.7 if release_year >= 2020 else 6.5)
                specs["ram_gb"] = 12 if release_year >= 2025 else (8 if release_year >= 2023 else 6)
                specs["storage_gb"] = 256
                specs["battery_mah"] = 4900 if release_year >= 2025 else (4685 if release_year == 2024 else 4422)
            elif "plus" in name_lower:
                specs["screen_size_inches"] = 6.7
                specs["ram_gb"] = 8 if release_year >= 2024 else 6
                specs["storage_gb"] = 128
                specs["battery_mah"] = 4674 if release_year == 2024 else 4383
            elif "pro" in name_lower:
                specs["screen_size_inches"] = 6.3 if release_year >= 2024 else 6.1
                specs["ram_gb"] = 12 if release_year >= 2025 else (8 if release_year >= 2023 else 6)
                specs["storage_gb"] = 128
                specs["battery_mah"] = 3582 if release_year == 2024 else (3274 if release_year == 2023 else 3200)
            elif "mini" in name_lower:
                specs["screen_size_inches"] = 5.4
                specs["ram_gb"] = 4
                specs["storage_gb"] = 128
                specs["battery_mah"] = 2438 if "13" in name_lower else 2227
            elif "air" in name_lower: # iPhone 17 Air
                specs["screen_size_inches"] = 6.6
                specs["ram_gb"] = 8
                specs["storage_gb"] = 128
                specs["battery_mah"] = 3000
            else: # iPhone thường
                specs["screen_size_inches"] = 6.1
                specs["ram_gb"] = 8 if release_year >= 2024 else (6 if release_year >= 2022 else 4)
                specs["storage_gb"] = 128
                specs["battery_mah"] = 3561 if release_year == 2024 else (3349 if release_year == 2023 else 3279)
            
            # Chipset
            if "pro" in name_lower:
                specs["chipset"] = f"Apple A{release_year - 2006} Pro"
            else:
                specs["chipset"] = f"Apple A{release_year - 2006}" if release_year >= 2024 else f"Apple A{release_year - 2007}"
            
            # Generation & Release Date
            if "17" in name_lower:
                specs["generation"] = "iPhone 17 Series"
                specs["release_date"] = "2025-09"
            elif "16" in name_lower:
                specs["generation"] = "iPhone 16 Series"
                specs["release_date"] = "2024-09"
            elif "15" in name_lower:
                specs["generation"] = "iPhone 15 Series"
                specs["release_date"] = "2023-09"
            elif "14" in name_lower:
                specs["generation"] = "iPhone 14 Series"
                specs["release_date"] = "2022-09"
            elif "13" in name_lower:
                specs["generation"] = "iPhone 13 Series"
                specs["release_date"] = "2021-09"
            elif "12" in name_lower:
                specs["generation"] = "iPhone 12 Series"
                specs["release_date"] = "2020-10"
            elif "11" in name_lower:
                specs["generation"] = "iPhone 11 Series"
                specs["release_date"] = "2019-09"
                
        elif brand == "Samsung":
            specs["screen_technology"] = "Dynamic AMOLED 2X"
            if "fold" in name_lower:
                specs["screen_size_inches"] = 7.6
                specs["ram_gb"] = 12
                specs["storage_gb"] = 256
                specs["battery_mah"] = 4400
                specs["chipset"] = "Snapdragon 8 Gen 3" if release_year == 2024 else ("Snapdragon 8 Gen 4" if release_year == 2025 else "Snapdragon 8 Gen 2")
                specs["generation"] = f"Galaxy Z Fold{name_lower.split('fold')[-1].strip().upper()}" if "fold" in name_lower else "Galaxy Z Fold"
                specs["release_date"] = f"{release_year}-07"
            elif "flip" in name_lower:
                specs["screen_size_inches"] = 6.7
                specs["ram_gb"] = 12 if release_year >= 2024 else 8
                specs["storage_gb"] = 256
                specs["battery_mah"] = 4000 if release_year >= 2024 else 3700
                specs["chipset"] = "Snapdragon 8 Gen 3" if release_year == 2024 else ("Snapdragon 8 Gen 4" if release_year == 2025 else "Snapdragon 8 Gen 2")
                specs["generation"] = f"Galaxy Z Flip{name_lower.split('flip')[-1].strip().upper()}" if "flip" in name_lower else "Galaxy Z Flip"
                specs["release_date"] = f"{release_year}-07"
            elif "ultra" in name_lower:
                specs["screen_size_inches"] = 6.8
                specs["ram_gb"] = 16 if release_year >= 2026 else 12
                specs["storage_gb"] = 256
                specs["battery_mah"] = 5000
                specs["chipset"] = "Snapdragon 8 Gen 3" if release_year == 2024 else ("Snapdragon 8 Elite" if release_year == 2025 else "Snapdragon 8 Gen 5")
                specs["generation"] = "Galaxy S Ultra"
                specs["release_date"] = f"{release_year}-01"
            elif "plus" in name_lower or "+" in name_lower:
                specs["screen_size_inches"] = 6.7
                specs["ram_gb"] = 12 if release_year >= 2024 else 8
                specs["storage_gb"] = 256
                specs["battery_mah"] = 4900
                specs["chipset"] = "Exynos 2400" if release_year == 2024 else "Snapdragon 8 Gen 2"
                specs["generation"] = "Galaxy S Plus"
                specs["release_date"] = f"{release_year}-01"
            elif "fe" in name_lower:
                specs["screen_size_inches"] = 6.4
                specs["ram_gb"] = 8
                specs["storage_gb"] = 128
                specs["battery_mah"] = 4500
                specs["chipset"] = "Exynos 2400e" if release_year >= 2024 else "Exynos 2200"
                specs["generation"] = "Galaxy FE"
                specs["release_date"] = f"{release_year}-10"
            else: # Dòng S thường hoặc dòng A/M
                if "galaxy s" in name_lower:
                    specs["screen_size_inches"] = 6.2 if release_year >= 2024 else 6.1
                    specs["ram_gb"] = 8
                    specs["storage_gb"] = 128
                    specs["battery_mah"] = 4000 if release_year >= 2024 else 3900
                    specs["chipset"] = "Exynos 2400" if release_year == 2024 else "Snapdragon 8 Gen 2"
                    specs["generation"] = "Galaxy S Series"
                    specs["release_date"] = f"{release_year}-01"
                else: # Dòng A/M
                    specs["screen_size_inches"] = 6.5
                    specs["ram_gb"] = 8 if ("a55" in name_lower or "a56" in name_lower or "a35" in name_lower or "a25" in name_lower) else 6
                    specs["storage_gb"] = 128
                    specs["battery_mah"] = 5000
                    specs["chipset"] = "Exynos 1480" if "a55" in name_lower else ("Exynos 1380" if "a35" in name_lower else "Dimensity 6100+")
                    specs["generation"] = "Galaxy A Series"
                    specs["release_date"] = f"{release_year}-03"
                    
        else: # Các hãng khác (Xiaomi, OPPO, vivo, OnePlus, Google...)
            if "ultra" in name_lower:
                specs["screen_size_inches"] = 6.8
                specs["ram_gb"] = 12 if release_year <= 2024 else 16
                specs["storage_gb"] = 256
                specs["battery_mah"] = 5000 if release_year <= 2024 else 5500
                specs["chipset"] = "Snapdragon 8 Gen 3" if release_year == 2024 else "Snapdragon 8 Elite"
                specs["generation"] = "Flagship Ultra"
            elif "pro" in name_lower:
                specs["screen_size_inches"] = 6.7
                specs["ram_gb"] = 12
                specs["storage_gb"] = 256
                specs["battery_mah"] = 4800 if release_year <= 2024 else 5200
                specs["chipset"] = "Snapdragon 8 Gen 3" if release_year == 2024 else "Dimensity 9400"
                specs["generation"] = "Flagship Pro"
            else:
                specs["screen_size_inches"] = 6.5
                specs["ram_gb"] = 8
                specs["storage_gb"] = 128
                specs["battery_mah"] = 5000
                specs["chipset"] = "Dimensity 7200" if brand == "Xiaomi" else "Snapdragon 7 Gen 3"
                specs["generation"] = "Standard Edition"
                
    # ── LAPTOP ──────────────────────────────────────────────────────────────
    elif category == "Laptop":
        specs["model_year"] = release_year
        specs["screen_size_inches"] = 14.0
        specs["ram_gb"] = 16
        specs["storage_gb"] = 512
        specs["chipset"] = "Intel Core i5"
        specs["processor"] = "Core i5"
        specs["graphics"] = "Intel Iris Xe"
        specs["generation"] = f"{brand} Laptop {release_year}"
        specs["release_date"] = f"{release_year}-06"
        
        if brand == "Apple":
            specs["graphics"] = "Apple GPU"
            if "macbook air" in name_lower:
                specs["chipset"] = "Apple M3" if "m3" in name_lower else ("Apple M2" if "m2" in name_lower else ("Apple M4" if "m4" in name_lower else "Apple M1"))
                specs["processor"] = specs["chipset"]
                specs["screen_size_inches"] = 15.3 if "15" in name_lower else (13.6 if ("m2" in name_lower or "m3" in name_lower or "m4" in name_lower) else 13.3)
                specs["ram_gb"] = 16 if ("m3" in name_lower or "m4" in name_lower) else 8
                specs["storage_gb"] = 256
                specs["generation"] = f"MacBook Air {specs['chipset']}"
                specs["release_date"] = "2024-03" if "m3" in name_lower else ("2022-07" if "m2" in name_lower else "2020-11")
            elif "macbook pro" in name_lower:
                specs["chipset"] = "Apple M3 Pro" if "m3 pro" in name_lower else ("Apple M4 Pro" if "m4 pro" in name_lower else ("Apple M3 Max" if "m3 max" in name_lower else "Apple M3"))
                specs["processor"] = specs["chipset"]
                specs["screen_size_inches"] = 16.2 if "16" in name_lower else 14.2
                specs["ram_gb"] = 18 if "pro" in specs["chipset"].lower() else (36 if "max" in specs["chipset"].lower() else 16)
                specs["storage_gb"] = 512
                specs["generation"] = f"MacBook Pro {specs['chipset']}"
                specs["release_date"] = "2024-11" if "m4" in name_lower else "2023-11"
                
        else: # Windows Laptops
            is_gaming = any(x in name_lower for x in ["gaming", "rog", "tuf", "strix", "scar", "legion", "loq", "predator", "helios", "nitro", "vector", "raider", "cyborg", "katana", "blade", "alienware"])
            if is_gaming:
                specs["screen_size_inches"] = 15.6 if ("15" in name_lower or "a15" in name_lower or "f15" in name_lower) else 16.0
                specs["ram_gb"] = 16 if release_year <= 2024 else 32
                specs["storage_gb"] = 512 if release_year <= 2023 else 1024
                specs["chipset"] = "Intel Core i7" if ("i7" in name_lower or "intel" in name_lower) else "AMD Ryzen 7"
                specs["processor"] = "Core i7-13700H" if "intel" in name_lower or "i7" in name_lower else "Ryzen 7 7840HS"
                specs["graphics"] = "NVIDIA GeForce RTX 4060"
                specs["generation"] = "Gaming Series"
                specs["release_date"] = f"{release_year}-05"
            else: # Dòng văn phòng mỏng nhẹ (XPS, Spectre, Zenbook, ThinkPad, Surface)
                specs["screen_size_inches"] = 13.4 if "13" in name_lower else 14.0
                specs["ram_gb"] = 16
                specs["storage_gb"] = 512
                specs["chipset"] = "Intel Core Ultra 7" if release_year >= 2024 else "Intel Core i7"
                specs["processor"] = "Core Ultra 7 155H" if release_year >= 2024 else "Core i7-1360P"
                specs["graphics"] = "Intel Arc Graphics" if release_year >= 2024 else "Intel Iris Xe"
                specs["generation"] = "Evo Premium Ultrabook"
                specs["release_date"] = f"{release_year}-04"
                
    # ── TAI NGHE ────────────────────────────────────────────────────────────
    elif category == "Tai nghe":
        specs["battery_hours"] = 6
        specs["connection"] = "Bluetooth 5.3"
        specs["connector"] = "USB-C"
        specs["noise_cancellation"] = False
        specs["generation"] = f"{brand} Audio"
        specs["release_date"] = f"{release_year}-09"
        
        is_anc = any(x in name_lower for x in ["pro", "anc", "ultra", "noise cancellation", "wh-1000", "wf-1000", "quietcomfort", "momentum", "steth", "major"])
        specs["noise_cancellation"] = is_anc
        
        is_overear = any(x in name_lower for x in ["max", "wh-", "quietcomfort headphones", "momentum 4", "major", "monitor", "space one", "aonic 50"])
        if is_overear:
            specs["battery_hours"] = 30 if ("sony" in name_lower or "bose" in name_lower) else (20 if "airpods max" in name_lower else 50)
            specs["generation"] = "Premium Over-Ear"
        else: # True Wireless
            specs["battery_hours"] = 6 if is_anc else 8
            specs["connector"] = "Lightning" if (brand == "Apple" and release_year <= 2022 and "pro" not in name_lower) else "USB-C"
            specs["generation"] = "True Wireless Earbuds"
            
    return specs

def run() -> None:
    client = get_client()
    print("Fetching active products from BigQuery...")
    query = f"""
        SELECT product_id, product_name, brand, category, release_year
        FROM `{PROJECT_ID}.{DATASET}.product_config`
        WHERE is_active = TRUE
    """
    rows = list(client.query(query).result())
    print(f"Found {len(rows)} products.")
    
    records = []
    now = datetime.now(timezone.utc).isoformat()
    
    for r in rows:
        p_id = r.product_id
        name = r.product_name
        brand = r.brand
        cat = r.category
        year = r.release_year
        
        specs = get_specs_for_product(name, cat, brand, year)
        
        # Mô tả sản phẩm thực tế
        desc = f"{name} được ra mắt vào năm {year} bởi {brand or 'nhà sản xuất'} thuộc danh mục {cat or 'thiết bị công nghệ'}."
        if cat == "Điện thoại":
            desc += f" Sở hữu màn hình {specs.get('screen_size_inches')} inch {specs.get('screen_technology')}, chip {specs.get('chipset')} cùng bộ nhớ {specs.get('storage_gb')}GB."
        elif cat == "Laptop":
            desc += f" Trang bị bộ vi xử lý {specs.get('processor')}, RAM {specs.get('ram_gb')}GB, ổ cứng {specs.get('storage_gb')}GB SSD cùng đồ họa {specs.get('graphics')}."
        elif cat == "Tai nghe":
            desc += f" Thiết bị được tích hợp kết nối {specs.get('connection')}, pin kéo dài tới {specs.get('battery_hours')} giờ{' và công nghệ chống ồn chủ động ANC.' if specs.get('noise_cancellation') else '.'}"
            
        records.append({
            "product_id": p_id,
            "specs_str": json.dumps(specs, ensure_ascii=False),
            "description": desc,
            "updated_at": now,
            "updated_by": "system_seeder"
        })
        
    print("Merging specifications into product_details table in BigQuery...")
    
    # Tạo bảng temp để load dữ liệu lên trước khi MERGE
    tmp_table = f"{PROJECT_ID}.{DATASET}._tmp_populate_specs_{int(datetime.now().timestamp())}"
    schema = [
        bigquery.SchemaField("product_id", "STRING"),
        bigquery.SchemaField("specs_str", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("updated_at", "TIMESTAMP"),
        bigquery.SchemaField("updated_by", "STRING")
    ]
    
    load_job = client.load_table_from_json(
        records, tmp_table,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
    )
    load_job.result()
    
    merge_sql = f"""
        MERGE `{PROJECT_ID}.{DATASET}.product_details` AS target
        USING `{tmp_table}` AS source
        ON target.product_id = source.product_id
        WHEN MATCHED THEN UPDATE SET
            target.specs = PARSE_JSON(source.specs_str),
            target.description = source.description,
            target.updated_at = source.updated_at,
            target.updated_by = source.updated_by
        WHEN NOT MATCHED THEN INSERT (
            product_id, specs, description, official_url, image_url, updated_at, updated_by
        ) VALUES (
            source.product_id, PARSE_JSON(source.specs_str), source.description, NULL, NULL, source.updated_at, source.updated_by
        )
    """
    
    client.query(merge_sql).result()
    client.delete_table(tmp_table, not_found_ok=True)
    print(f"Successfully populated specs for {len(records)} products.")

if __name__ == "__main__":
    run()
