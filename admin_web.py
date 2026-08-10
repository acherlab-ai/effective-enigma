"""
============================================================
BRINGH ADMIN — Trang quản lý bot (1 file duy nhất)
============================================================

Chạy:
    pip install flask python-dotenv --break-system-packages
    python admin_web.py

Mặc định chạy ở cổng 8080, đọc/ghi cùng thư mục dữ liệu với bot
(bringh_bot.py) qua biến môi trường BRINGH_DATA_DIR (mặc định
là thư mục "data" cạnh file). Vì vậy 2 tiến trình (bot + web) cần
trỏ chung một BRINGH_DATA_DIR mới thấy chung dữ liệu.

Đăng nhập admin: đặt biến môi trường ADMIN_PASSWORD, nếu không có
sẽ dùng mật khẩu mặc định bên dưới.
"""

import os
import json
import secrets
from datetime import date, timedelta
from pathlib import Path
from functools import wraps

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    render_template_string,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ============================================================
# CẤU HÌNH
# ============================================================

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD",
    "Hn0961718254@"
)

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

DATA_DIR = Path(
    os.getenv("BRINGH_DATA_DIR", "data")
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATS_FILE = DATA_DIR / "stats_store.json"
ADMIN_STATE_FILE = DATA_DIR / "admin_state.json"
BANNED_FILE = DATA_DIR / "banned_users.json"

DEFAULT_MAINTENANCE_MESSAGE = (
    "Bringh đang bảo trì xíu nha 🛠️ "
    "Lát quay lại nói chuyện tiếp nhé!"
)

DAYS_FOR_CHART = 14


# ============================================================
# ĐỌC / GHI FILE
# ============================================================

def _load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def load_stats():
    return _load_json(STATS_FILE, {
        "total_messages": 0,
        "total_tokens": 0,
        "messages_by_day": {},
        "tokens_by_day": {},
        "users": {}
    })


def load_admin_state():
    return _load_json(ADMIN_STATE_FILE, {
        "maintenance": False,
        "maintenance_message": DEFAULT_MAINTENANCE_MESSAGE
    })


def save_admin_state(state):
    _save_json(ADMIN_STATE_FILE, state)


def load_banned_users():
    return _load_json(BANNED_FILE, {})


def save_banned_users(banned):
    _save_json(BANNED_FILE, banned)


def last_n_days(n):
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def build_dashboard_payload():
    stats = load_stats()
    admin_state = load_admin_state()
    banned = load_banned_users()

    days = last_n_days(DAYS_FOR_CHART)
    messages_by_day = stats.get("messages_by_day", {})
    tokens_by_day = stats.get("tokens_by_day", {})

    chart_messages = [messages_by_day.get(d, 0) for d in days]
    chart_tokens = [tokens_by_day.get(d, 0) for d in days]
    chart_labels = [d[5:] for d in days]

    users = stats.get("users", {})
    top_users = sorted(
        users.items(),
        key=lambda kv: kv[1].get("tokens", 0),
        reverse=True
    )[:30]

    top_users_list = [
        {
            "chat_id": chat_id,
            "messages": info.get("messages", 0),
            "tokens": info.get("tokens", 0),
            "first_seen": info.get("first_seen", ""),
            "last_seen": info.get("last_seen", "")
        }
        for chat_id, info in top_users
    ]

    today_str = date.today().isoformat()

    return {
        "total_users": len(users),
        "total_messages": stats.get("total_messages", 0),
        "total_tokens": stats.get("total_tokens", 0),
        "messages_today": messages_by_day.get(today_str, 0),
        "tokens_today": tokens_by_day.get(today_str, 0),
        "chart_labels": chart_labels,
        "chart_messages": chart_messages,
        "chart_tokens": chart_tokens,
        "top_users": top_users_list,
        "maintenance": admin_state.get("maintenance", False),
        "maintenance_message": admin_state.get(
            "maintenance_message",
            DEFAULT_MAINTENANCE_MESSAGE
        ),
        "banned_users": banned,
    }


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1">
<title>Bringh Admin — Đăng nhập</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: radial-gradient(circle at 20% 20%, #1c1f2e 0%, #0a0b12 60%);
    padding: 20px;
  }
  .card {
    width: 100%;
    max-width: 380px;
    background: linear-gradient(160deg, #171a26 0%, #12141d 100%);
    border: 1px solid #262a3d;
    border-radius: 20px;
    padding: 36px 28px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .logo {
    font-size: 42px;
    text-align: center;
    margin-bottom: 6px;
  }
  h1 {
    color: #f1f2f6;
    font-size: 20px;
    text-align: center;
    margin: 0 0 4px;
  }
  p.sub {
    color: #7d8199;
    text-align: center;
    font-size: 13px;
    margin: 0 0 28px;
  }
  label {
    display: block;
    color: #9297b0;
    font-size: 13px;
    margin-bottom: 8px;
  }
  input[type=password] {
    width: 100%;
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid #2b2f45;
    background: #0e0f18;
    color: #f1f2f6;
    font-size: 15px;
    margin-bottom: 20px;
    outline: none;
    transition: border-color .15s;
  }
  input[type=password]:focus {
    border-color: #6c5ce7;
  }
  button {
    width: 100%;
    padding: 14px;
    border: none;
    border-radius: 12px;
    background: linear-gradient(135deg, #6c5ce7, #a29bfe);
    color: #fff;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
  }
  button:active { transform: scale(0.98); }
  .error {
    background: #3a1520;
    border: 1px solid #5a1f2e;
    color: #ff8fa3;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 13px;
    margin-bottom: 18px;
    text-align: center;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="logo">🐾</div>
    <h1>Bringh Admin</h1>
    <p class="sub">Đăng nhập để quản lý bot</p>
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
      <label for="password">Mật khẩu quản trị</label>
      <input type="password" id="password" name="password" autofocus required>
      <button type="submit">Đăng nhập</button>
    </form>
  </div>
</body>
</html>
"""


# ============================================================
# DASHBOARD (có thêm phần quản lý banned)
# ============================================================

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1">
<title>Bringh Admin — Bảng điều khiển</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0b12;
    color: #f1f2f6;
    padding-bottom: 40px;
  }
  header {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    background: rgba(10,11,18,0.9);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid #1c1f2e;
  }
  header .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 17px;
  }
  header .brand span.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #2ecc71;
    box-shadow: 0 0 8px #2ecc71;
  }
  header .brand span.dot.off {
    background: #e74c3c;
    box-shadow: 0 0 8px #e74c3c;
  }
  header a.logout {
    color: #7d8199;
    text-decoration: none;
    font-size: 13px;
    border: 1px solid #262a3d;
    padding: 8px 14px;
    border-radius: 10px;
  }
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 20px 16px;
  }
  .grid-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }
  @media (max-width: 640px) {
    .grid-cards { grid-template-columns: repeat(2, 1fr); }
  }
  .card {
    background: linear-gradient(160deg, #171a26 0%, #12141d 100%);
    border: 1px solid #21243a;
    border-radius: 16px;
    padding: 18px;
  }
  .card .label {
    color: #7d8199;
    font-size: 12.5px;
    margin-bottom: 8px;
  }
  .card .value {
    font-size: 24px;
    font-weight: 700;
  }
  .card .sub-value {
    color: #6c5ce7;
    font-size: 12px;
    margin-top: 4px;
  }
  .panel {
    background: linear-gradient(160deg, #171a26 0%, #12141d 100%);
    border: 1px solid #21243a;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 20px;
  }
  .panel h2 {
    font-size: 15px;
    margin: 0 0 14px;
    color: #d3d5e0;
  }
  .chart-wrap {
    position: relative;
    height: 220px;
  }
  .maintenance-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .maintenance-status {
    font-size: 14px;
    color: #9297b0;
  }
  .maintenance-status b {
    color: #f1f2f6;
  }
  .switch {
    position: relative;
    display: inline-block;
    width: 54px;
    height: 30px;
    flex-shrink: 0;
  }
  .switch input { display: none; }
  .slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: #2b2f45;
    border-radius: 30px;
    transition: .2s;
  }
  .slider:before {
    content: "";
    position: absolute;
    height: 24px;
    width: 24px;
    left: 3px;
    top: 3px;
    background: #f1f2f6;
    border-radius: 50%;
    transition: .2s;
  }
  .switch input:checked + .slider {
    background: linear-gradient(135deg, #e74c3c, #ff6b6b);
  }
  .switch input:checked + .slider:before {
    transform: translateX(24px);
  }
  textarea {
    width: 100%;
    margin-top: 14px;
    background: #0e0f18;
    border: 1px solid #2b2f45;
    border-radius: 10px;
    color: #f1f2f6;
    padding: 10px 12px;
    font-size: 13.5px;
    resize: vertical;
    min-height: 60px;
    font-family: inherit;
  }
  .save-msg-btn {
    margin-top: 10px;
    background: #262a3d;
    border: none;
    color: #d3d5e0;
    padding: 9px 16px;
    border-radius: 10px;
    font-size: 13px;
    cursor: pointer;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th {
    text-align: left;
    color: #7d8199;
    font-weight: 500;
    padding: 8px 6px;
    border-bottom: 1px solid #21243a;
    white-space: nowrap;
  }
  td {
    padding: 9px 6px;
    border-bottom: 1px solid #1a1c29;
    color: #d3d5e0;
    white-space: nowrap;
  }
  .table-scroll {
    overflow-x: auto;
  }
  .empty {
    color: #565a70;
    font-size: 13px;
    text-align: center;
    padding: 20px 0;
  }
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #1c1f2e;
    border: 1px solid #2b2f45;
    color: #f1f2f6;
    padding: 12px 20px;
    border-radius: 12px;
    font-size: 13.5px;
    opacity: 0;
    transition: .25s;
    pointer-events: none;
    z-index: 50;
  }
  .toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  .unban-btn {
    background: #2b2f45;
    border: none;
    color: #f1f2f6;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
  }
  .unban-btn:hover {
    background: #3a3f5a;
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <span class="dot {{ 'off' if maintenance else '' }}"></span>
    🐾 Bringh Admin
  </div>
  <a class="logout" href="{{ url_for('logout') }}">Đăng xuất</a>
</header>

<main>

  <div class="grid-cards">
    <div class="card">
      <div class="label">👥 Tổng user</div>
      <div class="value" id="stat-users">{{ data.total_users }}</div>
    </div>
    <div class="card">
      <div class="label">💬 Tổng tin nhắn</div>
      <div class="value" id="stat-messages">{{ data.total_messages }}</div>
      <div class="sub-value" id="stat-messages-today">Hôm nay: {{ data.messages_today }}</div>
    </div>
    <div class="card">
      <div class="label">⚡ Tổng token</div>
      <div class="value" id="stat-tokens">{{ data.total_tokens }}</div>
      <div class="sub-value" id="stat-tokens-today">Hôm nay: {{ data.tokens_today }}</div>
    </div>
  </div>

  <div class="panel">
    <h2>🛠️ Chế độ bảo trì</h2>
    <div class="maintenance-box">
      <div class="maintenance-status">
        Trạng thái: <b id="maintenance-label">{{ 'ĐANG BẢO TRÌ' if maintenance else 'Hoạt động bình thường' }}</b>
      </div>
      <label class="switch">
        <input type="checkbox" id="maintenance-toggle" {{ 'checked' if maintenance else '' }}>
        <span class="slider"></span>
      </label>
    </div>
    <textarea id="maintenance-message">{{ data.maintenance_message }}</textarea>
    <button class="save-msg-btn" id="save-message-btn">Lưu nội dung thông báo</button>
  </div>

  <div class="panel">
    <h2>📈 Tin nhắn theo ngày (14 ngày gần nhất)</h2>
    <div class="chart-wrap">
      <canvas id="chartMessages"></canvas>
    </div>
  </div>

  <div class="panel">
    <h2>⚡ Token theo ngày (14 ngày gần nhất)</h2>
    <div class="chart-wrap">
      <canvas id="chartTokens"></canvas>
    </div>
  </div>

  <div class="panel">
    <h2>👥 Top user theo token đã dùng</h2>
    {% if data.top_users %}
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Chat ID</th>
            <th>Tin nhắn</th>
            <th>Token</th>
            <th>Lần đầu</th>
            <th>Gần nhất</th>
          </tr>
        </thead>
        <tbody id="users-table-body">
          {% for u in data.top_users %}
          <tr>
            <td>{{ u.chat_id }}</td>
            <td>{{ u.messages }}</td>
            <td>{{ u.tokens }}</td>
            <td>{{ u.first_seen }}</td>
            <td>{{ u.last_seen }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <div class="empty">Chưa có user nào.</div>
    {% endif %}
  </div>

  <!-- PHẦN QUẢN LÝ BANNED -->
  <div class="panel">
    <h2>🚫 User bị ban</h2>
    <div id="banned-list">
      {% if data.banned_users %}
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Chat ID</th>
                <th>Lý do</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody id="banned-table-body">
              {% for chat_id, reason in data.banned_users.items() %}
              <tr data-chat="{{ chat_id }}">
                <td>{{ chat_id }}</td>
                <td>{{ reason }}</td>
                <td><button class="unban-btn" data-chat="{{ chat_id }}">Mở khóa</button></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      {% else %}
        <div class="empty">Không có user nào bị ban.</div>
      {% endif %}
    </div>
  </div>

</main>

<div class="toast" id="toast"></div>

<script>
const chartLabels = {{ data.chart_labels | tojson }};
const chartMessages = {{ data.chart_messages | tojson }};
const chartTokens = {{ data.chart_tokens | tojson }};

const commonOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: '#1a1c29' }, ticks: { color: '#7d8199', font: { size: 11 } } },
    y: { grid: { color: '#1a1c29' }, ticks: { color: '#7d8199', font: { size: 11 } }, beginAtZero: true }
  }
};

new Chart(document.getElementById('chartMessages'), {
  type: 'bar',
  data: {
    labels: chartLabels,
    datasets: [{
      data: chartMessages,
      backgroundColor: '#6c5ce7',
      borderRadius: 6,
      maxBarThickness: 28
    }]
  },
  options: commonOptions
});

new Chart(document.getElementById('chartTokens'), {
  type: 'line',
  data: {
    labels: chartLabels,
    datasets: [{
      data: chartTokens,
      borderColor: '#00cec9',
      backgroundColor: 'rgba(0,206,201,0.15)',
      fill: true,
      tension: 0.35,
      pointRadius: 3,
      pointBackgroundColor: '#00cec9'
    }]
  },
  options: commonOptions
});

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}

// ---- MAINTENANCE ----
document.getElementById('maintenance-toggle').addEventListener('change', async (e) => {
  const on = e.target.checked;
  try {
    const res = await fetch('/api/maintenance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ maintenance: on })
    });
    const data = await res.json();
    document.getElementById('maintenance-label').textContent =
      data.maintenance ? 'ĐANG BẢO TRÌ' : 'Hoạt động bình thường';
    showToast(data.maintenance ? '🛠️ Đã bật bảo trì' : '✅ Đã tắt bảo trì, bot hoạt động lại');
  } catch (err) {
    showToast('❌ Lỗi, thử lại nha');
    e.target.checked = !on;
  }
});

document.getElementById('save-message-btn').addEventListener('click', async () => {
  const msg = document.getElementById('maintenance-message').value;
  try {
    const res = await fetch('/api/maintenance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ maintenance_message: msg })
    });
    await res.json();
    showToast('💾 Đã lưu nội dung thông báo bảo trì');
  } catch (err) {
    showToast('❌ Lỗi, thử lại nha');
  }
});

// ---- BANNED USERS ----
async function refreshBannedList() {
  try {
    const res = await fetch('/api/banned');
    const banned = await res.json();
    const container = document.getElementById('banned-list');
    const tbody = document.getElementById('banned-table-body');
    if (!tbody) return; // nếu chưa có bảng

    const currentChats = new Set();
    tbody.querySelectorAll('tr').forEach(row => {
      currentChats.add(row.dataset.chat);
    });

    // Xóa những hàng không còn trong danh sách banned mới
    for (const chat of currentChats) {
      if (!banned[chat]) {
        const row = tbody.querySelector(`tr[data-chat="${chat}"]`);
        if (row) row.remove();
      }
    }

    // Thêm các user mới
    for (const [chat, reason] of Object.entries(banned)) {
      if (!currentChats.has(chat)) {
        const tr = document.createElement('tr');
        tr.dataset.chat = chat;
        tr.innerHTML = `
          <td>${chat}</td>
          <td>${reason}</td>
          <td><button class="unban-btn" data-chat="${chat}">Mở khóa</button></td>
        `;
        tbody.appendChild(tr);
      }
    }

    // Nếu không có user nào, hiển thị thông báo
    if (Object.keys(banned).length === 0) {
      container.innerHTML = '<div class="empty">Không có user nào bị ban.</div>';
    } else {
      // Đảm bảo có bảng
      if (!document.querySelector('#banned-list table')) {
        container.innerHTML = `
          <div class="table-scroll">
            <table>
              <thead><tr><th>Chat ID</th><th>Lý do</th><th>Hành động</th></tr></thead>
              <tbody id="banned-table-body"></tbody>
            </table>
          </div>
        `;
        // Gọi lại để populate
        await refreshBannedList();
      }
    }
  } catch (err) {
    // im lặng
  }
}

// Xử lý sự kiện click trên nút unban (delegation)
document.addEventListener('click', async (e) => {
  if (e.target.classList.contains('unban-btn')) {
    const chat_id = e.target.dataset.chat;
    if (!chat_id) return;
    try {
      const res = await fetch('/api/unban', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`✅ Đã mở khóa user ${chat_id}`);
        await refreshBannedList();
      } else {
        showToast(`❌ Lỗi: ${data.error || 'không xác định'}`);
      }
    } catch (err) {
      showToast('❌ Lỗi kết nối, thử lại nha');
    }
  }
});

// Tự động refresh banned list mỗi 15 giây
setInterval(refreshBannedList, 15000);

// ---- STATS REFRESH ----
async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('stat-users').textContent = data.total_users;
    document.getElementById('stat-messages').textContent = data.total_messages;
    document.getElementById('stat-messages-today').textContent = 'Hôm nay: ' + data.messages_today;
    document.getElementById('stat-tokens').textContent = data.total_tokens;
    document.getElementById('stat-tokens-today').textContent = 'Hôm nay: ' + data.tokens_today;
  } catch (err) {
    // im lặng
  }
}
setInterval(refreshStats, 10000);

</script>
</body>
</html>
"""


# ============================================================
# ROUTES
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "Sai mật khẩu rồi, thử lại nha."
    return render_template_string(LOGIN_PAGE, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    data = build_dashboard_payload()
    return render_template_string(
        DASHBOARD_PAGE,
        data=data,
        maintenance=data["maintenance"]
    )


@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(build_dashboard_payload())


@app.route("/api/maintenance", methods=["GET", "POST"])
@login_required
def api_maintenance():
    state = load_admin_state()
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        if "maintenance" in payload:
            state["maintenance"] = bool(payload["maintenance"])
        if "maintenance_message" in payload:
            new_msg = str(payload["maintenance_message"]).strip()
            state["maintenance_message"] = new_msg or DEFAULT_MAINTENANCE_MESSAGE
        save_admin_state(state)
    return jsonify(state)


@app.route("/api/banned")
@login_required
def api_banned():
    banned = _load_json(BANNED_FILE, {})
    return jsonify(banned)


@app.route("/api/unban", methods=["POST"])
@login_required
def api_unban():
    payload = request.get_json(silent=True) or {}
    chat_id = payload.get("chat_id")
    if not chat_id:
        return jsonify({"success": False, "error": "Thiếu chat_id"})

    banned = _load_json(BANNED_FILE, {})
    if chat_id in banned:
        del banned[chat_id]
        _save_json(BANNED_FILE, banned)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "User không bị ban"})


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("ADMIN_PORT", "8080"))
    print()
    print("====================================")
    print("🐾 BRINGH ADMIN ĐANG CHẠY")
    print("====================================")
    print(f"URL   : http://0.0.0.0:{port}")
    print(f"DATA  : {DATA_DIR.resolve()}")
    print("====================================")
    print()

    app.run(host="0.0.0.0", port=port, debug=False)
