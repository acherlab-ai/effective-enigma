# Bringh Bot - Zalo AI Chat Bot

🐾 **Bringh** là một bot trò chuyện AI trên Zalo với tính cách thân thiện, tự nhiên như một người bạn thật sự.

## ✨ Tính năng

### 🤖 Bot Core
- **Trò chuyện tự nhiên**: Hiểu teencode, tiếng lóng, lỗi chính tả
- **Trí nhớ thông minh**:
  - **Ngắn hạn**: Ghi nhớ cuộc trò chuyện gần đây
  - **Dài hạn**: Nhớ về người dùng (tên, sở thích, chuyện quan trọng)
- **Xử lý đa phương tiện**:
  - **Text**: Trả lời tin nhắn văn bản
  - **Ảnh**: Mô tả, phân tích ảnh (với Vision AI)
  - **Sticker**: Phản hồi tự nhiên với nhãn gián
- **Chống tấn công**:
  - **Prompt Injection/Jailbreak**: Lọc các cố gắng thao túng hệ thống
  - **OCR Security**: Kiểm tra text trong ảnh có chứa lệnh độc hại
  - **Rate Limiting**: Chống spam
- **Đồng bộ dữ liệu**: Sử dụng SQLite cho hiệu suất và an toàn

### 🌐 Admin Web
- **Dashboard**: Thống kê real-time (user, tin nhắn, token)
- **Quản lý user**:
  - Xem top user theo token
  - Xem trí nhớ của user
  - Reset context/quên hết user
- **Chặn user**:
  - Ban/unban user
  - Xem lịch sử ban
- **Bảo trì**: Bật/tắt chế độ bảo trì
- **Tìm kiếm**: Tìm user theo chat_id
- **Hoạt động gần đây**: Xem lịch sử hoạt động

### 🔒 Bảo mật
- **Chống Prompt Injection**: Hệ thống lọc nâng cao
- **Chống Jailbreak**: Không cho phép thay đổi system prompt
- **Bảo mật dữ liệu**: Không tiết lộ thông tin nhạy cảm
- **Xác thực Admin**: Đăng nhập bằng mật khẩu

## 🚀 Cài đặt

### Yêu cầu
- Python 3.10+
- pip
- Git

### Cài đặt

1. **Clone repository**:
```bash
git clone https://github.com/acherlab-ai/effective-enigma.git
cd effective-enigma
```

2. **Tạo môi trường ảo (recommended)**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

3. **Cài đặt dependencies**:
```bash
pip install -r requirements.txt
```

4. **Cài đặt OCR (nếu sử dụng EasyOCR)**:
```bash
# EasyOCR yêu cầu PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install easyocr
```

5. **Cấu hình**:
```bash
# Copy file mẫu
cp .env.example .env

# Chỉnh sửa .env với thông tin của bạn
nano .env  # hoặc sử dụng bất kỳ editor nào
```

6. **Chạy bot**:
```bash
# Terminal 1: Chạy bot
python bot/app.py

# Terminal 2: Chạy admin web
python admin/app.py
```

7. **Truy cập admin**:
- Mở trình duyệt: `http://localhost:8080`
- Đăng nhập với mật khẩu trong `.env` (ADMIN_PASSWORD)

## 📁 Cấu trúc project

