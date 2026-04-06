from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import time, random, string

app = Flask(__name__)
app.secret_key = "notif_secret_2024"
socketio = SocketIO(app, cors_allowed_origins="*")

connected_users = {}
notification_history = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>LivePing – Real-Time Alerts</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #13131a;
    --surface2: #1c1c27;
    --border: #2a2a3d;
    --accent: #7c5cfc;
    --accent2: #fc5c7d;
    --green: #3effa3;
    --yellow: #ffd166;
    --text: #e8e8f0;
    --muted: #6e6e8a;
    --font: 'Syne', sans-serif;
    --mono: 'JetBrains Mono', monospace;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; overflow-x: hidden; }

  /* ── LOGIN ── */
  #login-screen {
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; position: relative;
    background: radial-gradient(ellipse 80% 60% at 50% -10%, #2a1a5e44, transparent),
                radial-gradient(ellipse 60% 40% at 80% 110%, #5c1a3a33, transparent);
  }
  #login-screen::before {
    content:''; position:absolute; inset:0;
    background-image: repeating-linear-gradient(0deg, transparent, transparent 39px, #ffffff06 40px),
                      repeating-linear-gradient(90deg, transparent, transparent 39px, #ffffff06 40px);
    pointer-events:none;
  }
  .login-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 48px 40px; width: 100%; max-width: 420px;
    position: relative; z-index:1;
    box-shadow: 0 0 60px #7c5cfc22, 0 24px 64px #00000088;
  }
  .login-card .logo { font-size: 28px; font-weight: 800; letter-spacing: -1px; margin-bottom: 6px; }
  .login-card .logo span { color: var(--accent); }
  .login-card .tagline { color: var(--muted); font-size: 13px; margin-bottom: 36px; font-family: var(--mono); }
  .login-card label { font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--muted); display: block; margin-bottom: 8px; }
  .login-card input[type=text] {
    width: 100%; background: var(--bg); border: 1px solid var(--border);
    color: var(--text); border-radius: 8px; padding: 12px 16px;
    font-family: var(--font); font-size: 15px; outline: none; transition: border .2s;
  }
  .login-card input[type=text]:focus { border-color: var(--accent); }
  .app-list { display: flex; gap: 10px; flex-wrap: wrap; margin: 20px 0 28px; }
  .app-pill {
    padding: 5px 12px; border-radius: 20px; font-size: 11px; font-family: var(--mono);
    border: 1px solid var(--border); color: var(--muted); cursor: pointer; transition: all .2s;
  }
  .app-pill:hover, .app-pill.active { border-color: var(--accent); color: var(--accent); background: #7c5cfc15; }
  .btn-join {
    width: 100%; padding: 13px; background: var(--accent); border: none; border-radius: 8px;
    color: #fff; font-family: var(--font); font-size: 15px; font-weight: 700;
    cursor: pointer; transition: transform .15s, box-shadow .15s;
    letter-spacing: .5px;
  }
  .btn-join:hover { transform: translateY(-2px); box-shadow: 0 8px 24px #7c5cfc55; }
  .btn-join:active { transform: translateY(0); }

  /* ── DASHBOARD ── */
  #dashboard { display: none; flex-direction: column; min-height: 100vh; }

  /* topbar */
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 24px; height: 56px; background: var(--surface);
    border-bottom: 1px solid var(--border); position: sticky; top:0; z-index:100;
  }
  .topbar .logo { font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }
  .topbar .logo span { color: var(--accent); }
  .status-row { display: flex; align-items: center; gap: 14px; }
  .status-dot { width:8px; height:8px; border-radius:50%; background: var(--green); box-shadow: 0 0 8px var(--green); }
  .username-badge { font-size:13px; font-family: var(--mono); color: var(--muted); }
  .user-count { font-size:12px; font-family: var(--mono); color: var(--muted); }
  .btn-leave { background:none; border:1px solid var(--border); color:var(--muted); font-family:var(--font); font-size:12px; padding:5px 12px; border-radius:6px; cursor:pointer; transition:all .2s; }
  .btn-leave:hover { border-color: var(--accent2); color: var(--accent2); }

  /* layout */
  .dashboard-body { display: grid; grid-template-columns: 1fr 340px; gap: 0; flex:1; }

  /* main panel */
  .main-panel { padding: 28px 28px 28px 28px; display: flex; flex-direction: column; gap: 20px; border-right: 1px solid var(--border); }

  /* app tabs */
  .app-tabs { display:flex; gap:8px; flex-wrap:wrap; }
  .app-tab {
    padding: 7px 16px; border-radius: 20px; font-size: 12px; font-family: var(--mono);
    border: 1px solid var(--border); color: var(--muted); cursor:pointer; transition: all .2s;
    display: flex; align-items:center; gap:6px;
  }
  .app-tab .app-icon { font-size: 14px; }
  .app-tab.active { background: var(--accent); border-color: var(--accent); color:#fff; }
  .app-tab:hover:not(.active) { border-color: var(--accent); color: var(--accent); }

  /* compose box */
  .compose-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px;
  }
  .compose-card h3 { font-size: 13px; text-transform: uppercase; letter-spacing:1.5px; color: var(--muted); margin-bottom:16px; }
  .compose-row { display:flex; gap:10px; }
  .compose-input {
    flex:1; background: var(--bg); border:1px solid var(--border); color:var(--text);
    border-radius:8px; padding:11px 14px; font-family:var(--font); font-size:14px; outline:none; transition:border .2s;
  }
  .compose-input:focus { border-color: var(--accent); }
  .btn-send {
    padding:11px 22px; background: var(--accent); border:none; border-radius:8px;
    color:#fff; font-family:var(--font); font-weight:700; font-size:14px; cursor:pointer; transition: all .15s;
    white-space:nowrap;
  }
  .btn-send:hover { background: #8f70ff; }
  .btn-send:active { transform: scale(.97); }

  /* quick triggers */
  .quick-section h3 { font-size:13px; text-transform:uppercase; letter-spacing:1.5px; color:var(--muted); margin-bottom:12px; }
  .quick-btns { display:flex; gap:10px; flex-wrap:wrap; }
  .qbtn {
    padding:8px 16px; border-radius:8px; font-size:13px; font-family:var(--font);
    border:1px solid var(--border); background: var(--surface); color:var(--text); cursor:pointer; transition:all .2s;
  }
  .qbtn:hover { background: var(--surface2); border-color: var(--accent); }

  /* live feed */
  .feed-section { flex:1; }
  .feed-section h3 { font-size:13px; text-transform:uppercase; letter-spacing:1.5px; color:var(--muted); margin-bottom:12px; }
  #live-feed {
    display:flex; flex-direction:column; gap:10px;
    max-height: 340px; overflow-y:auto; padding-right:4px;
  }
  #live-feed::-webkit-scrollbar { width:4px; }
  #live-feed::-webkit-scrollbar-thumb { background: var(--border); border-radius:4px; }
  .feed-empty { color:var(--muted); font-size:13px; font-family:var(--mono); text-align:center; padding:40px 0; }

  .notif-card {
    background: var(--surface); border:1px solid var(--border); border-radius:10px;
    padding: 14px 16px; display:flex; align-items:flex-start; gap:14px;
    animation: slideIn .3s ease; transition: border-color .3s;
    position: relative; overflow:hidden;
  }
  .notif-card::before {
    content:''; position:absolute; left:0; top:0; bottom:0; width:3px;
    background: var(--accent); border-radius:3px 0 0 3px;
  }
  .notif-card.type-alert::before { background: var(--accent2); }
  .notif-card.type-success::before { background: var(--green); }
  .notif-card.type-warning::before { background: var(--yellow); }
  .notif-app { font-size:20px; line-height:1; margin-top:1px; }
  .notif-body { flex:1; min-width:0; }
  .notif-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }
  .notif-sender { font-size:13px; font-weight:700; color:var(--text); }
  .notif-time { font-size:11px; font-family:var(--mono); color:var(--muted); }
  .notif-msg { font-size:13px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

  @keyframes slideIn { from { opacity:0; transform:translateY(-10px); } to { opacity:1; transform:none; } }

  /* ── LIVE ALERT POPUP ── */
  #alert-popup {
    position:fixed; top:72px; right:24px; z-index:9999;
    width:340px; background: var(--surface); border:1px solid var(--accent);
    border-radius:12px; padding:16px 18px; box-shadow: 0 8px 32px #7c5cfc44;
    transform: translateX(120%); transition: transform .35s cubic-bezier(.175,.885,.32,1.275);
    display:flex; align-items:flex-start; gap:12px;
  }
  #alert-popup.visible { transform: translateX(0); }
  #alert-popup .popup-icon { font-size:26px; line-height:1; }
  #alert-popup .popup-body { flex:1; }
  #alert-popup .popup-title { font-size:13px; font-weight:700; margin-bottom:3px; color:var(--accent); }
  #alert-popup .popup-msg { font-size:13px; color:var(--text); }
  #alert-popup .popup-close { background:none; border:none; color:var(--muted); font-size:18px; cursor:pointer; padding:0; line-height:1; margin-top:-2px; }
  .popup-bar { position:absolute; bottom:0; left:0; height:2px; background:var(--accent); border-radius:0 0 12px 12px; animation: shrink 4s linear forwards; }
  @keyframes shrink { from { width:100%; } to { width:0%; } }

  /* sidebar */
  .sidebar { padding: 24px 20px; display:flex; flex-direction:column; gap:20px; }
  .sidebar h3 { font-size:13px; text-transform:uppercase; letter-spacing:1.5px; color:var(--muted); margin-bottom:12px; }
  .users-list { display:flex; flex-direction:column; gap:8px; max-height:200px; overflow-y:auto; }
  .user-item { display:flex; align-items:center; gap:10px; padding:8px 10px; background:var(--surface); border-radius:8px; border:1px solid var(--border); }
  .user-avatar { width:28px; height:28px; border-radius:50%; background: var(--accent); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:#fff; flex-shrink:0; }
  .user-name { font-size:13px; font-family:var(--mono); }
  .user-you { font-size:10px; color:var(--muted); margin-left:auto; }

  .history-list { display:flex; flex-direction:column; gap:8px; max-height: 280px; overflow-y:auto; }
  .history-list::-webkit-scrollbar { width:4px; }
  .history-list::-webkit-scrollbar-thumb { background: var(--border); border-radius:4px; }
  .hist-item { padding:10px 12px; background:var(--surface); border-radius:8px; border:1px solid var(--border); }
  .hist-sender { font-size:11px; color:var(--accent); font-family:var(--mono); margin-bottom:3px; }
  .hist-msg { font-size:12px; color:var(--muted); }
  .hist-time { font-size:10px; color:var(--border); font-family:var(--mono); margin-top:4px; }

  /* sound wave animation for live indicator */
  .live-badge { display:inline-flex; align-items:center; gap:6px; background:#3effa322; border:1px solid var(--green); border-radius:20px; padding:3px 10px; font-size:11px; font-family:var(--mono); color:var(--green); }
  .wave { display:inline-flex; gap:2px; align-items:flex-end; height:12px; }
  .wave span { width:2px; background:var(--green); border-radius:2px; animation: wave 1s ease-in-out infinite; }
  .wave span:nth-child(1) { height:4px; animation-delay:0s; }
  .wave span:nth-child(2) { height:8px; animation-delay:.15s; }
  .wave span:nth-child(3) { height:12px; animation-delay:.3s; }
  .wave span:nth-child(4) { height:6px; animation-delay:.45s; }
  @keyframes wave { 0%,100% { transform:scaleY(1); } 50% { transform:scaleY(.4); } }

  @media(max-width:768px) {
    .dashboard-body { grid-template-columns:1fr; }
    .sidebar { border-top:1px solid var(--border); }
  }
</style>
</head>
<body>

<!-- ══ LOGIN ══ -->
<div id="login-screen">
  <div class="login-card">
    <div class="logo">Live<span>Ping</span></div>
    <div class="tagline">// real-time notification system</div>
    <label>your username</label>
    <input type="text" id="username-input" placeholder="e.g. john_doe" maxlength="24"/>
    <div class="app-list" id="app-list">
      <span class="app-pill active" data-app="WhatsApp">💬 WhatsApp</span>
      <span class="app-pill" data-app="Instagram">📸 Instagram</span>
      <span class="app-pill" data-app="Twitter">🐦 Twitter</span>
      <span class="app-pill" data-app="Facebook">👤 Facebook</span>
      <span class="app-pill" data-app="YouTube">▶️ YouTube</span>
      <span class="app-pill" data-app="Snapchat">👻 Snapchat</span>
    </div>
    <button class="btn-join" onclick="joinSystem()">Join Live System →</button>
  </div>
</div>

<!-- ══ DASHBOARD ══ -->
<div id="dashboard">

  <div class="topbar">
    <div class="logo">Live<span>Ping</span></div>
    <div class="status-row">
      <div class="live-badge"><div class="wave"><span></span><span></span><span></span><span></span></div> LIVE</div>
      <span class="username-badge" id="top-username"></span>
      <span class="user-count" id="top-usercount">0 online</span>
      <button class="btn-leave" onclick="leaveSystem()">Leave</button>
    </div>
  </div>

  <div class="dashboard-body">

    <!-- main -->
    <div class="main-panel">

      <div class="app-tabs" id="app-tabs"></div>

      <div class="compose-card">
        <h3>Send Notification</h3>
        <div class="compose-row">
          <input class="compose-input" id="msg-input" type="text" placeholder="Type your message…" maxlength="120"/>
          <button class="btn-send" onclick="sendNotification()">⚡ Send</button>
        </div>
      </div>

      <div class="quick-section">
        <h3>Quick Triggers</h3>
        <div class="quick-btns">
          <button class="qbtn" onclick="quickSend('🔔 New message received!')">🔔 New Message</button>
          <button class="qbtn" onclick="quickSend('❤️ Someone liked your post!')">❤️ Like</button>
          <button class="qbtn" onclick="quickSend('💬 New comment on your photo!')">💬 Comment</button>
          <button class="qbtn" onclick="quickSend('👥 New follower request!')">👥 Follow Request</button>
          <button class="qbtn" onclick="quickSend('🔴 You are live now!')">🔴 Go Live</button>
          <button class="qbtn" onclick="quickSend('📦 Your order has been shipped!')">📦 Order</button>
        </div>
      </div>

      <div class="feed-section">
        <h3>Live Feed</h3>
        <div id="live-feed">
          <div class="feed-empty">No notifications yet. Send the first one!</div>
        </div>
      </div>

    </div>

    <!-- sidebar -->
    <div class="sidebar">
      <div>
        <h3>Online Users</h3>
        <div class="users-list" id="users-list"></div>
      </div>
      <div>
        <h3>Notification History</h3>
        <div class="history-list" id="history-list"></div>
      </div>
    </div>

  </div>
</div>

<!-- ══ ALERT POPUP ══ -->
<div id="alert-popup">
  <div class="popup-icon" id="popup-icon">🔔</div>
  <div class="popup-body">
    <div class="popup-title" id="popup-title">New Notification</div>
    <div class="popup-msg" id="popup-msg"></div>
  </div>
  <button class="popup-close" onclick="closePopup()">✕</button>
  <div class="popup-bar" id="popup-bar"></div>
</div>

<script>
const APP_META = {
  WhatsApp:  { icon:'💬', color:'#25d366' },
  Instagram: { icon:'📸', color:'#e1306c' },
  Twitter:   { icon:'🐦', color:'#1da1f2' },
  Facebook:  { icon:'👤', color:'#1877f2' },
  YouTube:   { icon:'▶️', color:'#ff0000' },
  Snapchat:  { icon:'👻', color:'#fffc00' },
};

let currentUser = '';
let selectedApp = 'WhatsApp';
let socket = null;
let popupTimer = null;
let feedEmpty = true;

// ── pill selection
document.querySelectorAll('.app-pill').forEach(p => {
  p.addEventListener('click', () => {
    document.querySelectorAll('.app-pill').forEach(x => x.classList.remove('active'));
    p.classList.add('active');
    selectedApp = p.dataset.app;
  });
});

// ── enter key
document.getElementById('username-input').addEventListener('keydown', e => { if(e.key==='Enter') joinSystem(); });

function joinSystem() {
  const val = document.getElementById('username-input').value.trim();
  if(!val) { document.getElementById('username-input').style.borderColor='var(--accent2)'; return; }
  currentUser = val;
  document.getElementById('top-username').textContent = '@' + currentUser;

  // build app tabs
  const tabs = document.getElementById('app-tabs');
  tabs.innerHTML = Object.entries(APP_META).map(([name,meta]) =>
    `<div class="app-tab ${name===selectedApp?'active':''}" data-app="${name}" onclick="selectTab(this,'${name}')">`+
    `<span class="app-icon">${meta.icon}</span>${name}</div>`
  ).join('');

  // connect socket
  socket = io();

  socket.on('connect', () => {
    socket.emit('user_join', { username: currentUser });
  });

  socket.on('user_list', data => {
    updateUserList(data.users);
    document.getElementById('top-usercount').textContent = data.users.length + ' online';
  });

  socket.on('new_notification', data => {
    addToFeed(data);
    addToHistory(data);
    showPopup(data);
  });

  socket.on('history', data => {
    data.notifications.forEach(n => addToHistory(n));
  });

  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('dashboard').style.display = 'flex';
}

function leaveSystem() {
  if(socket) socket.disconnect();
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('dashboard').style.display = 'none';
  document.getElementById('live-feed').innerHTML = '<div class="feed-empty">No notifications yet. Send the first one!</div>';
  document.getElementById('history-list').innerHTML = '';
  feedEmpty = true;
}

function selectTab(el, app) {
  document.querySelectorAll('.app-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  selectedApp = app;
}

function sendNotification() {
  const msg = document.getElementById('msg-input').value.trim();
  if(!msg || !socket) return;
  socket.emit('send_notification', {
    username: currentUser,
    app: selectedApp,
    message: msg
  });
  document.getElementById('msg-input').value = '';
}

function quickSend(msg) {
  if(!socket) return;
  socket.emit('send_notification', {
    username: currentUser,
    app: selectedApp,
    message: msg
  });
}

document.getElementById('msg-input').addEventListener('keydown', e => {
  if(e.key==='Enter') sendNotification();
});

function addToFeed(data) {
  const feed = document.getElementById('live-feed');
  if(feedEmpty) { feed.innerHTML = ''; feedEmpty = false; }
  const meta = APP_META[data.app] || { icon:'🔔', color:'var(--accent)' };
  const card = document.createElement('div');
  card.className = 'notif-card';
  card.style.setProperty('--card-accent', meta.color);
  card.innerHTML =
    `<div class="notif-app">${meta.icon}</div>`+
    `<div class="notif-body">`+
      `<div class="notif-header">`+
        `<span class="notif-sender">@${data.username}</span>`+
        `<span class="notif-time">${data.time}</span>`+
      `</div>`+
      `<div class="notif-msg">${escHtml(data.message)}</div>`+
    `</div>`;
  card.querySelector('.notif-card')?.style;
  feed.insertBefore(card, feed.firstChild);
  if(feed.children.length > 40) feed.removeChild(feed.lastChild);
}

function addToHistory(data) {
  const list = document.getElementById('history-list');
  const meta = APP_META[data.app] || { icon:'🔔' };
  const item = document.createElement('div');
  item.className = 'hist-item';
  item.innerHTML =
    `<div class="hist-sender">${meta.icon} @${data.username} · ${data.app}</div>`+
    `<div class="hist-msg">${escHtml(data.message)}</div>`+
    `<div class="hist-time">${data.time}</div>`;
  list.insertBefore(item, list.firstChild);
  if(list.children.length > 30) list.removeChild(list.lastChild);
}

function updateUserList(users) {
  const list = document.getElementById('users-list');
  list.innerHTML = users.map(u =>
    `<div class="user-item">`+
      `<div class="user-avatar">${u[0].toUpperCase()}</div>`+
      `<span class="user-name">${u}</span>`+
      (u===currentUser ? `<span class="user-you">you</span>` : '')+
    `</div>`
  ).join('');
}

function showPopup(data) {
  const meta = APP_META[data.app] || { icon:'🔔' };
  document.getElementById('popup-icon').textContent = meta.icon;
  document.getElementById('popup-title').textContent = data.app + ' · @' + data.username;
  document.getElementById('popup-msg').textContent = data.message;

  // reset bar
  const bar = document.getElementById('popup-bar');
  bar.style.animation = 'none';
  void bar.offsetWidth;
  bar.style.animation = 'shrink 4s linear forwards';

  const popup = document.getElementById('alert-popup');
  popup.classList.add('visible');
  if(popupTimer) clearTimeout(popupTimer);
  popupTimer = setTimeout(closePopup, 4000);
}

function closePopup() {
  document.getElementById('alert-popup').classList.remove('visible');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on("user_join")
def handle_join(data):
    username = data.get("username", "Anonymous")
    sid = request.sid
    connected_users[sid] = username

    # send history to newcomer
    emit("history", {"notifications": notification_history[-20:]}, to=sid)

    # broadcast updated user list
    socketio.emit("user_list", {"users": list(connected_users.values())})
    print(f"[JOIN] {username} connected ({len(connected_users)} online)")

@socketio.on("send_notification")
def handle_notification(data):
    username = data.get("username", "Unknown")
    app_name = data.get("app", "App")
    message = data.get("message", "")

    ts = time.strftime("%H:%M")
    notif = {
        "username": username,
        "app": app_name,
        "message": message,
        "time": ts
    }
    notification_history.append(notif)
    if len(notification_history) > 100:
        notification_history.pop(0)

    socketio.emit("new_notification", notif)
    print(f"[NOTIF] @{username} via {app_name}: {message}")

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    user = connected_users.pop(sid, "Unknown")
    socketio.emit("user_list", {"users": list(connected_users.values())})
    print(f"[LEAVE] {user} disconnected ({len(connected_users)} online)")

if __name__ == "__main__":
    print("=" * 50)
    print("  LivePing – Real-Time Notification System")
    print("  Running on http://127.0.0.1:5000")
    print("=" * 50)
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
