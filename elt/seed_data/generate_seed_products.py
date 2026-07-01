"""Generate a reproducible 500-row sample technology product catalog."""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

OUTPUT = Path(__file__).with_name("seed_products.csv")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_value = ascii_value.replace("+", " plus ")
    ascii_value = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower())
    return ascii_value.strip("-")


def add(target: list[dict], brand: str, category: str, year: int, *names: str) -> None:
    for name in names:
        aliases = {name.lower()}
        if name.lower().startswith(brand.lower() + " "):
            aliases.add(name[len(brand) + 1:])
        target.append({
            "product_id": slugify(name),
            "product_name": name,
            "brand": brand,
            "category": category,
            "release_year": year,
            "aliases": "|".join(sorted(aliases)),
        })


def phone_products() -> list[dict]:
    rows: list[dict] = []
    add(rows, "Apple", "Điện thoại", 2025, "iPhone 17", "iPhone 17 Air", "iPhone 17 Pro", "iPhone 17 Pro Max")
    add(rows, "Apple", "Điện thoại", 2024, "iPhone 16", "iPhone 16 Plus", "iPhone 16 Pro", "iPhone 16 Pro Max", "iPhone 16e")
    add(rows, "Apple", "Điện thoại", 2023, "iPhone 15", "iPhone 15 Plus", "iPhone 15 Pro", "iPhone 15 Pro Max")
    add(rows, "Apple", "Điện thoại", 2022, "iPhone 14", "iPhone 14 Plus", "iPhone 14 Pro", "iPhone 14 Pro Max")
    add(rows, "Apple", "Điện thoại", 2021, "iPhone 13", "iPhone 13 mini", "iPhone 13 Pro", "iPhone 13 Pro Max")
    add(rows, "Apple", "Điện thoại", 2020, "iPhone 12", "iPhone 12 mini", "iPhone 12 Pro", "iPhone 12 Pro Max")

    for year, series in ((2026, "S26"), (2025, "S25"), (2024, "S24"), (2023, "S23"), (2022, "S22"), (2021, "S21"), (2020, "S20")):
        add(rows, "Samsung", "Điện thoại", year, *(f"Samsung Galaxy {series}{suffix}" for suffix in ("", "+", " Ultra", " FE")))
    for year, series in ((2025, "Z Fold7"), (2025, "Z Flip7"), (2024, "Z Fold6"), (2024, "Z Flip6"), (2023, "Z Fold5"), (2023, "Z Flip5"), (2022, "Z Fold4"), (2022, "Z Flip4")):
        add(rows, "Samsung", "Điện thoại", year, f"Samsung Galaxy {series}")
    for series in ("A06", "A16", "A26", "A36", "A56", "A05s", "A15", "A25", "A35", "A55", "A14", "A24", "A34", "A54", "M15", "M35", "M55"):
        add(rows, "Samsung", "Điện thoại", 2025, f"Samsung Galaxy {series}")

    for year, series in ((2025, "15"), (2024, "14"), (2023, "13"), (2022, "12"), (2021, "11")):
        add(rows, "Xiaomi", "Điện thoại", year, *(f"Xiaomi {series}{suffix}" for suffix in ("", " Pro", " Ultra", " Lite", "T", "T Pro")))
    for series in ("14", "13", "12", "11", "10"):
        add(rows, "Xiaomi", "Điện thoại", 2025, *(f"Redmi Note {series}{suffix}" for suffix in ("", " Pro", " Pro+", " 5G")))
    for model in ("F7", "F7 Pro", "X7", "X7 Pro", "M7", "M7 Pro", "F6", "F6 Pro", "X6", "X6 Pro", "M6", "M6 Pro"):
        add(rows, "POCO", "Điện thoại", 2025, f"POCO {model}")

    for series in ("X8", "X7", "X6", "X5", "X3"):
        add(rows, "OPPO", "Điện thoại", 2025, *(f"OPPO Find {series}{suffix}" for suffix in ("", " Pro", " Ultra")))
    for series in ("14", "13", "12", "11", "10", "8"):
        add(rows, "OPPO", "Điện thoại", 2025, *(f"OPPO Reno {series}{suffix}" for suffix in ("", " Pro", " Pro+")))

    for series in ("X200", "X100", "X90", "X80"):
        add(rows, "vivo", "Điện thoại", 2025, *(f"vivo {series}{suffix}" for suffix in ("", " Pro", " Ultra")))
    for series in ("V50", "V40", "V30", "V29", "V27"):
        add(rows, "vivo", "Điện thoại", 2025, *(f"vivo {series}{suffix}" for suffix in ("", " Pro")))

    for series in ("13", "12", "11", "10", "9"):
        add(rows, "OnePlus", "Điện thoại", 2025, *(f"OnePlus {series}{suffix}" for suffix in ("", "R", " Pro")))
    for series in ("9", "8", "7", "6"):
        add(rows, "Google", "Điện thoại", 2025, *(f"Google Pixel {series}{suffix}" for suffix in ("", " Pro", " Pro XL", "a")))
    for series in ("Magic7", "Magic6", "Magic5"):
        add(rows, "HONOR", "Điện thoại", 2025, *(f"HONOR {series}{suffix}" for suffix in ("", " Pro", " Lite")))
    for model in ("Phone (3)", "Phone (3a)", "Phone (3a) Pro", "Phone (2)", "Phone (2a)", "Phone (2a) Plus", "CMF Phone 1", "CMF Phone 2 Pro"):
        add(rows, "Nothing", "Điện thoại", 2025, f"Nothing {model}")
    for model in ("Edge 60 Pro", "Edge 60 Fusion", "Edge 50 Pro", "Edge 50 Fusion", "Razr 60 Ultra", "Razr 60", "Razr 50 Ultra", "Razr 50"):
        add(rows, "Motorola", "Điện thoại", 2025, f"Motorola {model}")
    for model in ("GT 7 Pro", "GT 7", "GT 6", "14 Pro+", "14 Pro", "13 Pro+", "13 Pro", "C75"):
        add(rows, "realme", "Điện thoại", 2025, f"realme {model}")
    for model in ("ROG Phone 9 Pro", "ROG Phone 9", "ROG Phone 8 Pro", "ROG Phone 8", "Zenfone 12 Ultra", "Zenfone 11 Ultra"):
        add(rows, "ASUS", "Điện thoại", 2025, f"ASUS {model}")

    return rows[:250]


