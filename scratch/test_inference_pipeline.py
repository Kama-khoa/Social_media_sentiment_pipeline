import sys
from pathlib import Path

# Set console output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Thêm thư mục gốc vào sys.path để import được module nlp
sys.path.append(str(Path(__file__).parent.parent))

from nlp.inference.phobert_classifier import PhoBERTClassifier
from nlp.inference.velectra_extractor import VELECTRAExtractor

def test_pipeline():
    root = Path(__file__).parent.parent
    local_sentiment = root / "models" / "phobert_sentiment"
    local_aspect = root / "models" / "velectra_aspect"
    
    use_local = local_sentiment.exists() and local_aspect.exists()
    
    try:
        if use_local:
            print("Loading local fine-tuned models from models/ directory...")
            extractor = VELECTRAExtractor()
            classifier = PhoBERTClassifier()
        else:
            print("Loading base models from HuggingFace (Cảnh báo: Kết quả sẽ là ngẫu nhiên vì chưa được học!)...")
            extractor = VELECTRAExtractor(model_dir="FPTAI/velectra-base-discriminator-cased")
            classifier = PhoBERTClassifier(model_dir="vinai/phobert-base-v2")
    except Exception as e:
        print(f"Lỗi khi khởi tạo model: {e}")
        return

    sentence = "Màn hình điện thoại này rất đẹp nhưng pin lại quá yếu."
    print(f"\nCâu test: {sentence}")
    print("-" * 50)

    # 1. Test Aspect Extraction
    try:
        aspects = extractor.extract(sentence)
        print("Kết quả VELECTRA Extractor:", aspects)
    except Exception as e:
        print(f"Lỗi VELECTRA inference: {e}")

    # 2. Test Sentiment Classification
    try:
        # Giả sử VELECTRA tách được chữ 'Màn hình' hoặc lấy trực tiếp nhãn Aspect
        for aspect in aspects:
            aspect_label = aspect.get("aspect_label", "NONE")
            if aspect_label != "O" and aspect_label != "NONE":
                sentiment_label, conf = classifier.classify(sentence, aspect_label=aspect_label)
                print(f"Kết quả PhoBERT Sentiment cho '{aspect_label}': {sentiment_label} (Confidence: {conf:.2f})")
    except Exception as e:
        print(f"Lỗi PhoBERT inference: {e}")

if __name__ == "__main__":
    test_pipeline()