```
effective-enigma/
├── bot/
│   ├── __init__.py
│   ├── app.py              # Main bot application
│   ├── config.py           # Configuration
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── ai.py           # AI API calls
│   │   ├── text.py         # Text message handler
│   │   ├── image.py        # Image message handler
│   │   └── sticker.py      # Sticker message handler
│   └── utils/
│       ├── __init__.py
│       ├── security.py     # Anti prompt injection
│       ├── memory.py       # Memory management
│       ├── stats.py        # Statistics tracking
│       └── ocr.py          # OCR for images
│
├── admin/
│   ├── __init__.py
│   ├── app.py              # Flask admin application
│   ├── database.py         # Database access for admin
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css   # Main stylesheet
│   │   └── js/             # JavaScript files
│   └── templates/
│       └── base.html       # Base template
│
├── data/                  # Database and data files
│
├── .env.example           # Example configuration
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## 🔧 Cấu hình

### Biến môi trường quan trọng

| Biến | Mô tả | Mặc định |
|------|-------|---------|
| `ZALO_BOT_TOKEN` | Token bot Zalo | *Bắt buộc* |
| `MISTRAL_API_KEY` | API key Mistral AI | *Bắt buộc* |
| `ADMIN_PASSWORD` | Mật khẩu admin | `Hn0961718254@` |
| `ADMIN_PORT` | Cổng admin web | `8080` |
| `OCR_PROVIDER` | Nhà cung cấp OCR | `easyocr` |
| `AI_MODEL` | Model AI | `mistral-small-latest` |

### Lựa chọn OCR

| Provider | Ưu điểm | Nhược điểm | Cài đặt |
|----------|--------|------------|---------|
| `easyocr` | Offline, dễ sử dụng | Cần PyTorch | `pip install easyocr torch` |
| `tesseract` | Offline, nhẹ | Cần cài đặt hệ thống | `pip install pytesseract` + [Tesseract](https://github.com/tesseract-ocr/tesseract) |
| `google_vision` | Chính xác nhất | Online, có giới hạn | `GOOGLE_VISION_API_KEY` |

## 📊 Lệnh bot

| Lệnh | Mô tả |
|------|-------|
| `/start` | Bắt đầu trò chuyện |
| `/reset` | Xóa context gần đây (vẫn nhớ facts) |
| `/quenhet` | Quên hết (xóa tất cả trí nhớ) |
| `/stats` | Xem thống kê cá nhân |

## 🛡️ Bảo mật

### Chống Prompt Injection
Bot có hệ thống lọc nâng cao:
1. **Regex filtering**: Lọc các mẫu tấn công đã biết
2. **OCR Security**: Kiểm tra text trong ảnh
3. **System prompt**: Kháng các cố gắng thay đổi prompt
4. **Ban tự động**: Auto ban user cố tấn công

### Danh sách chặn
- User bị ban vĩnh viễn nếu cố:
  - Prompt injection
  - Jailbreak
  - Yêu cầu tiết lộ system prompt
- Admin có thể mở khóa qua web

## 📈 Admin Web

### Chức năng
- **Dashboard**: Xem thống kê tổng quan
- **Top Users**: Xếp hạng user theo token
- **Banned Users**: Quản lý user bị chặn
- **Search**: Tìm user theo chat_id
- **Memory Viewer**: Xem/chỉnh sửa trí nhớ user
- **Maintenance**: Bật/tắt chế độ bảo trì
- **Recent Activity**: Xem hoạt động gần đây

### Real-time Updates
Admin web sử dụng **Socket.IO** để cập nhật thống kê ngay lập tức mà không cần tải lại trang.

## 🔄 Đồng bộ dữ liệu

### SQLite Database
Tất cả dữ liệu được lưu trong SQLite:
- `short_term_memory`: Context trò chuyện
- `long_term_memory`: Facts về user
- `daily_stats`: Thống kê hàng ngày
- `user_stats`: Thống kê theo user
- `message_log`: Log tin nhắn
- `banned_users`: Danh sách chặn

### Backward Compatibility
Bot tự động migrate dữ liệu từ JSON cũ sang SQLite khi khởi chạy lần đầu.

## 🐛 Gỡ lỗi

### Lỗi thường gặp

1. **ModuleNotFoundError: easyocr**
   ```bash
   pip install easyocr torch
   ```

2. **Lỗi kết nối Mistral API**
   - Kiểm tra `MISTRAL_API_KEY`
   - Kiểm tra mạng internet

3. **Lỗi kết nối Zalo**
   - Kiểm tra `ZALO_BOT_TOKEN`
   - Kiểm tra bot có hoạt động trên Zalo Developer

4. **Admin không truy cập được**
   - Kiểm tra `ADMIN_PASSWORD`
   - Kiểm tra cổng `ADMIN_PORT`

### Log
- Bot log: `data/bot.log`
- Flask log: Terminal output

## 📝 Contributing

1. Fork repository
2. Tạo branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m 'Add some feature'`
4. Push: `git push origin feature/your-feature`
5. Tạo Pull Request

## 📄 License

MIT License - Xem file [LICENSE](LICENSE) để biết chi tiết.

## 🙏 Đóng góp

Cảm ơn bạn đã sử dụng Bringh Bot! Nếu có bất kỳ vấn đề nào, vui lòng tạo issue trên GitHub.

---

**Made with ❤️ by acherlab-ai**
