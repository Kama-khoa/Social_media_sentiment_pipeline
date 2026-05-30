import argparse
import sys
from pathlib import Path

# Set console output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Create experiment directories locally and on Google Drive")
    parser.add_argument(
        "--drive-path", 
        type=str, 
        default=r"G:\My Drive", 
        help="Đường dẫn đến thư mục Google Drive (ví dụ: G:\\My Drive)"
    )
    args = parser.parse_args()
    
    root = Path(__file__).parent.parent
    local_exp_dir = root / "experiments"
    
    # Danh sách các thư mục con ở local
    local_subdirs = [
        local_exp_dir / "phobert_sentiment_v2_baseline",
        local_exp_dir / "velectra_ner_v2_baseline",
        local_exp_dir / "reports",
        local_exp_dir / "error_analysis"
    ]
    
    print("Khởi tạo thư mục thực nghiệm ở local...")
    for d in local_subdirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
        print(f"  -> Created local directory: {d.name}")
        
    # Khởi tạo trên Google Drive
    drive_base = Path(args.drive_path)
    if drive_base.exists():
        drive_exp_dir = drive_base / "experiments"
        drive_subdirs = [
            drive_exp_dir / "phobert_sentiment_v2_baseline",
            drive_exp_dir / "velectra_ner_v2_baseline",
            drive_exp_dir / "reports",
            drive_exp_dir / "error_analysis"
        ]
        
        print(f"\nKhởi tạo thư mục thực nghiệm trên Google Drive tại: {drive_base}...")
        for d in drive_subdirs:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  -> Created Drive directory: experiments/{d.name}")
        print("\n[HOÀN TẤT] Khởi tạo các thư mục thực nghiệm trên Drive thành công!")
    else:
        print(f"\n[BỎ QUA] Không tìm thấy ổ đĩa Google Drive tại '{drive_base}'. Vui lòng kiểm tra lại Google Drive Desktop hoặc cung cấp tham số --drive-path chính xác.")

if __name__ == "__main__":
    main()
