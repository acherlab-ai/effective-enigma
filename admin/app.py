"""
Bringh Admin Web Application
=============================

Flask-based admin interface with:
- Real-time statistics via Socket.IO
- User management
- Ban/unban functionality
- System settings
- Responsive design with HTMX
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
from flask_socketio import SocketIO, emit

from bot.config import (
    ADMIN_PASSWORD,
    ADMIN_PORT,
    SECRET_KEY,
    DATA_DIR,
    DAYS_FOR_CHART,
)
from admin.database import (
    get_total_stats,
    get_daily_stats,
    get_top_users,
    get_user_stats,
    search_users,
    get_banned_users,
    ban_user,
    unban_user,
    get_admin_state,
    set_admin_state,
    get_long_term_memory,
    update_long_term_memory,
    get_short_term_memory,
    reset_short_term_memory,
    forget_user,
    get_recent_activity,
    get_system_info,
)


# ============================================================
# FLASK APP SETUP
# ============================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Socket.IO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# ============================================================
# AUTHENTICATION
# ============================================================

def login_required(view_func):
    """Decorator to require login."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def last_n_days(n: int) -> List[str]:
    """Get list of last N days in ISO format."""
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def build_dashboard_payload() -> Dict[str, Any]:
    """Build payload for dashboard."""
    stats = get_total_stats()
    daily_stats = get_daily_stats(DAYS_FOR_CHART)
    
    # Build charts data
    days = last_n_days(DAYS_FOR_CHART)
    
    # Create dicts for quick lookup
    daily_dict = {s["date"]: s for s in daily_stats}
    
    chart_messages = [daily_dict.get(d, {"messages": 0})["messages"] for d in days]
    chart_tokens = [daily_dict.get(d, {"tokens": 0})["tokens"] for d in days]
    chart_labels = [d[5:] for d in days]  # "MM-DD" format
    
    # Get top users
    top_users = get_top_users(30)
    
    # Get banned users
    banned_list = get_banned_users()
    
    # Get admin state
    admin_state = get_admin_state()
    
    # Get today's date string
    today_str = date.today().isoformat()
    
    return {
        "total_users": stats["total_users"],
        "total_messages": stats["total_messages"],
        "total_tokens": stats["total_tokens"],
        "messages_today": stats["messages_today"],
        "tokens_today": stats["tokens_today"],
        "active_users_today": stats["active_users_today"],
        "chart_labels": chart_labels,
        "chart_messages": chart_messages,
        "chart_tokens": chart_tokens,
        "top_users": top_users,
        "banned_users": banned_list,
        "banned_count": len(banned_list),
        "maintenance": admin_state.get("maintenance", False),
        "maintenance_message": admin_state.get(
            "maintenance_message",
            "Bringh đang bảo trì xíu nha 🛠️ Lát quay lại nói chuyện tiếp nhé!"
        ),
        "system_info": get_system_info(),
    }


# ============================================================
# HTML TEMPLATES
# ============================================================

# Login page
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


