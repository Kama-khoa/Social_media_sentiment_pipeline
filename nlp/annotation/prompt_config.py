"""
prompt_config.py — Cấu hình prompt cho LLM Sentiment Annotator.

Lưu trữ các Few-shot examples và cấu hình tham số cho prompt.
Dễ dàng thêm/sửa ví dụ để cải thiện chất lượng của Gemini.
"""
from typing import Dict, List

# Các khía cạnh hợp lệ
ASPECT_LABELS: List[str] = ["Pin", "Camera", "Màn hình", "Hiệu năng", "Thiết kế", "Giá"]

# Các cảm xúc hợp lệ
SENTIMENT_LABELS: List[str] = ["positive", "negative", "neutral"]

# Few-shot examples để hướng dẫn LLM
FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
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

def get_system_prompt() -> str:
    """Trả về phần hướng dẫn chính của System Prompt."""
    aspect_list = ", ".join(ASPECT_LABELS)
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
        "Ví dụ minh họa:\n"
    )
