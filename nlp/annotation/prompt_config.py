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

# Few-shot đơn điểm bổ sung cho 6 khía cạnh:
# Pin, Camera, Màn hình, Hiệu năng, Thiết kế, Giá
FEW_SHOT_EXAMPLES.extend([
    # =========================
    # 1. Pin
    # =========================
    {
        "sentence": "Pin dùng rất lâu, sáng sạc đầy tối vẫn còn nhiều",
        "aspect_label": "Pin",
        "segment_text": "Pin dùng rất lâu",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Thời lượng pin ổn, đủ dùng cho một ngày học tập",
        "aspect_label": "Pin",
        "segment_text": "Thời lượng pin ổn",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Pin tụt nhanh quá, mới dùng vài tiếng đã phải sạc",
        "aspect_label": "Pin",
        "segment_text": "Pin tụt nhanh quá",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Máy hao pin khi xem video liên tục",
        "aspect_label": "Pin",
        "segment_text": "hao pin",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Dung lượng pin là 5000mAh theo đúng thông tin công bố",
        "aspect_label": "Pin",
        "segment_text": "Dung lượng pin là 5000mAh",
        "sentiment_label": "neutral",
    },
    {
        "sentence": "Pin ở mức bình thường, không quá nổi bật",
        "aspect_label": "Pin",
        "segment_text": "Pin ở mức bình thường",
        "sentiment_label": "neutral",
    },

    # =========================
    # 2. Camera
    # =========================
    {
        "sentence": "Camera chụp ban ngày rất nét và màu đẹp",
        "aspect_label": "Camera",
        "segment_text": "Camera chụp ban ngày rất nét và màu đẹp",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Ảnh selfie rõ mặt, màu da nhìn tự nhiên",
        "aspect_label": "Camera",
        "segment_text": "Ảnh selfie rõ mặt",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Camera thiếu sáng chụp rất bệt màu",
        "aspect_label": "Camera",
        "segment_text": "Camera thiếu sáng chụp rất bệt màu",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Ảnh chụp bị nhiễu nhiều khi dùng trong phòng tối",
        "aspect_label": "Camera",
        "segment_text": "Ảnh chụp bị nhiễu nhiều",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Camera sau có độ phân giải 50MP",
        "aspect_label": "Camera",
        "segment_text": "Camera sau có độ phân giải 50MP",
        "sentiment_label": "neutral",
    },
    {
        "sentence": "Camera trước chỉ ở mức dùng được",
        "aspect_label": "Camera",
        "segment_text": "Camera trước chỉ ở mức dùng được",
        "sentiment_label": "neutral",
    },

    # =========================
    # 3. Màn hình
    # =========================
    {
        "sentence": "Màn hình hiển thị sắc nét, màu sắc rất rực rỡ",
        "aspect_label": "Màn hình",
        "segment_text": "Màn hình hiển thị sắc nét",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Tần số quét màn hình cao nên vuốt rất mượt",
        "aspect_label": "Màn hình",
        "segment_text": "màn hình cao nên vuốt rất mượt",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Màn hình bị ám vàng khá khó chịu",
        "aspect_label": "Màn hình",
        "segment_text": "Màn hình bị ám vàng",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Ra ngoài trời thì màn hình hơi tối",
        "aspect_label": "Màn hình",
        "segment_text": "màn hình hơi tối",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Màn hình có kích thước 6.7 inch",
        "aspect_label": "Màn hình",
        "segment_text": "Màn hình có kích thước 6.7 inch",
        "sentiment_label": "neutral",
    },
    {
        "sentence": "Màn hình nhìn ở mức bình thường",
        "aspect_label": "Màn hình",
        "segment_text": "Màn hình nhìn ở mức bình thường",
        "sentiment_label": "neutral",
    },

    # =========================
    # 4. Hiệu năng
    # =========================
    {
        "sentence": "Hiệu năng rất mạnh, mở nhiều ứng dụng vẫn mượt",
        "aspect_label": "Hiệu năng",
        "segment_text": "Hiệu năng rất mạnh",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Chơi game ổn định, không bị tụt fps",
        "aspect_label": "Hiệu năng",
        "segment_text": "Chơi game ổn định",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Máy chạy chậm và hay bị đơ khi mở app nặng",
        "aspect_label": "Hiệu năng",
        "segment_text": "Máy chạy chậm và hay bị đơ",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Hiệu năng xử lý tác vụ nặng khá kém",
        "aspect_label": "Hiệu năng",
        "segment_text": "Hiệu năng xử lý tác vụ nặng khá kém",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Máy dùng chip Snapdragon 8 Gen 2",
        "aspect_label": "Hiệu năng",
        "segment_text": "Máy dùng chip Snapdragon 8 Gen 2",
        "sentiment_label": "neutral",
    },
    {
        "sentence": "Hiệu năng ở mức đủ dùng cho nhu cầu cơ bản",
        "aspect_label": "Hiệu năng",
        "segment_text": "Hiệu năng ở mức đủ dùng",
        "sentiment_label": "neutral",
    },

    # =========================
    # 5. Thiết kế
    # =========================
    {
        "sentence": "Thiết kế máy đẹp, cầm rất sang tay",
        "aspect_label": "Thiết kế",
        "segment_text": "Thiết kế máy đẹp",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Kiểu dáng gọn nhẹ, mang đi học rất tiện",
        "aspect_label": "Thiết kế",
        "segment_text": "Kiểu dáng gọn nhẹ",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Thiết kế quá dày, cầm lâu bị mỏi tay",
        "aspect_label": "Thiết kế",
        "segment_text": "Thiết kế quá dày",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Mặt lưng dễ bám vân tay nên nhìn nhanh bẩn",
        "aspect_label": "Thiết kế",
        "segment_text": "Mặt lưng dễ bám vân tay",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Thiết kế không có gì đặc biệt so với bản trước",
        "aspect_label": "Thiết kế",
        "segment_text": "Thiết kế không có gì đặc biệt",
        "sentiment_label": "neutral",
    },
    {
        "sentence": "Máy có thiết kế dạng thanh truyền thống",
        "aspect_label": "Thiết kế",
        "segment_text": "thiết kế dạng thanh truyền thống",
        "sentiment_label": "neutral",
    },

    # =========================
    # 6. Giá
    # =========================
    {
        "sentence": "Giá quá tốt so với cấu hình nhận được",
        "aspect_label": "Giá",
        "segment_text": "Giá quá tốt",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Mức giá này rất đáng mua",
        "aspect_label": "Giá",
        "segment_text": "Mức giá này rất đáng mua",
        "sentiment_label": "positive",
    },
    {
        "sentence": "Giá hơi cao so với chất lượng thực tế",
        "aspect_label": "Giá",
        "segment_text": "Giá hơi cao",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Bán đắt quá, cùng tầm tiền có nhiều lựa chọn ngon hơn",
        "aspect_label": "Giá",
        "segment_text": "Bán đắt quá",
        "sentiment_label": "negative",
    },
    {
        "sentence": "Giá niêm yết là 12 triệu",
        "aspect_label": "Giá",
        "segment_text": "Giá niêm yết là 12 triệu",
        "sentiment_label": "neutral",
    },
    {
        "sentence": "Mức giá ngang với các sản phẩm cùng phân khúc",
        "aspect_label": "Giá",
        "segment_text": "Mức giá ngang với các sản phẩm cùng phân khúc",
        "sentiment_label": "neutral",
    },
])

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
