import os
from transformers import pipeline

def test_models_from_drive(drive_path="G:/My Drive/models"):
    """
    Script test thử các mô hình đã fine-tune lưu trên Google Drive.
    Lưu ý: Bạn cần cài Google Drive for Desktop để đồng bộ thư mục Drive về máy local (thường là ổ G:).
    Nếu đường dẫn Drive của bạn khác, hãy sửa biến `drive_path` cho phù hợp.
    """
    print(f"Đang tìm kiếm mô hình tại: {drive_path}")
    
    phobert_model_path = os.path.join(drive_path, "phobert_sentiment")
    velectra_model_path = os.path.join(drive_path, "velectra_aspect")
    
    # Kiểm tra xem mô hình có tồn tại trên local không
    if not os.path.exists(phobert_model_path):
        print(f"⚠️ Lỗi: Không tìm thấy thư mục mô hình PhoBERT tại {phobert_model_path}")
        print("Hãy đảm bảo bạn đã đồng bộ Google Drive về máy hoặc đổi đường dẫn đúng.")
        return
        
    if not os.path.exists(velectra_model_path):
        print(f"⚠️ Lỗi: Không tìm thấy thư mục mô hình vELECTRA tại {velectra_model_path}")
        return

    print("\n[1/2] Đang tải mô hình phân loại cảm xúc (PhoBERT)...")
    sentiment_analyzer = pipeline(
        "text-classification", 
        model=phobert_model_path, 
        tokenizer=phobert_model_path
    )
    
    print("[2/2] Đang tải mô hình trích xuất khía cạnh (vELECTRA)...")
    aspect_extractor = pipeline(
        "token-classification", 
        model=velectra_model_path, 
        tokenizer=velectra_model_path, 
        aggregation_strategy="simple"
    )

    print("\n✅ Tải mô hình thành công! Bạn có thể nhập các câu bình luận để test (Nhập 'q' để thoát).")
    print("-" * 60)
    
    while True:
        text = input("\nNhập câu bình luận: ")
        if text.strip().lower() in ['q', 'quit', 'exit']:
            break
            
        if not text.strip():
            continue
            
        print("\n--- Kết quả Trích xuất Khía cạnh (Aspects) ---")
        aspects = aspect_extractor(text)
        if not aspects:
            print("Không tìm thấy khía cạnh nào.")
        else:
            for item in aspects:
                print(f"  - Khía cạnh: {item['entity_group']}, Từ: '{item['word']}', Độ tự tin: {item['score']:.4f}")

        print("\n--- Kết quả Phân loại Cảm xúc (Sentiment) ---")
        sentiments = sentiment_analyzer(text)
        for item in sentiments:
            print(f"  - Cảm xúc: {item['label']}, Độ tự tin: {item['score']:.4f}")
            
if __name__ == "__main__":
    # Thay đổi đường dẫn tới thư mục gốc chứa các models trên Google Drive của bạn
    test_models_from_drive(drive_path="G:/My Drive/models")