# Dashboard page (will be loaded via HTMX)
DASHBOARD_PAGE = """
<!DOCTYPE html>
<html lang="vi" hx-ext="websocket">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1">
<title>Bringh Admin — Bảng điều khiển</title>
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://unpkg.com/htmx.org/dist/ext/websocket.js"></script>
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
  header a.logout:hover {
    background: #1a1c29;
  }
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px 16px;
  }
  .grid-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
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
    display: flex;
    align-items: center;
    gap: 8px;
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
  .save-msg-btn:hover {
    background: #2e3449;
  }
  .hint {
    color: #7d8199;
    font-size: 12.5px;
    margin: -6px 0 14px;
  }
  .ban-btn, .unban-btn, .view-btn, .edit-btn, .reset-btn, .forget-btn {
    border: none;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 12.5px;
    cursor: pointer;
    white-space: nowrap;
    margin: 0 2px;
  }
  .ban-btn {
    background: #3a1520;
    color: #ff8fa3;
  }
  .ban-btn:hover {
    background: #4a1a2a;
  }
  .unban-btn {
    background: #12321f;
    color: #4ee08a;
  }
  .unban-btn:hover {
    background: #1a4529;
  }
  .view-btn {
    background: #1a2332;
    color: #6c5ce7;
  }
  .view-btn:hover {
    background: #202b40;
  }
  .edit-btn {
    background: #1a2332;
    color: #f6ad55;
  }
  .edit-btn:hover {
    background: #202b40;
  }
  .reset-btn {
    background: #1a2332;
    color: #fc8181;
  }
  .reset-btn:hover {
    background: #202b40;
  }
  .forget-btn {
    background: #1a2332;
    color: #ff6b6b;
  }
  .forget-btn:hover {
    background: #202b40;
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
    background: #12141d;
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
  .modal {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    opacity: 0;
    visibility: hidden;
    transition: .2s;
  }
  .modal.show {
    opacity: 1;
    visibility: visible;
  }
  .modal-content {
    background: #171a26;
    border: 1px solid #262a3d;
    border-radius: 16px;
    padding: 24px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .modal-header h3 {
    margin: 0;
    font-size: 16px;
  }
  .modal-close {
    background: none;
    border: none;
    color: #7d8199;
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
  }
  .modal-close:hover {
    color: #f1f2f6;
  }
  .form-group {
    margin-bottom: 16px;
  }
  .form-group label {
    display: block;
    color: #9297b0;
    font-size: 13px;
    margin-bottom: 6px;
  }
  .form-group input,
  .form-group textarea {
    width: 100%;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid #2b2f45;
    background: #0e0f18;
    color: #f1f2f6;
    font-size: 13.5px;
    font-family: inherit;
  }
  .form-group textarea {
    resize: vertical;
    min-height: 100px;
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
  }
  .btn {
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    border: none;
  }
  .btn-primary {
    background: linear-gradient(135deg, #6c5ce7, #a29bfe);
    color: #fff;
  }
  .btn-secondary {
    background: #262a3d;
    color: #d3d5e0;
  }
  .btn-secondary:hover {
    background: #2e3449;
  }
  .memory-content {
    background: #0e0f18;
    border: 1px solid #2b2f45;
    border-radius: 10px;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 300px;
    overflow-y: auto;
    color: #d3d5e0;
  }
  .tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
    border-bottom: 1px solid #21243a;
    padding-bottom: 8px;
  }
  .tab {
    padding: 8px 16px;
    border-radius: 8px 8px 0 0;
    background: none;
    border: none;
    color: #7d8199;
    font-size: 13px;
    cursor: pointer;
  }
  .tab.active {
    background: #262a3d;
    color: #f1f2f6;
  }
  .tab-content {
    display: none;
  }
  .tab-content.active {
    display: block;
  }
  .search-box {
    margin-bottom: 16px;
  }
  .search-box input {
    width: 100%;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid #2b2f45;
    background: #0e0f18;
    color: #f1f2f6;
    font-size: 13.5px;
  }
  @media (max-width: 768px) {
    .grid-cards {
      grid-template-columns: repeat(2, 1fr);
    }
    main {
      padding: 16px 12px;
    }
  }
</style>
</head>
<body hx-ws="connect:/ws">

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
    <div class="card">
      <div class="label">🔒 User bị chặn</div>
      <div class="value" id="stat-banned">{{ data.banned_count }}</div>
    </div>
  </div>

  <div class="panel">
    <h2>🛠️ Chế độ bảo trì</h2>
    <div class="maintenance-box">
      <div class="maintenance-status">
        Trạng thái: <b id="maintenance-label">{{ 'ĐANG BẢO TRÌ' if maintenance else 'Hoạt động bình thường' }}</b>
      </div>
      <label class="switch">
        <input type="checkbox" id="maintenance-toggle" {{ 'checked' if maintenance else '' }} hx-post="/api/maintenance" hx-trigger="change" hx-swap="none">
        <span class="slider"></span>
      </label>
    </div>
    <textarea id="maintenance-message" hx-post="/api/maintenance" hx-trigger="change, keyup changed delay:1000ms" hx-swap="none">{{ data.maintenance_message }}</textarea>
    <button class="save-msg-btn" onclick="saveMaintenanceMessage()">Lưu nội dung thông báo</button>
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
    <div class="tabs">
      <button class="tab active" onclick="switchTab('users')">👥 Top User</button>
      <button class="tab" onclick="switchTab('banned')">🚫 User bị chặn</button>
      <button class="tab" onclick="switchTab('search')">🔍 Tìm kiếm</button>
    </div>
    
    <div id="tab-users" class="tab-content active">
      <h2 style="margin-top: 0;">👥 Top user theo token đã dùng</h2>
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
              <th>Hành động</th>
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
              <td>
                <button class="view-btn" onclick="viewUserMemory('{{ u.chat_id }}')">Xem</button>
                <button class="ban-btn" onclick="banUser('{{ u.chat_id }}')">Chặn</button>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
        <div class="empty">Chưa có user nào.</div>
      {% endif %}
    </div>
    
    <div id="tab-banned" class="tab-content">
      <h2 style="margin-top: 0;">🚫 User bị chặn vĩnh viễn ({{ data.banned_count }})</h2>
      <p class="hint">
        User bị chặn do cố prompt injection / jailbreak, hoặc admin chặn tay.
      </p>
      {% if data.banned_users %}
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Chat ID</th>
              <th>Lý do</th>
              <th>Thời điểm chặn</th>
              <th>Hành động</th>
            </tr>
          </thead>
          <tbody id="banned-table-body">
            {% for b in data.banned_users %}
            <tr>
              <td>{{ b.chat_id }}</td>
              <td>{{ b.reason }}</td>
              <td>{{ b.banned_at }}</td>
              <td>
                <button class="unban-btn" onclick="unbanUser('{{ b.chat_id }}')">Mở khoá</button>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
        <div class="empty">Chưa có ai bị chặn.</div>
      {% endif %}
    </div>
    
    <div id="tab-search" class="tab-content">
      <h2 style="margin-top: 0;">🔍 Tìm kiếm user</h2>
      <div class="search-box">
        <input type="text" id="search-input" placeholder="Nhập chat_id hoặc từ khóa..." onkeyup="searchUsers()">
      </div>
      <div id="search-results"></div>
    </div>
  </div>

  <div class="panel">
    <h2>📊 Hoạt động gần đây</h2>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Chat ID</th>
            <th>Loại tin</th>
            <th>Token</th>
            <th>Thời gian</th>
          </tr>
        </thead>
        <tbody id="recent-activity">
          <!-- Will be populated via JavaScript -->
        </tbody>
      </table>
    </div>
  </div>

</main>

<!-- Memory View Modal -->
<div id="memory-modal" class="modal">
  <div class="modal-content">
    <div class="modal-header">
      <h3>Trí nhớ của <span id="memory-user-id"></span></h3>
      <button class="modal-close" onclick="closeModal('memory-modal')">×</button>
    </div>
    <div class="tabs">
      <button class="tab active" onclick="switchMemoryTab('facts')">🧠 Trí nhớ dài hạn</button>
      <button class="tab" onclick="switchMemoryTab('context')">💬 Context gần đây</button>
    </div>
    <div id="memory-facts" class="tab-content active">
      <div class="form-group">
        <label>Trí nhớ dài hạn (Facts):</label>
        <div class="memory-content" id="facts-content"></div>
      </div>
      <div class="form-group">
        <label>Cập nhật trí nhớ:</label>
        <textarea id="facts-edit" placeholder="Nhập trí nhớ mới..."></textarea>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" onclick="saveFacts()">Lưu</button>
        <button class="btn btn-secondary" onclick="closeModal('memory-modal')">Đóng</button>
      </div>
    </div>
    <div id="memory-context" class="tab-content">
      <div class="form-group">
        <label>Context gần đây:</label>
        <div class="memory-content" id="context-content"></div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" onclick="resetContext()">Reset Context</button>
        <button class="btn btn-secondary" onclick="forgetUser()">Quên hết</button>
        <button class="btn btn-secondary" onclick="closeModal('memory-modal')">Đóng</button>
      </div>
    </div>
  </div>
</div>

<!-- Confirm Modal -->
<div id="confirm-modal" class="modal">
  <div class="modal-content" style="max-width: 400px;">
    <div class="modal-header">
      <h3 id="confirm-title"></h3>
      <button class="modal-close" onclick="closeModal('confirm-modal')">×</button>
    </div>
    <div id="confirm-message"></div>
    <div class="form-actions">
      <button class="btn btn-primary" id="confirm-yes" onclick="confirmYes()">Đồng ý</button>
      <button class="btn btn-secondary" onclick="closeModal('confirm-modal')">Hủy</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// Global state
let currentAction = null;
let currentChatId = null;

// Chart initialization
const chartLabels = {{ data.chart_labels | tojson }};
const chartMessages = {{ data.chart_messages | tojson }};
const chartTokens = {{ data.chart_tokens | tojson }};

const commonOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { 
    legend: { display: false },
    tooltip: { 
      backgroundColor: '#1c1f2e',
      titleColor: '#f1f2f6',
      bodyColor: '#d3d5e0',
      borderColor: '#2b2f45',
      borderWidth: 1
    }
  },
  scales: {
    x: { 
      grid: { color: '#1a1c29' }, 
      ticks: { color: '#7d8199', font: { size: 11 } } 
    },
    y: { 
      grid: { color: '#1a1c29' }, 
      ticks: { color: '#7d8199', font: { size: 11 } }, 
      beginAtZero: true 
    }
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

// Toast notification
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}

// Maintenance toggle
function setupMaintenanceToggle() {
  const toggle = document.getElementById('maintenance-toggle');
  const label = document.getElementById('maintenance-label');
  const dot = document.querySelector('header .dot');
  
  toggle.addEventListener('change', async (e) => {
    const on = e.target.checked;
    try {
      const res = await fetch('/api/maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ maintenance: on })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      
      const data = await res.json();
      label.textContent = data.maintenance ? 'ĐANG BẢO TRÌ' : 'Hoạt động bình thường';
      dot.classList.toggle('off', data.maintenance);
      showToast(data.maintenance ? '🛠️ Đã bật bảo trì' : '✅ Đã tắt bảo trì, bot hoạt động lại');
    } catch (err) {
      showToast('❌ Lỗi, thử lại nha');
      e.target.checked = !on;
    }
  });
}

// Save maintenance message
function saveMaintenanceMessage() {
  const msg = document.getElementById('maintenance-message').value;
  fetch('/api/maintenance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ maintenance_message: msg })
  }).then(res => {
    if (res.ok) {
      showToast('💾 Đã lưu nội dung thông báo bảo trì');
    } else {
      showToast('❌ Lỗi, thử lại nha');
    }
  }).catch(() => showToast('❌ Lỗi, thử lại nha'));
}

// Ban user
function banUser(chatId) {
  currentChatId = chatId;
  currentAction = 'ban';
  document.getElementById('confirm-title').textContent = 'Xác nhận chặn user';
  document.getElementById('confirm-message').textContent = 
    'Bạn có chắc chắn muốn chặn vĩnh viễn user ' + chatId + '?';
  document.getElementById('confirm-yes').textContent = 'Chặn';
  document.getElementById('confirm-modal').classList.add('show');
}

// Unban user
function unbanUser(chatId) {
  currentChatId = chatId;
  currentAction = 'unban';
  document.getElementById('confirm-title').textContent = 'Xác nhận mở khoá';
  document.getElementById('confirm-message').textContent = 
    'Bạn có chắc chắn muốn mở khoá cho user ' + chatId + '?';
  document.getElementById('confirm-yes').textContent = 'Mở khoá';
  document.getElementById('confirm-modal').classList.add('show');
}

// Reset context
function resetContext() {
  currentAction = 'reset_context';
  document.getElementById('confirm-title').textContent = 'Xác nhận reset context';
  document.getElementById('confirm-message').textContent = 
    'Bạn có chắc chắn muốn reset context ngắn hạn cho user này? (vẫn giữ trí nhớ dài hạn)';
  document.getElementById('confirm-yes').textContent = 'Reset';
  document.getElementById('confirm-modal').classList.add('show');
}

// Forget user
function forgetUser() {
  currentAction = 'forget';
  document.getElementById('confirm-title').textContent = 'Xác nhận quên hết';
  document.getElementById('confirm-message').textContent = 
    'Bạn có chắc chắn muốn quên hoàn toàn user này? (xóa hết trí nhớ và thống kê)';
  document.getElementById('confirm-yes').textContent = 'Quên hết';
  document.getElementById('confirm-modal').classList.add('show');
}

// Confirm action
function confirmYes() {
  if (!currentChatId && currentAction !== 'reset_context' && currentAction !== 'forget') {
    closeModal('confirm-modal');
    return;
  }
  
  if (currentAction === 'ban') {
    fetch('/api/ban', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: currentChatId, reason: 'Admin chặn tay' })
    }).then(res => {
      if (res.ok) {
        showToast('🚫 Đã chặn ' + currentChatId);
        setTimeout(() => location.reload(), 600);
      } else {
        showToast('❌ Lỗi, thử lại nha');
      }
    }).catch(() => showToast('❌ Lỗi, thử lại nha'));
  } 
  else if (currentAction === 'unban') {
    fetch('/api/unban', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: currentChatId })
    }).then(res => {
      if (res.ok) {
        showToast('✅ Đã mở khoá ' + currentChatId);
        setTimeout(() => location.reload(), 600);
      } else {
        showToast('❌ Lỗi, thử lại nha');
      }
    }).catch(() => showToast('❌ Lỗi, thử lại nha'));
  }
  else if (currentAction === 'reset_context') {
    fetch('/api/reset_context', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: currentChatId })
    }).then(res => {
      if (res.ok) {
        showToast('🧹 Đã reset context');
        closeModal('memory-modal');
        setTimeout(() => location.reload(), 600);
      } else {
        showToast('❌ Lỗi, thử lại nha');
      }
    }).catch(() => showToast('❌ Lỗi, thử lại nha'));
  }
  else if (currentAction === 'forget') {
    fetch('/api/forget', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: currentChatId })
    }).then(res => {
      if (res.ok) {
        showToast('🧹 Đã quên hết user');
        closeModal('memory-modal');
        setTimeout(() => location.reload(), 600);
      } else {
        showToast('❌ Lỗi, thử lại nha');
      }
    }).catch(() => showToast('❌ Lỗi, thử lại nha'));
  }
  
  closeModal('confirm-modal');
  currentAction = null;
  currentChatId = null;
}

// Close modal
function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('show');
  currentAction = null;
  currentChatId = null;
}

// Switch tabs
function switchTab(tabName) {
  // Hide all tab contents
  document.querySelectorAll('.tab-content').forEach(el => {
    el.classList.remove('active');
  });
  
  // Show selected tab
  document.getElementById('tab-' + tabName).classList.add('active');
  
  // Update tab buttons
  document.querySelectorAll('.tab').forEach(el => {
    el.classList.remove('active');
  });
  event.target.classList.add('active');
}

// Switch memory tabs
function switchMemoryTab(tabName) {
  document.querySelectorAll('#memory-modal .tab-content').forEach(el => {
    el.classList.remove('active');
  });
  document.getElementById('memory-' + tabName).classList.add('active');
  
  document.querySelectorAll('#memory-modal .tab').forEach(el => {
    el.classList.remove('active');
  });
  event.target.classList.add('active');
}

// View user memory
async function viewUserMemory(chatId) {
  currentChatId = chatId;
  
  try {
    // Get facts
    const factsRes = await fetch('/api/memory?chat_id=' + chatId + '&type=facts');
    const factsData = await factsRes.json();
    document.getElementById('memory-user-id').textContent = chatId;
    document.getElementById('facts-content').textContent = factsData.facts || '(chưa có trí nhớ dài hạn)';
    document.getElementById('facts-edit').value = factsData.facts || '';
    
    // Get context
    const contextRes = await fetch('/api/memory?chat_id=' + chatId + '&type=context');
    const contextData = await contextRes.json();
    const contextStr = JSON.stringify(contextData.context, null, 2);
    document.getElementById('context-content').textContent = contextStr || '(chưa có context)';
    
    // Show modal
    document.getElementById('memory-modal').classList.add('show');
  } catch (err) {
    showToast('❌ Lỗi tải trí nhớ');
  }
}

// Save facts
async function saveFacts() {
  const facts = document.getElementById('facts-edit').value;
  
  try {
    const res = await fetch('/api/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        chat_id: currentChatId,
        type: 'facts',
        content: facts
      })
    });
    
    if (res.ok) {
      showToast('💾 Đã lưu trí nhớ dài hạn');
      closeModal('memory-modal');
    } else {
      showToast('❌ Lỗi, thử lại nha');
    }
  } catch (err) {
    showToast('❌ Lỗi, thử lại nha');
  }
}

// Search users
async function searchUsers() {
  const query = document.getElementById('search-input').value;
  if (!query || query.length < 2) {
    document.getElementById('search-results').innerHTML = '<div class="empty">Nhập ít nhất 2 ký tự</div>';
    return;
  }
  
  try {
    const res = await fetch('/api/search?q=' + encodeURIComponent(query));
    const data = await res.json();
    
    if (data.users.length === 0) {
      document.getElementById('search-results').innerHTML = '<div class="empty">Không tìm thấy user nào</div>';
      return;
    }
    
    let html = '<table><thead><tr><th>Chat ID</th><th>Tin nhắn</th><th>Token</th><th>Lần đầu</th><th>Gần nhất</th><th>Hành động</th></tr></thead><tbody>';
    
    data.users.forEach(u => {
      html += `
        <tr>
          <td>${u.chat_id}</td>
          <td>${u.messages}</td>
          <td>${u.tokens}</td>
          <td>${u.first_seen}</td>
          <td>${u.last_seen}</td>
          <td>
            <button class="view-btn" onclick="viewUserMemory('${u.chat_id}')">Xem</button>
            <button class="ban-btn" onclick="banUser('${u.chat_id}')">Chặn</button>
          </td>
        </tr>
      `;
    });
    
    html += '</tbody></table>';
    document.getElementById('search-results').innerHTML = html;
  } catch (err) {
    document.getElementById('search-results').innerHTML = '<div class="empty">Lỗi khi tìm kiếm</div>';
  }
}

// Real-time updates via Socket.IO
const socket = new WebSocket('ws://' + window.location.host + '/ws');

socket.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'stats_update') {
    // Update stats
    document.getElementById('stat-users').textContent = data.total_users;
    document.getElementById('stat-messages').textContent = data.total_messages;
    document.getElementById('stat-messages-today').textContent = 'Hôm nay: ' + data.messages_today;
    document.getElementById('stat-tokens').textContent = data.total_tokens;
    document.getElementById('stat-tokens-today').textContent = 'Hôm nay: ' + data.tokens_today;
    document.getElementById('stat-banned').textContent = data.banned_count;
  }
};

// Load recent activity
async function loadRecentActivity() {
  try {
    const res = await fetch('/api/activity');
    const data = await res.json();
    
    const tbody = document.getElementById('recent-activity');
    let html = '';
    
    data.activity.slice(0, 20).forEach(a => {
      html += `
        <tr>
          <td>${a.chat_id}</td>
          <td>${a.message_type}</td>
          <td>${a.tokens}</td>
          <td>${a.timestamp}</td>
        </tr>
      `;
    });
    
    tbody.innerHTML = html;
  } catch (err) {
    console.error('Error loading recent activity:', err);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  setupMaintenanceToggle();
  loadRecentActivity();
});

// Close modals on outside click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal')) {
    e.target.classList.remove('show');
  }
});
</script>

</body>
</html>
"""