def laptop_products() -> list[dict]:
    rows: list[dict] = []
    add(rows, "Apple", "Laptop", 2025, "MacBook Air 13 M4", "MacBook Air 15 M4", "MacBook Pro 14 M4", "MacBook Pro 14 M4 Pro", "MacBook Pro 14 M4 Max", "MacBook Pro 16 M4 Pro", "MacBook Pro 16 M4 Max")
    add(rows, "Apple", "Laptop", 2024, "MacBook Air 13 M3", "MacBook Air 15 M3", "MacBook Pro 14 M3", "MacBook Pro 14 M3 Pro", "MacBook Pro 16 M3 Pro")
    for family, models in {
        "Dell": ("XPS 13", "XPS 14", "XPS 16", "Inspiron 14", "Inspiron 16", "Latitude 5450", "Latitude 7450", "Precision 3590", "Alienware m16 R2", "Alienware x16 R2", "G15 5530"),
        "HP": ("Spectre x360 14", "Spectre x360 16", "OmniBook Ultra Flip 14", "OmniBook X 14", "Pavilion Plus 14", "Envy x360 14", "Victus 15", "Victus 16", "OMEN 16", "OMEN Transcend 14", "EliteBook 840 G11"),
        "Lenovo": ("ThinkPad X1 Carbon Gen 13", "ThinkPad X1 Yoga Gen 9", "ThinkPad T14 Gen 5", "ThinkBook 14 Gen 7", "Yoga Slim 7i", "Yoga Pro 9i", "IdeaPad Slim 5", "IdeaPad Pro 5", "Legion 5i", "Legion 7i", "Legion Pro 5i", "LOQ 15"),
        "ASUS": ("Zenbook 14 OLED", "Zenbook S 14 OLED", "Vivobook S 14 OLED", "Vivobook 15", "ROG Zephyrus G14", "ROG Zephyrus G16", "ROG Strix G16", "ROG Strix Scar 18", "TUF Gaming A15", "TUF Gaming F16", "ProArt P16"),
        "Acer": ("Swift Go 14", "Swift X 14", "Aspire 5", "Aspire 7", "Predator Helios Neo 16", "Predator Helios 18", "Nitro V 15", "Nitro 16", "TravelMate P4"),
        "MSI": ("Stealth 16 AI Studio", "Stealth 14 AI Studio", "Raider 18 HX", "Vector 16 HX", "Katana 15", "Cyborg 15", "Prestige 14 AI Evo", "Modern 14", "Creator Z17 HX Studio"),
        "Razer": ("Blade 14", "Blade 15", "Blade 16", "Blade 18"),
        "Microsoft": ("Surface Laptop 7 13.8", "Surface Laptop 7 15", "Surface Laptop Studio 2", "Surface Pro 11"),
        "Samsung": ("Galaxy Book5 Pro 14", "Galaxy Book5 Pro 16", "Galaxy Book5 360", "Galaxy Book4 Ultra", "Galaxy Book4 Pro"),
        "LG": ("gram 14", "gram 16", "gram 17", "gram Pro 16", "gram Style 14"),
        "Huawei": ("MateBook X Pro", "MateBook 14", "MateBook D 16", "MateBook D 14"),
        "Gigabyte": ("AORUS 16X", "AORUS 17X", "G6X", "AERO 16 OLED"),
    }.items():
        for model in models:
            add(rows, family, "Laptop", 2025, f"{family} {model}")
            if len(rows) < 150:
                add(rows, family, "Laptop", 2024, f"{family} {model} 2024")
    return rows[:150]


