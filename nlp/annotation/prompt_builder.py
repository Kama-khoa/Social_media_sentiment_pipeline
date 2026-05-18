from __future__ import annotations

import json


class PromptBuilder:
    _ASPECT_LABELS = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]

    _FEW_SHOT_EXAMPLES = [
        {
            "sentence": "Pin trâu lắm, dùng cả ngày không hết",
            "aspect_label": "Pin",
            "segment_text": "Pin trâu",
            "sentiment_label": "positive",
        },
        {
            "sentence": "Camera chụp ảnh nhòe, mình rất thất vọng",
            "aspect_label": "Camera",
            "segment_text": "Camera chụp ảnh nhòe",
            "sentiment_label": "negative",
        },
        {
            "sentence": "Màn hình mượt nhưng hiệu năng chơi game hơi giật lag",
            "aspect_label": "Màn hình",
            "segment_text": "Màn hình mượt",
            "sentiment_label": "positive",
        },
        {
            "sentence": "Màn hình mượt nhưng hiệu năng chơi game hơi giật lag",
            "aspect_label": "Hiệu năng",
            "segment_text": "hiệu năng chơi game hơi giật lag",
            "sentiment_label": "negative",
        },
        {
            "sentence": "Thiết kế máy khá bình thường, giá chát quá",
            "aspect_label": "Thiết kế",
            "segment_text": "Thiết kế máy khá bình thường",
            "sentiment_label": "neutral",
        },
        {
            "sentence": "Thiết kế máy khá bình thường, giá chát quá",
            "aspect_label": "Giá",
            "segment_text": "giá chát quá",
            "sentiment_label": "negative",
        },
        {
            "sentence": "Sản phẩm giao hàng nhanh, shop đóng gói kỹ",
            "aspect_label": "NONE",
            "segment_text": "",
            "sentiment_label": "neutral",
        },
    ]

    def build_annotation_prompt(self, sentences: list[str]) -> str:
        aspect_list = ", ".join(self._ASPECT_LABELS)
        examples_json = json.dumps(self._FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)
        sentences_json = json.dumps(sentences, ensure_ascii=False, indent=2)
        return (
            "Bạn là chuyên gia phân tích cảm xúc sản phẩm công nghệ tiếng Việt.\n"
            "Nhiệm vụ: Với mỗi câu bình luận, xác định khía cạnh sản phẩm được đề cập"
            " và cảm xúc tương ứng.\n\n"
            f"Khía cạnh hợp lệ: {aspect_list}\n"
            "Nếu câu không đề cập đến bất kỳ khía cạnh nào,"
            " dùng aspect_label = \"NONE\" và segment_text = \"\".\n"
            "Nếu một câu có đề cập đến NHIỀU khía cạnh khác nhau, hãy tạo nhiều object tương ứng với mỗi khía cạnh cho câu đó.\n\n"
            "Cảm xúc hợp lệ: positive, negative, neutral\n\n"
            "Yêu cầu về kết quả:\n"
            "- Trả về JSON array thuần (chỉ chứa mảng các object).\n"
            "- Mỗi object có đúng 4 trường: sentence, aspect_label, segment_text, sentiment_label.\n"
            "- Trường `segment_text` phải là trích xuất đúng cụm từ trong câu gốc thể hiện khía cạnh đó.\n\n"
            f"Ví dụ minh họa:\n{examples_json}\n\n"
            f"Danh sách câu cần gán nhãn:\n{sentences_json}"
        )
