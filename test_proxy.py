import os
import requests

host = os.environ.get("BRIGHTDATA_PROXY_HOST")
port = os.environ.get("BRIGHTDATA_PROXY_PORT")
user = os.environ.get("BRIGHTDATA_USERNAME")
pwd = os.environ.get("BRIGHTDATA_PASSWORD")

if not all([host, port, user, pwd]):
    print("❌ THIẾU BIẾN MÔI TRƯỜNG TRONG CONTAINER:")
    print(f"HOST: {'Có' if host else 'Thiếu'}, PORT: {'Có' if port else 'Thiếu'}, USER: {'Có' if user else 'Thiếu'}, PASS: {'Có' if pwd else 'Thiếu'}")
    print("Vui lòng khởi động lại Docker bằng lệnh `docker compose ... down` và `up -d` để nạp lại file .env!")
    exit(1)

proxy_url = f"http://{user}:{pwd}@{host}:{port}"
proxies = {"http": proxy_url, "https": proxy_url}

print("1. Đang kiểm tra kết nối TRỰC TIẾP (Không qua proxy)...")
try:
    r = requests.get("https://api.ipify.org", timeout=10)
    print("✅ IP gốc của Container:", r.text.strip())
except Exception as e:
    print("❌ Lỗi kết nối trực tiếp:", type(e).__name__)

print("\n2. Đang kiểm tra kết nối QUY TẮC QUA PROXY BrightData...")
try:
    r = requests.get("https://api.ipify.org", proxies=proxies, timeout=15)
    print("✅ Thành công! Proxy cho phép truy cập. IP đầu ra của Proxy là:", r.text.strip())
except Exception as e:
    print("❌ Lỗi kết nối qua proxy:", repr(e))
