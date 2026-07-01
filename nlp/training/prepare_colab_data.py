import json
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from underthesea import word_tokenize

logger = logging.getLogger(__name__)

def prepare_data_for_colab(input_json_paths: list[Path], output_dir: Path):
    """
    Đọc dữ liệu gán nhãn từ Gemini, chia Train/Val 
    và lưu thành định dạng chuẩn để dễ đưa lên Colab.
    Hỗ trợ gộp nhiều file JSON đầu vào.
    """
    data = []
    for path in input_json_paths:
        if not path.exists():
            print(f"Không tìm thấy file: {path}, bỏ qua.")
            continue
        with open(path, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
            data.extend(file_data)
            print(f"Loaded {len(file_data)} records from {path}")

    if not data:
        print("Không có dữ liệu hợp lệ từ bất kỳ file nào.")
        return

    import random
    random.seed(42)
    # Lọc các record hợp lệ
    valid_data = []
    for item in data:
        if "sentence" in item and "sentiment_label" in item and "ner_tags" in item:
            # Lọc bỏ 100% câu NONE theo yêu cầu để tăng mật độ B/I tags
            if item.get("aspect_label") == "NONE":
                continue
                
            orig_tokens = item["tokens"]
            orig_tags = item["ner_tags"]
            
            new_tokens = []
            new_tags = []
            
            # Split tokens with spaces to prevent alignment bugs in HF Tokenizer
            for t, tag in zip(orig_tokens, orig_tags):
                parts = str(t).split()
                if not parts:
                    continue
                new_tokens.extend(parts)
                # If it's a B- tag, the first part is B-, subsequent parts are I-
                if tag.startswith("B-"):
                    new_tags.append(tag)
                    i_tag = "I-" + tag[2:]
                    new_tags.extend([i_tag] * (len(parts) - 1))
                else:
                    new_tags.extend([tag] * len(parts))
            
            valid_data.append({
                "tokens": new_tokens,
                "ner_tags": new_tags,
                "sentence": item["sentence"],
                "sentiment_label": item["sentiment_label"],
                "aspect_label": item.get("aspect_label", "NONE"),
            })
        elif "sentence" in item and "sentiment_label" in item and "bio_tags" in item:
            # Fallback for old key format
            # Lọc bỏ 100% câu NONE theo yêu cầu để tăng mật độ B/I tags
            if item.get("aspect_label") == "NONE":
                continue
                
            orig_tokens = item.get("tokens", [])
            orig_tags = item["bio_tags"]
            if not orig_tokens:
                from underthesea import word_tokenize
                orig_tokens = word_tokenize(item["sentence"])
                
            if len(orig_tokens) != len(orig_tags):
                continue
                
            new_tokens = []
            new_tags = []
            for t, tag in zip(orig_tokens, orig_tags):
                parts = str(t).split()
                if not parts:
                    continue
                new_tokens.extend(parts)
                if tag.startswith("B-"):
                    new_tags.append(tag)
                    i_tag = "I-" + tag[2:]
                    new_tags.extend([i_tag] * (len(parts) - 1))
                else:
                    new_tags.extend([tag] * len(parts))

            valid_data.append({
                "tokens": new_tokens,
                "ner_tags": new_tags,
                "sentence": item["sentence"],
                "sentiment_label": item["sentiment_label"],
                "aspect_label": item.get("aspect_label", "NONE"),
            })

    if not valid_data:
        print("Không có dữ liệu hợp lệ để export.")
        return

    # Chia tập train / val (80% / 20%)
    from sklearn.model_selection import train_test_split
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
    
    input_files = [
        root / "gemini_annotated_full.json",
        root / "gemini_annotated_pos_neg.json"
    ]
    
    # Nếu chưa có full, dùng sample fallback
    if not (root / "gemini_annotated_full.json").exists() and (root / "gemini_annotated_sample.json").exists():
        input_files[0] = root / "gemini_annotated_sample.json"
        print(f"[Info] Chưa có file full, dùng sample fallback cho file chính.")
        
    # Lưu thẳng vào Google Drive
    out_dir = Path("G:/My Drive/dataset_hf")
    prepare_data_for_colab(input_files, out_dir)
