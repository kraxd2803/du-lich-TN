import streamlit as st
import requests
import json
import re
import difflib
from unidecode import unidecode

# ======================================
# 🔧 UTILITIES
# ======================================

def normalize_string(text):
    """Chuẩn hóa chuỗi: viết thường, bỏ dấu, xóa ký tự đặc biệt."""
    if not text:
        return ""
    text = text.lower().strip()
    text = unidecode(text)
    text = text.replace("–", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fuzzy_match(user_input, normalized_lookup, threshold=0.45):
    """Tìm địa điểm gần đúng nhất theo fuzzy."""
    query = normalize_string(user_input)
    all_keys = list(normalized_lookup.keys())

    match = difflib.get_close_matches(query, all_keys, n=1, cutoff=threshold)
    if match:
        normalized_key = match[0]
        return normalized_lookup[normalized_key], difflib.SequenceMatcher(None, query, normalized_key).ratio()
    return None, 0.0


def detect_intent(text):
    """Nhận diện câu mới hay follow-up."""
    text = text.lower().strip()

    follow_words = ["tiếp", "nữa", "ok", "oke", "rồi sao", "sao nữa", "tiếp tục", "vậy"]
    if len(text.split()) <= 2:
        return "follow_up"
    if any(w in text for w in follow_words):
        return "follow_up"
    if "?" in text:
        return "new_question"
    return "new_question"

def detect_place_suggestion(text):
    text = normalize_string(text)

    keywords = [
        "di dau", "choi gi", "goi y", "noi nao", "dia diem",
        "cho vui", "cho nao thu vi", "nen di dau", "co gi vui",
        "dia diem du lich", "travel", "tham quan","di dau o tay ninh"
    ]

    return any(k in text for k in keywords)



# ======================================
# 🍜 DATABASE QUÁN ĂN
# ======================================

food_spots = {
    "núi bà đen": [
        ("Bánh canh Trảng Bàng Bé Năm", "đặc sản Trảng Bàng"),
        ("Quán Gà Hấp Hành 7 Núi", "đặc sản gà hấp"),
    ],
    "hồ dầu tiếng": [
        ("Hải Sản Tươi Sống Hữu Lợi", "tôm cá hồ rất tươi"),
        ("Quán Lộc Vừng", "view ngắm hoàng hôn"),
    ],
    "tòa thánh cao đài": [
        ("Bún riêu Bà Tám", "giá rẻ, ngon"),
        ("Cơm chay Tâm Đức", "quán chay gần nhất"),
    ],
    "làng nổi tân lập": [
        ("cá lóc nướng trui", "ngon quên lối về"),
        ("bánh xèo", "giòn rụm,ngon, trải nghiệm khó quên"),
    ],
}


# ======================================
# 📚 TẢI DỮ LIỆU TXT
# ======================================

DATA_FILE = "data_tayninh.txt"
IMAGES_FILE = "images.json"

try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_text = f.read()
except:
    raw_text = ""
    st.error("❌ Không tìm thấy file data_tayninh.txt")

tourism_data = {}
normalized_lookup = {}

current_key = None
for line in raw_text.splitlines():
    if line.startswith("###"):
        place = line.replace("###", "").strip().lower()
        tourism_data[place] = ""
        normalized_lookup[normalize_string(place)] = place
        current_key = place
    elif current_key:
        tourism_data[current_key] += line + "\n"


# ======================================
# 🖼 ẢNH
# ======================================

try:
    with open(IMAGES_FILE, "r", encoding="utf-8") as f:
        images = json.load(f)
except:
    images = {}
    st.warning("⚠️ Không tìm thấy images.json hoặc lỗi định dạng.")


# ======================================
# 🌐 GIAO DIỆN STREAMLIT
# ======================================

st.set_page_config(page_title="Chatbot Du Lịch Tây Ninh", page_icon="🗺️")
st.title("🗺️ Chatbot Du Lịch Tây Ninh – Beta Version")
st.caption("Made by Đăng Khoa 🔰 - 1.0")



# Session
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Bạn muốn khám phá địa điểm nào ở Tây Ninh hôm nay?"}
    ]

if "topic" not in st.session_state:
    st.session_state.topic = None


# HIển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ======================================
# ⌨️ NHẬN INPUT
# ======================================

user_input = st.chat_input("Nhập câu hỏi...")

