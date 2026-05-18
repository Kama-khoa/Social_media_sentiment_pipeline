import json
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from underthesea import word_tokenize

logger = logging.getLogger(__name__)

def prepare_data_for_colab(input_json_path: Path, output_dir: Path):
    """
    Đọc dữ liệu gán nhãn từ Gemini, chia Train/Val 
    và lưu thành định dạng chuẩn để dễ đưa lên Colab.
    """
    if not input_json_path.exists():
        print(f"Không tìm thấy file: {input_json_path}")
        return

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Lọc các record hợp lệ
    valid_data = []
    for item in data:
        # Tùy thuộc vào cấu trúc trả về từ GeminiAnnotator,
        # Nếu dùng hàm _attach_bio_tags thì item sẽ có "bio_tags"
        if "sentence" in item and "sentiment_label" in item and "bio_tags" in item:
            tokens = word_tokenize(item["sentence"])
            bio_tags = item["bio_tags"]
            if len(tokens) != len(bio_tags):
                logger.warning("Token/BIO mismatch (%d vs %d), skipping: %s", len(tokens), len(bio_tags), item["sentence"][:60])
                continue
            valid_data.append({
                "tokens": tokens,
                "ner_tags": bio_tags,
                "sentence": item["sentence"],
                "sentiment_label": item["sentiment_label"],
                "aspect_label": item["aspect_label"],
            })

    if not valid_data:
        print("Không có dữ liệu hợp lệ để export.")
        return

    # Chia tập train / val (80% / 20%)
    train_data, val_data = train_test_split(valid_data, test_size=0.2, random_state=42)

    output_dir.mkdir(parents=True, exist_ok=True)
    
    train_file = output_dir / "train.jsonl"
    val_file = output_dir / "val.jsonl"

    # Export dạng JSONL (tiện lợi nhất cho HuggingFace Datasets)
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(val_file, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Đã xuất dữ liệu thành công!")
    print(f"- Train: {len(train_data)} câu -> {train_file}")
    print(f"- Val: {len(val_data)} câu -> {val_file}")
    print("\n=> BẠN HÃY UPLOAD THƯ MỤC NÀY LÊN GOOGLE DRIVE CỦA BẠN ĐỂ SẴN SÀNG CHẠY COLAB.")

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent / "data" / "export_for_colab"
    input_file = root / "gemini_annotated_full.json"
    if not input_file.exists():
        input_file = root / "gemini_annotated_sample.json"
        print(f"[Info] Chưa có file full, dùng sample: {input_file}")
    out_dir = root / "dataset_hf"
    prepare_data_for_colab(input_file, out_dir)
