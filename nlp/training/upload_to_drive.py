import argparse
import shutil
import sys
from pathlib import Path

# Set console output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Copy dataset files to Google Drive")
    parser.add_argument(
        "--drive-path", 
        type=str, 
        default=r"G:\My Drive\dataset_hf", 
        help="Đường dẫn đến thư mục dataset_hf trên Google Drive"
    )
    args = parser.parse_args()

    # Thư mục gốc của project (nơi chứa data/)
    root = Path(__file__).parent.parent.parent
    local_data_dir = root / "data"
    
    drive_base_dir = Path(args.drive_path)
    
    # Kiểm tra xem ổ đĩa Google Drive có tồn tại không (VD: G:\My Drive)
    if not drive_base_dir.parent.exists():
        print(f"[LỖI] Không tìm thấy thư mục cha của Google Drive tại: {drive_base_dir.parent}")
        print("Vui lòng đảm bảo Google Drive Desktop đang chạy, hoặc cung cấp đúng tham số --drive-path")
        return

    # Đường dẫn nguồn
    src_sentiment = local_data_dir / "sentiment"
    src_ner = local_data_dir / "ner"
    
    # Đường dẫn đích
    dst_sentiment = drive_base_dir / "sentiment"
    dst_ner = drive_base_dir / "ner"
    
    print("Bắt đầu xuất dữ liệu lên Google Drive...")
    
    # Hàm copy đệ quy giữ nguyên cấu trúc thư mục
    def copy_dir_recursive(src, dst):
        if not src.exists():
            print(f"[CẢNH BÁO] Thư mục nguồn không tồn tại: {src}")
            return
            
        copied_count = 0
        for item in src.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(src)
                dest_file = dst / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)
                print(f"  -> Copied: {rel_path}")
                copied_count += 1
        print(f"  Tổng cộng đã copy: {copied_count} files")

    print(f"\n1. Exporting Sentiment data to:\n   {dst_sentiment}...")
    copy_dir_recursive(src_sentiment, dst_sentiment)
    
    print(f"\n2. Exporting NER data to:\n   {dst_ner}...")
    copy_dir_recursive(src_ner, dst_ner)
    
    print("\n[HOÀN TẤT] Quá trình copy lên Drive đã xong!")

if __name__ == "__main__":
    main()
