import sys
from pathlib import Path

# Set console output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Thêm thư mục gốc vào sys.path để import được module nlp
sys.path.append(str(Path(__file__).parent.parent))

from nlp.inference.phobert_classifier import PhoBERTClassifier
from nlp.inference.velectra_extractor import VELECTRAExtractor

def test_pipeline_with_base_model():
    print("Loading base models from HuggingFace (thay vì thư mục local)...")
    
    try:
        # Ép dùng base model. Cảnh báo: Kết quả sẽ là ngẫu nhiên vì chưa được học!
        extractor = VELECTRAExtractor(model_dir="FPTAI/velectra-base-discriminator-cased")
        classifier = PhoBERTClassifier(model_dir="vinai/phobert-base-v2")
    except Exception as e:
        print(f"Lỗi khi khởi tạo model (có thể do thiếu thư viện hoặc mạng): {e}")
        return

    sentence = "Màn hình điện thoại này rất đẹp nhưng pin lại quá yếu."
    print(f"\nCâu test: {sentence}")
    print("-" * 50)

    # 1. Test Aspect Extraction
    try:
        aspects = extractor.extract(sentence)
        print("Kết quả VELECTRA (Base - Rác):", aspects)
    except Exception as e:
        print(f"Lỗi VELECTRA inference: {e}")

    # 2. Test Sentiment Classification
    try:
        # Giả sử VELECTRA tách được chữ 'Màn hình'
        sentiment_label, conf = classifier.classify(sentence, aspect_label="Màn hình")
        print(f"Kết quả PhoBERT (Base - Rác) cho 'Màn hình': {sentiment_label} (Confidence: {conf:.2f})")
    except Exception as e:
        print(f"Lỗi PhoBERT inference: {e}")

if __name__ == "__main__":
    test_pipeline_with_base_model()
