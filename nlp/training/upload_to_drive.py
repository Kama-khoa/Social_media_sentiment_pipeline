import argparse
import shutil
from pathlib import Path

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
    src_phobert = local_data_dir / "sentiment" / "phobert"
    src_velectra = local_data_dir / "ner" / "velectra"
    
    # Đường dẫn đích
    dst_phobert = drive_base_dir / "sentiment" / "phobert"
    dst_velectra = drive_base_dir / "ner" / "velectra"
    
    print("Bắt đầu xuất dữ liệu lên Google Drive...")
    
    # Hàm copy và ghi đè
    def copy_dir(src, dst):
        if not src.exists():
            print(f"[CẢNH BÁO] Thư mục nguồn không tồn tại: {src}")
            return
            
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.glob("*"):
            if item.is_file():
                dest_file = dst / item.name
                shutil.copy2(item, dest_file)
                print(f"  -> Copied: {item.name}")

    print(f"\n1. Exporting PhoBERT data to:\n   {dst_phobert}...")
    copy_dir(src_phobert, dst_phobert)
    
    print(f"\n2. Exporting vELECTRA data to:\n   {dst_velectra}...")
    copy_dir(src_velectra, dst_velectra)
    
    print("\n[HOÀN TẤT] Quá trình copy lên Drive đã xong!")

if __name__ == "__main__":
    main()