if user_input:

    # Hiển thị câu người dùng
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Intent
    intent = detect_intent(user_input)

    # Fuzzy match
    matched_key, score = fuzzy_match(user_input, normalized_lookup)

    is_suggestion = detect_place_suggestion(user_input)


    # Nếu follow-up nhưng đã có topic → tiếp tục
    if intent == "follow_up" and st.session_state.topic:
        matched_key = st.session_state.topic

    # Nếu match tốt → dùng dữ liệu offline

    if is_suggestion:
        st.session_state.topic = None
            # Lấy 2 địa điểm đầu tiên đúng từ dữ liệu
        top_places = list(tourism_data.keys())[:2]

    # Ghép nội dung thật từ file
        places_text = ""
        for p in top_places:
            places_text += f"\n### {p}\n{tourism_data[p]}\n"
            
        prompt = f"""
        Bạn là hướng dẫn viên du lịch Tây Ninh.

        Người dùng muốn gợi ý địa điểm.

        Dựa trên dữ liệu:
        ---
        {places_text}
        ---

        Chỉ được trả lời dựa trên dữ liệu bên trên.
        Không được bịa ra địa danh mới, hoạt động mới hoặc thông tin ngoài dữ liệu.
    
        Hãy mô tả từng địa điểm có đề mục rõ ràng:
        - Giới thiệu ngắn gọn
        - Hoạt động thú vị
        - Thời gian nên đi

        Trả lời thật tự nhiên và thân thiện, chính xác và chỉ trả lời bằng tiếng việt.
        """

    elif matched_key:
        st.session_state.topic = matched_key
        context = tourism_data.get(matched_key, "").strip()

        prompt = f"""
        Bạn là hướng dẫn viên du lịch Tây Ninh.
        Người dùng hỏi: "{user_input}"

        Đây là thông tin về địa điểm **{matched_key}**:
        ---
        {context}
        ---

        Chỉ được trả lời dựa trên dữ liệu bên trên.
        Không được bịa ra địa danh mới, hoạt động mới hoặc thông tin ngoài dữ liệu.
        
        Hãy trả lời tự nhiên, thân thiện và chính xác dựa trên dữ liệu và trả lời bằng tiếng việt.
        Đồng thời cung cấp:
        - Tư vấn các hoạt động thú vị
        - thời gian nên đi
        """
        
    # Không match → hỏi toàn bộ dữ liệu
    else:
        st.session_state.topic = None
        prompt = f"""
        Bạn là hướng dẫn viên du lịch Tây Ninh.
        Dữ liệu du lịch:
        ---
        {places_text}
        ---

        Câu hỏi: "{user_input}"
        
        Chỉ được trả lời dựa trên dữ liệu bên trên.
        Không được bịa ra địa danh mới, hoạt động mới hoặc thông tin ngoài dữ liệu.

        Hãy xin lỗi và trả lời là nơi này sẽ được cập nhật sau và gợi ý:
        - Giới thiệu ngắn
        - Hoạt động thú vị
        - Thời gian nên đi
        """

    # ======================================
    # 🤖 GỌI OLLAMA
    # ======================================

    placeholder = st.chat_message("assistant").empty()
    placeholder.markdown("⏳ *Đang tạo câu trả lời...*")

    full_reply = ""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2:1.5b",
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.4},
            },
            stream=True
        )

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "response" in data:
                    full_reply += data["response"]
                    placeholder.markdown(full_reply + "▌")

    except Exception as e:
        full_reply = f"⚠️ Lỗi khi kết nối AI: {e}"

    # ======================================
    # 🔗 THÊM LINK GOOGLE MAPS
    # ======================================
    if st.session_state.topic:
        google_query = st.session_state.topic.replace(" ", "+")
        maps_url = f"https://www.google.com/maps/search/?api=1&query={google_query}+tay+ninh"
        full_reply += f"\n\n📍 **Google Maps:** [Xem bản đồ]({maps_url})"

    # Cập nhật trả lời
    placeholder.markdown(full_reply.strip())
    st.session_state.messages.append({"role": "assistant", "content": full_reply.strip()})

    # ======================================
    # 🍜 GỢI Ý QUÁN ĂN
    # ======================================
    if st.session_state.topic:
        key = st.session_state.topic.lower()
        if key in food_spots:
            with st.expander("🍜 Gợi ý quán ăn gần đây"):
                for name, note in food_spots[key]:
                    st.markdown(f"- **{name}** — _{note}_")

    # ======================================
    # 🖼 HIỂN THỊ ẢNH
    # ======================================
    if st.session_state.topic and st.session_state.topic in images:
        arr = images[st.session_state.topic]
        if arr:
            with st.expander(f"📸 Hình ảnh về {st.session_state.topic.title()}"):
                for img in arr:
                    st.image(img, use_container_width=True)