def headphone_products() -> list[dict]:
    rows: list[dict] = []
    catalog = {
        "Apple": ("AirPods 4", "AirPods 4 ANC", "AirPods Pro 2", "AirPods Max USB-C"),
        "Samsung": ("Galaxy Buds4 Pro", "Galaxy Buds4", "Galaxy Buds3 Pro", "Galaxy Buds3", "Galaxy Buds FE"),
        "Sony": ("WH-1000XM6", "WF-1000XM6", "WH-1000XM5", "WF-1000XM5", "ULT WEAR WH-ULT900N", "LinkBuds Fit", "LinkBuds Open"),
        "Bose": ("QuietComfort Ultra Headphones", "QuietComfort Headphones", "QuietComfort Ultra Earbuds", "QuietComfort Earbuds"),
        "Sennheiser": ("Momentum 4 Wireless", "Momentum True Wireless 4", "Accentum Plus Wireless", "Accentum Wireless", "HD 660S2"),
        "JBL": ("Tour Pro 3", "Live Beam 3", "Live Buds 3", "Tune Beam 2", "Tune 770NC", "Quantum TWS Air"),
        "Jabra": ("Elite 10 Gen 2", "Elite 8 Active Gen 2", "Elite 10", "Elite 8 Active", "Elite 4 Active"),
        "Nothing": ("Ear", "Ear (a)", "Ear (2)", "CMF Buds Pro 2", "CMF Buds 2 Plus"),
        "Xiaomi": ("Buds 5 Pro", "Buds 5", "Redmi Buds 6 Pro", "Redmi Buds 6", "Redmi Buds 5 Pro"),
        "Anker": ("Soundcore Liberty 4 Pro", "Soundcore Liberty 4 NC", "Soundcore Space One Pro", "Soundcore Space One", "Soundcore AeroFit Pro"),
        "Beats": ("Studio Pro", "Solo 4", "Fit Pro", "Studio Buds +", "Powerbeats Pro 2"),
        "Marshall": ("Major V", "Monitor III ANC", "Motif II ANC", "Minor IV"),
        "Audio-Technica": ("ATH-M50xBT2", "ATH-TWX9", "ATH-CKS50TW2", "ATH-S300BT"),
        "Bowers & Wilkins": ("Px8", "Px7 S3", "Pi8", "Pi6"),
        "Technics": ("EAH-AZ100", "EAH-AZ80", "EAH-A800"),
        "Shure": ("AONIC 50 Gen 2", "SE215", "SE846 Gen 2"),
        "Edifier": ("NeoBuds Pro 2", "W830NB", "WH950NB", "Stax Spirit S5"),
        "Huawei": ("FreeBuds Pro 4", "FreeBuds 6", "FreeClip", "FreeBuds SE 3"),
        "OPPO": ("Enco X3", "Enco Air4 Pro", "Enco Buds3 Pro", "Enco Free4"),
        "realme": ("Buds Air7 Pro", "Buds Air7", "Buds T310", "Buds Wireless 5 ANC"),
        "OnePlus": ("Buds Pro 3", "Buds 4", "Nord Buds 3 Pro", "Nord Buds 3"),
        "Google": ("Pixel Buds Pro 2", "Pixel Buds A-Series"),
        "Logitech": ("G PRO X 2 LIGHTSPEED", "G733 LIGHTSPEED", "Zone Wireless 2"),
        "Razer": ("BlackShark V2 Pro", "Barracuda Pro", "Hammerhead Pro HyperSpeed"),
        "SteelSeries": ("Arctis Nova Pro Wireless", "Arctis Nova 7", "Arctis GameBuds"),
    }
    for brand, models in catalog.items():
        add(rows, brand, "Tai nghe", 2025, *(f"{brand} {model}" for model in models))
    return rows[:100]


def main() -> None:
    rows = phone_products() + laptop_products() + headphone_products()
    if len(rows) != 500:
        raise ValueError(f"Expected 500 products, got {len(rows)}")
    product_ids = [row["product_id"] for row in rows]
    if len(product_ids) != len(set(product_ids)):
        raise ValueError("Duplicate product_id found")
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["product_id", "product_name", "brand", "category", "release_year", "aliases"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} sample products to {OUTPUT.name}")


if __name__ == "__main__":
    main()
