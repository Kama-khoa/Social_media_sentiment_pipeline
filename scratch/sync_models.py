import os
import shutil
import sys
from pathlib import Path

# Set console output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

def sync_model(src_dir: Path, dst_dir: Path, model_name: str):
    if not src_dir.exists():
        print(f"[CẢNH BÁO] Không tìm thấy thư mục nguồn cho {model_name} tại: {src_dir}")
        return False
        
    print(f"\nĐang đồng bộ mô hình {model_name}...")
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    # Chỉ copy các file trực tiếp trong thư mục gốc, bỏ qua thư mục con (checkpoint-*)
    copied_files = 0
    for item in src_dir.iterdir():
        if item.is_file() and item.name != "desktop.ini":
            dst_file = dst_dir / item.name
            print(f"  -> Copying {item.name} ({item.stat().st_size / 1024 / 1024:.2f} MB)...")
            shutil.copy2(item, dst_file)
            copied_files += 1
            
    print(f"[THÀNH CÔNG] Đã đồng bộ {copied_files} files cho {model_name} về local tại: {dst_dir}")
    return True

def main():
    root = Path(__file__).parent.parent
    drive_base = Path("G:/My Drive/models")
    
    if not drive_base.exists():
        print(f"[LỖI] Không tìm thấy thư mục Google Drive tại {drive_base}.")
        print("Vui lòng đảm bảo Google Drive Desktop đang chạy và được gán ổ G:")
        sys.exit(1)
        
    # Định nghĩa nguồn và đích
    src_sentiment = drive_base / "phobert_sentiment_ls0p05_seed42"
    dst_sentiment = root / "models" / "phobert_sentiment"
    
    # src_aspect = drive_base / "velectra_aspect"
    # dst_aspect = root / "models" / "velectra_aspect"
    
    # Đồng bộ PhoBERT Sentiment
    sync_model(src_sentiment, dst_sentiment, "PhoBERT Sentiment (Best)")
    
    # Đồng bộ vELECTRA Aspect
    # sync_model(src_aspect, dst_aspect, "vELECTRA Aspect (Best)")
    
    print("\n=== ĐỒNG BỘ HOÀN TẤT ===")
    print("Bây giờ bạn có thể kiểm tra pipeline local bằng lệnh:")
    print("  python scratch/test_inference_pipeline.py")

if __name__ == "__main__":
    main()
