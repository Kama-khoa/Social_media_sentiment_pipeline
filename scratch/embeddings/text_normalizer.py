from __future__ import annotations

import hashlib
import re


class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        """
        Làm sạch và chuẩn hóa văn bản.
        - Chuyển thành chữ thường.
        - Bỏ khoảng trắng thừa.
        - Xóa các ký tự đặc biệt không cần thiết nhưng giữ lại dấu câu quan trọng.
        """
        if not text:
            return ""
        
        text = str(text).lower()
        # Loại bỏ các emoji hoặc ký tự lạ (chỉ giữ lại chữ, số và dấu cơ bản)
        # Tùy bài toán có thể giữ lại emoji để phân tích sentiment, 
        # nhưng ở đây ta tập trung vào text để hash.
        text = re.sub(r'[^\w\s.,!?]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def generate_hash(text: str) -> str:
        """Sinh mã SHA256 cho chuỗi văn bản đã chuẩn hóa."""
        normalized_text = TextNormalizer.normalize(text)
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
