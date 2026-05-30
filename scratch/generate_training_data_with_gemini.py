import json
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import được module nlp
sys.path.append(str(Path(__file__).parent.parent))

from nlp.annotation.gemini_annotator import GeminiAnnotator

def generate_sample_data():
    gemini = GeminiAnnotator(batch_size=5)
    
    # Một số câu mẫu lấy từ MXH
    raw_sentences = [
        "Màn hình đẹp, độ sáng cao ra nắng nhìn rõ",
        "Pin tuột như uống nước, mới dùng 2 tiếng đã hết",
        "Máy nóng quá, chơi game một chút là muốn phỏng tay",
        "Thiết kế cũng bình thường, không ấn tượng lắm",
        "Giá này thà mua iPhone cũ còn hơn",
        "Camera chụp đêm khá nhiễu, không đẹp như quảng cáo",
        "Màn hình tần số quét 120Hz vuốt rất mượt nhưng pin thì hao nhanh",
        "Giao hàng siêu tốc, gói hàng cẩn thận"
    ]
    
    print(f"Đang gửi {len(raw_sentences)} câu lên Gemini để gán nhãn...")
    results = gemini.annotate_all(raw_sentences)
    
    output_path = Path(__file__).parent.parent / "data" / "export_for_colab" / "gemini_annotated_sample.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"Hoàn thành! Đã lưu {len(results)} kết quả tại: {output_path}")

if __name__ == "__main__":
    generate_sample_data()