# ============================================================
# ROUTES
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
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
    """Logout."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    """Main dashboard."""
    data = build_dashboard_payload()
    return render_template_string(
        DASHBOARD_PAGE,
        data=data,
        maintenance=data["maintenance"]
    )


# ============================================================
# API ROUTES
# ============================================================

@app.route("/api/stats")
@login_required
def api_stats():
    """Get statistics."""
    return jsonify(build_dashboard_payload())


@app.route("/api/maintenance", methods=["GET", "POST"])
@login_required
def api_maintenance():
    """Get or set maintenance mode."""
    state = get_admin_state()
    
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        
        if "maintenance" in payload:
            state["maintenance"] = bool(payload["maintenance"])
        
        if "maintenance_message" in payload:
            new_msg = str(payload["maintenance_message"]).strip()
            state["maintenance_message"] = new_msg or (
                "Bringh đang bảo trì xíu nha 🛠️ Lát quay lại nói chuyện tiếp nhé!"
            )
        
        set_admin_state(state)
    
    return jsonify(state)


@app.route("/api/ban", methods=["POST"])
@login_required
def api_ban():
    """Ban a user."""
    payload = request.get_json(silent=True) or {}
    
    chat_id = str(payload.get("chat_id", "")).strip()
    if not chat_id:
        return jsonify({"error": "Thiếu chat_id"}), 400
    
    reason = str(payload.get("reason") or "Admin chặn tay").strip()
    
    if ban_user(chat_id, reason):
        # Also update JSON file for bot compatibility
        from bot.utils.security import save_banned, load_banned
        banned = load_banned()
        banned[chat_id] = {
            "reason": reason,
            "banned_at": __import__('datetime').datetime.now().isoformat()
        }
        save_banned(banned)
        
        return jsonify({"ok": True, "chat_id": chat_id})
    
    return jsonify({"error": "Failed to ban user"}), 500


@app.route("/api/unban", methods=["POST"])
@login_required
def api_unban():
    """Unban a user."""
    payload = request.get_json(silent=True) or {}
    
    chat_id = str(payload.get("chat_id", "")).strip()
    if not chat_id:
        return jsonify({"error": "Thiếu chat_id"}), 400
    
    if unban_user(chat_id):
        # Also update JSON file for bot compatibility
        from bot.utils.security import save_banned, load_banned
        banned = load_banned()
        banned.pop(chat_id, None)
        save_banned(banned)
        
        return jsonify({"ok": True, "chat_id": chat_id})
    
    return jsonify({"error": "Failed to unban user"}), 500


@app.route("/api/search")
@login_required
def api_search():
    """Search users."""
    query = request.args.get("q", "")
    if not query or len(query) < 2:
        return jsonify({"users": []})
    
    users = search_users(query, 50)
    return jsonify({"users": users})


@app.route("/api/memory")
@login_required
def api_memory():
    """Get or update user memory."""
    chat_id = request.args.get("chat_id", "")
    memory_type = request.args.get("type", "facts")
    
    if request.method == "GET":
        if memory_type == "facts":
            facts = get_long_term_memory(chat_id)
            return jsonify({"facts": facts})
        elif memory_type == "context":
            context = get_short_term_memory(chat_id)
            return jsonify({"context": context})
    
    # POST - update memory
    payload = request.get_json(silent=True) or {}
    chat_id = payload.get("chat_id", "")
    memory_type = payload.get("type", "facts")
    content = payload.get("content", "")
    
    if memory_type == "facts":
        if update_long_term_memory(chat_id, content):
            return jsonify({"ok": True})
    
    return jsonify({"error": "Failed to update memory"}), 500


@app.route("/api/reset_context", methods=["POST"])
@login_required
def api_reset_context():
    """Reset short-term memory for a user."""
    payload = request.get_json(silent=True) or {}
    chat_id = payload.get("chat_id", "")
    
    if reset_short_term_memory(chat_id):
        return jsonify({"ok": True})
    
    return jsonify({"error": "Failed to reset context"}), 500


@app.route("/api/forget", methods=["POST"])
@login_required
def api_forget():
    """Forget all memory for a user."""
    payload = request.get_json(silent=True) or {}
    chat_id = payload.get("chat_id", "")
    
    if forget_user(chat_id):
        return jsonify({"ok": True})
    
    return jsonify({"error": "Failed to forget user"}), 500


@app.route("/api/activity")
@login_required
def api_activity():
    """Get recent activity."""
    activity = get_recent_activity(50)
    return jsonify({"activity": activity})


# ============================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================

@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection."""
    if session.get("logged_in"):
        emit("stats_update", build_dashboard_payload())


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket disconnection."""
    pass


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print()
    print("=" * 50)
    print("🐾 BRINGH ADMIN ĐANG CHẠY")
    print("=" * 50)
    print(f"URL: http://0.0.0.0:{ADMIN_PORT}")
    print(f"DATA: {DATA_DIR.resolve()}")
    print("=" * 50)
    print()
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=ADMIN_PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )
