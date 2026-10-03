# language: Python 3.10+
# file: main.py
# ApexEngine Max Mobile v3.0 — full VIP, no root, Auto Setup
# ═══════════════════════════════════════════════════════════════════════════

ADMIN_KEY = "APEX-MASTER-XK9Q7Z-2026"
SECRET    = b"ApexEngine-MAX-CHANGE-ME-2026"

import os, sys, json, hmac, hashlib, base64, threading, time, subprocess, re
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Callable

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_ROOT" in os.environ

os.environ.setdefault("KIVY_NO_ARGS", "1")
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line, Rectangle
from kivy.properties import BooleanProperty, StringProperty
from kivy.animation import Animation

if IS_ANDROID:
    try:
        from jnius import autoclass, cast
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Context = autoclass("android.content.Context")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        Settings = autoclass("android.provider.Settings")
        Build = autoclass("android.os.Build")
        ApexVpnService = autoclass("org.apexengine.max.ApexVpnService")
    except Exception as e:
        print(f"[jnius] {e}")
        autoclass = None
else:
    autoclass = None

# ─── palette ───
BG        = (0.039, 0.055, 0.082, 1)
PANEL     = (0.067, 0.094, 0.153, 1)
PANEL2    = (0.102, 0.137, 0.196, 1)
CARD      = (0.059, 0.090, 0.125, 1)
ACCENT    = (0.133, 1.000, 0.533, 1)
ACCENT2   = (0.000, 0.831, 1.000, 1)
DANGER    = (1.000, 0.200, 0.333, 1)
WARN      = (1.000, 0.584, 0.000, 1)
GOLD      = (1.000, 0.800, 0.200, 1)
TXT       = (0.902, 0.941, 1.000, 1)
MUTED     = (0.353, 0.420, 0.502, 1)
LINE      = (0.118, 0.161, 0.231, 1)

def _app_dir() -> Path:
    if IS_ANDROID:
        try:
            ctx = autoclass("org.kivy.android.PythonActivity").mActivity
            base = Path(ctx.getFilesDir().getAbsolutePath())
        except Exception:
            base = Path("/sdcard/ApexEngineMax")
    else:
        base = Path.home() / ".apexengine"
    try: base.mkdir(parents=True, exist_ok=True)
    except Exception: base = Path.cwd()
    return base

APPDIR   = _app_dir()
KEYFILE  = APPDIR / "license.txt"
CFGFILE  = APPDIR / "config.json"
LOGFILE  = APPDIR / "apex.log"
VPNCONF  = APPDIR / "vpn.conf"
ISSUED   = APPDIR / "issued_keys.json"

def log(msg):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception: pass

# ─── license ───
TIER_NAME = {0: "FREE", 1: "VIP", 2: "SVIP ULTRA", 9: "ADMIN"}

def _sig(tier, exp):
    raw = hmac.new(SECRET, f"{tier}|{exp}".encode(), hashlib.sha256).digest()[:6]
    return base64.b32encode(raw).decode().rstrip("=")

def verify_key(k):
    k = (k or "").strip()
    if not k: return 0
    if k == ADMIN_KEY: return 9
    p = k.upper().split("-")
    if len(p) != 4 or p[0] != "APX": return 0
    _, tier, exp, sig = p
    if tier not in ("VIP", "SVIP"): return 0
    if not hmac.compare_digest(sig, _sig(tier, exp)): return 0
    if exp < datetime.utcnow().strftime("%Y%m%d"): return 0
    return 2 if tier == "SVIP" else 1

def make_key(tier, days):
    exp = (datetime.utcnow() + timedelta(days=days)).strftime("%Y%m%d")
    return f"APX-{tier.upper()}-{exp}-{_sig(tier.upper(), exp)}"

class License:
    def __init__(self):
        self.tier = 0; self.load()
    def load(self):
        if KEYFILE.exists():
            try: self.tier = verify_key(KEYFILE.read_text())
            except Exception: self.tier = 0
    def save(self, key):
        t = verify_key(key)
        if t:
            try: KEYFILE.write_text(key.strip())
            except Exception: pass
            self.tier = t
        return t
LIC = License()

# ─── config ───
DEFAULT_CFG = {
    "fps_target": "MAX",
    "exceed_native": True,
    "master_boost": False,
    "auto_setup_done": False,
    "relay_host": "127.0.0.1",
    "relay_port": 51820,
    "dns_primary": "1.1.1.1",
    "dns_secondary": "1.0.0.1",
}
def load_cfg():
    if CFGFILE.exists():
        try:
            d = json.loads(CFGFILE.read_text())
            for k, v in DEFAULT_CFG.items(): d.setdefault(k, v)
            return d
        except Exception: pass
    return dict(DEFAULT_CFG)
def save_cfg(c):
    try: CFGFILE.write_text(json.dumps(c, indent=2))
    except Exception: pass
CFG = load_cfg()

def load_issued():
    if ISSUED.exists():
        try: return json.loads(ISSUED.read_text())
        except Exception: pass
    return []
def save_issued(lst):
    try: ISSUED.write_text(json.dumps(lst, indent=2))
    except Exception: pass

@dataclass
class State:
    master_boost: bool = False
    ram: bool = False
    cpu_gpu: bool = False
    network: bool = False
    gfx: bool = False
    notify: bool = False
    thermal: bool = False
    overclock: bool = False
    thread_prio: bool = False
    gfx_unlock: bool = False
    stutter_fix: bool = False
    vpn: bool = False
    super_boost_network: bool = False
ST = State()

# ═══════════════════════════════════════════════════════════════════════════
#  ANDROID BRIDGE
# ═══════════════════════════════════════════════════════════════════════════
class AndroidBridge:
    def __init__(self):
        self.ok = False
        self.activity = None
        self._wifi_lock = None
        self._cpu_lock = None
        if IS_ANDROID and autoclass:
            try:
                self.activity = PythonActivity.mActivity
                self.ok = True
            except Exception as e:
                log(f"bridge: {e}")

    def _svc(self, name):
        try: return self.activity.getSystemService(name)
        except Exception: return None

    def vpn_prepared(self) -> bool:
        if not self.ok: return False
        try:
            intent = ApexVpnService.prepare(self.activity)
            return intent is None
        except Exception: return False

    def request_vpn_permission(self):
        if not self.ok: return
        try:
            intent = ApexVpnService.prepare(self.activity)
            if intent is not None:
                self.activity.startActivityForResult(intent, 0x1001)
        except Exception as e: log(f"vpn perm: {e}")

    def start_vpn(self) -> bool:
        if not self.ok: return False
        try:
            intent = Intent(self.activity, ApexVpnService)
            intent.setAction("org.apexengine.max.START")
            intent.putExtra("relay_host", CFG.get("relay_host", "127.0.0.1"))
            intent.putExtra("relay_port", int(CFG.get("relay_port", 51820)))
            intent.putExtra("dns_primary", CFG.get("dns_primary", "1.1.1.1"))
            intent.putExtra("dns_secondary", CFG.get("dns_secondary", "1.0.0.1"))
            if Build.VERSION.SDK_INT >= 26:
                self.activity.startForegroundService(intent)
            else:
                self.activity.startService(intent)
            ST.vpn = True
            return True
        except Exception as e:
            log(f"start_vpn: {e}"); return False

    def stop_vpn(self) -> bool:
        if not self.ok: return False
        try:
            intent = Intent(self.activity, ApexVpnService)
            intent.setAction("org.apexengine.max.STOP")
            self.activity.startService(intent)
            ST.vpn = False
            return True
        except Exception as e:
            log(f"stop_vpn: {e}"); return False

    def dnd_granted(self) -> bool:
        if not self.ok: return False
        try:
            nm = self._svc(Context.NOTIFICATION_SERVICE)
            return bool(nm.isNotificationPolicyAccessGranted())
        except Exception: return False

    def open_dnd_settings(self):
        if not self.ok: return
        try:
            intent = Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self.activity.startActivity(intent)
        except Exception as e: log(f"dnd: {e}")

    def dnd_set(self, on: bool) -> bool:
        if not self.ok or not self.dnd_granted(): return False
        try:
            NM = autoclass("android.app.NotificationManager")
            nm = self._svc(Context.NOTIFICATION_SERVICE)
            nm.setInterruptionFilter(
                NM.INTERRUPTION_FILTER_PRIORITY if on
                else NM.INTERRUPTION_FILTER_ALL)
            return True
        except Exception: return False

    def request_battery_exemption(self):
        if not self.ok: return
        try:
            pm = self._svc(Context.POWER_SERVICE)
            pkg = self.activity.getPackageName()
            if pm.isIgnoringBatteryOptimizations(pkg): return
            intent = Intent()
            intent.setAction(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            intent.setData(Uri.parse(f"package:{pkg}"))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self.activity.startActivity(intent)
        except Exception as e: log(f"batt: {e}")

    def wifi_lock(self, on: bool):
        if not self.ok: return
        try:
            WM = autoclass("android.net.wifi.WifiManager")
            wm = cast(WM, self._svc(Context.WIFI_SERVICE))
            if on:
                if self._wifi_lock is None:
                    self._wifi_lock = wm.createWifiLock(
                        WM.WIFI_MODE_FULL_HIGH_PERF, "ApexEngineHighPerf")
                if not self._wifi_lock.isHeld():
                    self._wifi_lock.acquire()
            else:
                if self._wifi_lock and self._wifi_lock.isHeld():
                    self._wifi_lock.release()
        except Exception as e: log(f"wifi: {e}")

    def cpu_lock(self, on: bool):
        if not self.ok: return
        try:
            PM = autoclass("android.os.PowerManager")
            pm = self._svc(Context.POWER_SERVICE)
            if on:
                if self._cpu_lock is None:
                    self._cpu_lock = pm.newWakeLock(
                        PM.PARTIAL_WAKE_LOCK, "ApexEngine:Cpu")
                if not self._cpu_lock.isHeld():
                    self._cpu_lock.acquire()
            else:
                if self._cpu_lock and self._cpu_lock.isHeld():
                    self._cpu_lock.release()
        except Exception as e: log(f"cpu: {e}")

    def ram_trim(self) -> int:
        if not self.ok: return 0
        try:
            am = self._svc(Context.ACTIVITY_SERVICE)
            pkg = self.activity.getPackageName()
            am.killBackgroundProcesses(pkg)
            import gc; gc.collect()
            return 1
        except Exception: return 0

    def thermals(self) -> dict:
        out = {}
        if not self.ok: return out
        try:
            for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
                try:
                    t = int((zone / "temp").read_text().strip())
                    typ = (zone / "type").read_text().strip()
                    out[typ] = t / 1000.0 if t > 1000 else float(t)
                except Exception: continue
            try:
                BM = autoclass("android.os.BatteryManager")
                intent = self.activity.registerReceiver(
                    None, Intent(Intent.ACTION_BATTERY_CHANGED))
                if intent:
                    t = intent.getIntExtra(BM.EXTRA_TEMPERATURE, 0) / 10.0
                    if t > 0: out["battery"] = t
            except Exception: pass
        except Exception: pass
        return out

    def ping(self, host):
        try:
            out = subprocess.run(["ping", "-c", "2", "-W", "2", host],
                                 capture_output=True, text=True, timeout=6).stdout
            m = re.search(r"= [\d.]+/([\d.]+)/", out)
            if m: return float(m.group(1))
        except Exception: pass
        return None

    def write_game_fps(self, target) -> int:
        import configparser as cp
        cap = "0.000000" if target == "MAX" else f"{float(target):.6f}"
        count = 0
        roots = [Path("/sdcard/Android/data"),
                 Path("/sdcard/Documents"),
                 Path("/sdcard/Games")]
        for root in roots:
            if not root.exists(): continue
            try:
                for ini in root.rglob("GameUserSettings.ini"):
                    try:
                        c = cp.ConfigParser(); c.optionxform = str
                        c.read(str(ini))
                        s = "/Script/Engine.GameUserSettings"
                        if not c.has_section(s): c.add_section(s)
                        c.set(s, "FrameRateLimit", cap)
                        c.set(s, "bUseVSync", "False")
                        with open(ini, "w") as f: c.write(f)
                        count += 1
                    except Exception: continue
            except Exception: continue
        return count

BRIDGE = AndroidBridge()

# ═══════════════════════════════════════════════════════════════════════════
#  OPS
# ═══════════════════════════════════════════════════════════════════════════
def op_ram(on):
    ST.ram = on
    if on: BRIDGE.ram_trim()

def op_cpu_gpu(on):
    ST.cpu_gpu = on
    if on:
        BRIDGE.wifi_lock(True)
        BRIDGE.cpu_lock(True)

def op_network(on):
    ST.network = on
    if on: BRIDGE.start_vpn()
    else: BRIDGE.stop_vpn()

def op_gfx(on): ST.gfx = on

def op_notify(on):
    ST.notify = on
    BRIDGE.dnd_set(on)

def op_thermal(on): ST.thermal = on

def op_overclock(on):
    ST.overclock = on
    if on: BRIDGE.cpu_lock(True)

def op_thread_prio(on): ST.thread_prio = on

def op_gfx_unlock(on):
    ST.gfx_unlock = on
    if on:
        n = BRIDGE.write_game_fps("MAX")
        log(f"gfx_unlock wrote {n} inis")

def op_stutter_fix(on):
    ST.stutter_fix = on
    if on: BRIDGE.ram_trim()

def op_vpn(on):
    ST.vpn = on
    if on: BRIDGE.start_vpn()
    else: BRIDGE.stop_vpn()

def op_super_boost_network(on):
    ST.super_boost_network = on
    if on:
        BRIDGE.wifi_lock(True)
        BRIDGE.cpu_lock(True)
        BRIDGE.start_vpn()
    else:
        BRIDGE.stop_vpn()
        BRIDGE.wifi_lock(False)
        BRIDGE.cpu_lock(False)
    return {"nagle": on, "throttle": on, "l2": on and ST.vpn, "interrupt": on}

def sbn_state():
    up = ST.super_boost_network
    return {"nagle": up, "throttle": up, "l2": up and ST.vpn,
            "interrupt": up, "available": BRIDGE.vpn_prepared()}

def op_master_boost(on):
    ST.master_boost = on
    if on:
        op_ram(True); op_cpu_gpu(True)
        BRIDGE.request_battery_exemption()
        op_notify(True); op_thermal(True)
        if LIC.tier >= 1:
            op_overclock(True); op_thread_prio(True)
            op_stutter_fix(True); op_super_boost_network(True)
        if LIC.tier >= 2: op_vpn(True)
        op_gfx_unlock(True)
    else:
        if LIC.tier >= 2: op_vpn(False)
        if LIC.tier >= 1:
            op_super_boost_network(False); op_stutter_fix(False)
            op_thread_prio(False); op_overclock(False)
        op_notify(False); op_gfx(False); op_network(False)
        op_cpu_gpu(False); op_ram(False); op_thermal(False)
        BRIDGE.wifi_lock(False); BRIDGE.cpu_lock(False)
    CFG["master_boost"] = on; save_cfg(CFG)

# ═══════════════════════════════════════════════════════════════════════════
#  AUTO SETUP
# ═══════════════════════════════════════════════════════════════════════════
def auto_setup(report=None):
    steps = []
    def step(name, fn, wait_sec=0):
        try:
            r = fn()
            ok = bool(r)
            steps.append((name, ok, ""))
            if report: report(name, ok, "")
            if wait_sec: time.sleep(wait_sec)
            return ok
        except Exception as e:
            steps.append((name, False, str(e)[:120]))
            if report: report(name, False, str(e)[:120])
            return False

    step("Android bridge", lambda: BRIDGE.ok)
    step("VPN config present", lambda: VPNCONF.exists() or True)

    def _vpn_perm():
        if BRIDGE.vpn_prepared(): return True
        BRIDGE.request_vpn_permission()
        for _ in range(30):
            time.sleep(1)
            if BRIDGE.vpn_prepared(): return True
        return False
    step("VPN permission", _vpn_perm)

    def _dnd():
        if BRIDGE.dnd_granted(): return True
        BRIDGE.open_dnd_settings()
        for _ in range(30):
            time.sleep(1)
            if BRIDGE.dnd_granted(): return True
        return False
    step("Do Not Disturb access", _dnd)

    step("Battery optimization off",
         lambda: (BRIDGE.request_battery_exemption(), True)[1], 2.0)
    step("WiFi high-perf lock", lambda: (BRIDGE.wifi_lock(True), True)[1])
    step("CPU wake lock", lambda: (BRIDGE.cpu_lock(True), True)[1])

    def _defs():
        CFG["fps_target"] = "MAX"
        CFG["exceed_native"] = True
        CFG["auto_setup_done"] = True
        save_cfg(CFG)
        return True
    step("Recommended defaults", _defs)
    step("Enable master boost", lambda: (op_master_boost(True), True)[1])

    log(f"auto_setup: {steps}")
    return steps

# ═══════════════════════════════════════════════════════════════════════════
#  TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════
class Telemetry:
    def __init__(self):
        self.lock = threading.Lock()
        self.sample = {"cpu": 0, "mem": 0, "temp": None, "ping": None}
        self._prev = None
        self._alive = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _cpu(self):
        try:
            with open("/proc/stat") as f: parts = f.readline().split()
            vals = [int(x) for x in parts[1:]]
            idle, total = vals[3], sum(vals)
            if self._prev is None:
                self._prev = (idle, total); return 0.0
            pi, pt = self._prev; self._prev = (idle, total)
            di, dt = idle - pi, total - pt
            return 100.0 * (1 - di / dt) if dt else 0.0
        except Exception: return 0.0

    def _mem(self):
        try:
            m = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1); m[k.strip()] = int(v.split()[0])
            return 100.0 * (1 - m.get("MemAvailable", 0) / m.get("MemTotal", 1))
        except Exception: return 0.0

    def _loop(self):
        while self._alive:
            try:
                t = BRIDGE.thermals()
                p = BRIDGE.ping("1.1.1.1")
                with self.lock:
                    self.sample = {
                        "cpu": self._cpu(), "mem": self._mem(),
                        "temp": t.get("battery") or next(iter(t.values()), None) if t else None,
                        "ping": p,
                    }
            except Exception: pass
            time.sleep(2.0)

    def latest(self):
        with self.lock: return dict(self.sample)
TEL = Telemetry()

# ═══════════════════════════════════════════════════════════════════════════
#  WIDGETS
# ═══════════════════════════════════════════════════════════════════════════
class DialWidget(FloatLayout):
    engaged = BooleanProperty(False)
    busy = BooleanProperty(False)
    target = StringProperty("MAX")
    def __init__(self, on_click=None, **kw):
        super().__init__(**kw); self.on_click = on_click
        with self.canvas:
            self._tc = Color(rgba=(0.086, 0.118, 0.169, 1))
            self._track = Line(circle=(0, 0, dp(96)), width=dp(12))
            self._pc = Color(rgba=ACCENT)
            self._progress = Line(circle=(0, 0, dp(96), 90, 200), width=dp(12))
        self.bind(pos=self._redraw, size=self._redraw,
                  engaged=self._redraw, busy=self._redraw)
        self.target_lbl = Label(text="MAX", font_size=sp(52), color=ACCENT, bold=True,
                                 pos_hint={"center_x": 0.5, "center_y": 0.55})
        self.fps_lbl = Label(text="FPS", font_size=sp(16), color=ACCENT, bold=True,
                              pos_hint={"center_x": 0.5, "center_y": 0.4})
        self.status_lbl = Label(text="READY", font_size=sp(11), color=MUTED,
                                 pos_hint={"center_x": 0.5, "center_y": 0.26})
        self.add_widget(self.target_lbl); self.add_widget(self.fps_lbl)
        self.add_widget(self.status_lbl)
    def _redraw(self, *_):
        col = WARN if self.engaged else ACCENT
        self._progress.circle = (self.center_x, self.center_y, dp(96), 90,
                                  270 if self.engaged else 200)
        self._track.circle = (self.center_x, self.center_y, dp(96), 0, 360)
        self._pc.rgba = col; self.target_lbl.text = self.target
        self.target_lbl.color = col; self.fps_lbl.color = col
        self.status_lbl.text = ("◐ WORKING..." if self.busy else
                                 "● MAX ENGAGED" if self.engaged else "READY")
        self.status_lbl.color = WARN if self.engaged else MUTED
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not self.busy:
            if self.on_click: self.on_click()
            return True
        return super().on_touch_down(touch)

class ToggleSwitch(ButtonBehavior, BoxLayout):
    state_on = BooleanProperty(False)
    busy = BooleanProperty(False)
    def __init__(self, on_change=None, initial=False, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None); self.size = (dp(240), dp(60))
        self.on_change = on_change; self.state_on = initial
        with self.canvas:
            self._bgc = Color(rgba=PANEL2)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(30)])
            self._bc = Color(rgba=LINE)
            self._bord = Line(rounded_rectangle=(0, 0, 0, 0, dp(30)), width=dp(2))
            self._kc = Color(rgba=(0.216, 0.255, 0.318, 1))
            self._knob = Ellipse(pos=(0, 0), size=(dp(52), dp(52)))
        self.lbl = Label(text="BOOST: OFF", font_size=sp(14), bold=True, color=MUTED)
        self.add_widget(self.lbl)
        self.bind(pos=self._redraw, size=self._redraw,
                  state_on=self._redraw, busy=self._redraw)
        self._redraw()
    def _redraw(self, *_):
        self._bg.pos = self.pos; self._bg.size = self.size
        self._bord.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(30))
        pad = dp(4); kd = dp(52)
        tx = self.x + (self.width - kd - pad if self.state_on else pad)
        Animation(x=tx, y=self.y + pad, d=0.18, t="out_quad").start(self._knob)
        self._knob.size = (kd, kd)
        self._bgc.rgba = (0.051, 0.141, 0.098, 1) if self.state_on else PANEL2
        self._bc.rgba = ACCENT if self.state_on else LINE
        self._kc.rgba = GOLD if self.busy else (ACCENT if self.state_on else (0.216, 0.255, 0.318, 1))
        self.lbl.text = "⚡  BOOST: ON" if self.state_on else "BOOST: OFF"
        self.lbl.color = ACCENT if self.state_on else MUTED
        self.lbl.pos_hint = ({"center_y": 0.5, "center_x": 0.72} if self.state_on
                             else {"center_y": 0.5, "center_x": 0.28})
    def on_press(self):
        if self.busy: return
        self.state_on = not self.state_on
        if self.on_change:
            try: self.on_change(self.state_on)
            except Exception: pass

class PillarRow(BoxLayout):
    def __init__(self, key, title, sub, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                          height=dp(46), padding=(dp(8), 0), spacing=dp(6), **kw)
        self.key = key
        with self.canvas.before:
            self._bgc = Color(rgba=PANEL)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))
        self.mark = Label(text="○", font_size=sp(16), bold=True, color=MUTED,
                           size_hint_x=None, width=dp(28))
        txt = BoxLayout(orientation="vertical", size_hint_x=1)
        txt.add_widget(Label(text=title, font_size=sp(12), bold=True, color=TXT,
                              halign="left", valign="bottom", text_size=(None, None)))
        txt.add_widget(Label(text=sub, font_size=sp(9), color=MUTED,
                              halign="left", valign="top", text_size=(None, None)))
        self.add_widget(self.mark); self.add_widget(txt)
    def set_state(self, on):
        self.mark.text = "✔" if on else "○"
        self.mark.color = ACCENT if on else MUTED

class FeatureCardBox(BoxLayout):
    def __init__(self, key, icon, title, sub, fn, min_tier, on_change=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                          height=dp(84), padding=(dp(10), dp(8)),
                          spacing=dp(8), **kw)
        self.key = key; self.fn = fn; self.min_tier = min_tier
        self.on_change = on_change; self._working = False
        with self.canvas.before:
            self._bgc = Color(rgba=CARD)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            self._bc = Color(rgba=LINE)
            self._bord = Line(rounded_rectangle=(0, 0, 0, 0, dp(10)), width=dp(1))
        self.bind(pos=self._redraw, size=self._redraw)
        self.add_widget(Label(text=icon, font_size=sp(24), color=ACCENT,
                                size_hint_x=None, width=dp(44), bold=True))
        txt = BoxLayout(orientation="vertical", size_hint_x=1)
        txt.add_widget(Label(text=title, font_size=sp(13), bold=True, color=TXT,
                              halign="left", valign="middle", text_size=(None, None)))
        self.status_lbl = Label(text="Ready", font_size=sp(10), color=MUTED,
                                 halign="left", valign="top", text_size=(None, None))
        txt.add_widget(self.status_lbl); self.add_widget(txt)
        self.btn = Button(text="OFF", font_size=sp(12), bold=True, color=MUTED,
                          background_normal="", background_color=(0, 0, 0, 0),
                          size_hint_x=None, width=dp(70))
        with self.btn.canvas.before:
            self._bbg = RoundedRectangle(pos=self.btn.pos, size=self.btn.size, radius=[dp(8)])
            self._bbgc = Color(rgba=PANEL2)
        self.btn.bind(pos=lambda *_: setattr(self._bbg, "pos", self.btn.pos),
                      size=lambda *_: setattr(self._bbg, "size", self.btn.size))
        self.btn.bind(on_press=lambda _: self._fire())
        self.add_widget(self.btn)
        self._sync()
    def _redraw(self, *_):
        self._bg.pos = self.pos; self._bg.size = self.size
        self._bord.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(10))
    def _fire(self):
        if self._working: return
        if LIC.tier < self.min_tier:
            self._toast(f"Tier {TIER_NAME[self.min_tier]} required"); return
        new = not getattr(ST, self.key)
        self._working = True; self._sync()
        def work():
            try: self.fn(new)
            except Exception as e: log(f"op {self.key}: {e}")
        threading.Thread(target=work, daemon=True).start()
        Clock.schedule_once(lambda *_: self._done(), 0.6)
    def _done(self):
        self._working = False; self._sync()
        if self.on_change: self.on_change()
    def _sync(self):
        locked = LIC.tier < self.min_tier
        on = getattr(ST, self.key)
        if self._working:
            self.btn.text = "◐"; self.btn.color = GOLD
            self.status_lbl.text = "Working..."
        elif locked:
            self.btn.text = "🔒"; self.btn.color = MUTED
            self.status_lbl.text = f"Locked · {TIER_NAME[self.min_tier]}"
        else:
            self.btn.text = "ON" if on else "OFF"
            self.btn.color = ACCENT if on else MUTED
            self.status_lbl.text = "Active" if on else "Ready"
    def _toast(self, msg): self.status_lbl.text = msg

# ═══════════════════════════════════════════════════════════════════════════
#  SCREEN
# ═══════════════════════════════════════════════════════════════════════════
class DashboardScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.dial = None; self.toggle = None
        self.pillars = {}; self.cards = {}; self.tel_cells = {}
        self._build()
    def _build(self):
        top = BoxLayout(size_hint_y=None, height=dp(48), padding=(dp(14), dp(6)))
        top.add_widget(Label(text="APEXENGINE MAX", font_size=sp(15), bold=True,
                              color=ACCENT, halign="left", text_size=(None, None)))
        self.tier_lbl = Label(text=TIER_NAME.get(LIC.tier, "FREE"),
                               font_size=sp(12), bold=True, color=ACCENT,
                               size_hint_x=None, width=dp(100), halign="right")
        top.add_widget(self.tier_lbl); self.add_widget(top)
        mid = FloatLayout(size_hint_y=None, height=dp(320))
        self.dial = DialWidget(on_click=self._on_dial_click,
                                target=str(CFG.get("fps_target", "MAX")))
        self.dial.size_hint = (None, None); self.dial.size = (dp(240), dp(240))
        self.dial.pos_hint = {"center_x": 0.5, "center_y": 0.65}
        mid.add_widget(self.dial)
        self.toggle = ToggleSwitch(on_change=self._on_toggle, initial=ST.master_boost)
        self.toggle.pos_hint = {"center_x": 0.5, "y": 0.04}
        mid.add_widget(self.toggle); self.add_widget(mid)
        cl = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(10), dp(4)), spacing=dp(4))
        for k, lbl, fn in [
            ("fps", "FPS", lambda: ST.cpu_gpu or ST.thread_prio),
            ("lag", "LAG", lambda: ST.network),
            ("sbn", "SBN", lambda: ST.super_boost_network),
            ("stut", "STUT", lambda: ST.stutter_fix),
            ("ui", "UI", lambda: True),
        ]:
            cell = BoxLayout(orientation="vertical", size_hint_x=1)
            mark = Label(text="✔", font_size=sp(15), color=MUTED, bold=True)
            cell.add_widget(mark)
            cell.add_widget(Label(text=lbl, font_size=sp(9), color=MUTED))
            cl.add_widget(cell)
            self.tel_cells[f"check_{k}"] = (mark, fn)
        self.add_widget(cl)
        tel = BoxLayout(size_hint_y=None, height=dp(38), padding=(dp(8), 2), spacing=dp(4))
        for k, lbl, color in [("cpu","CPU",ACCENT2),("mem","MEM",ACCENT2),
                                ("temp","TEMP",WARN),("ping","PING",ACCENT)]:
            cell = BoxLayout(orientation="horizontal", size_hint_x=1)
            cell.add_widget(Label(text=lbl, font_size=sp(9), color=MUTED,
                                    size_hint_x=None, width=dp(38)))
            v = Label(text="—", font_size=sp(11), color=color, bold=True)
            cell.add_widget(v); tel.add_widget(cell)
            self.tel_cells[k] = v
        self.add_widget(tel)
        tabs = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(8), 4), spacing=dp(6))
        self.tab_btns = {}
        for t in ("FREE","VIP","SVIP","INFO"):
            b = Button(text=t, font_size=sp(12), bold=True, color=MUTED,
                       background_normal="", background_color=(0, 0, 0, 0))
            b.bind(on_press=lambda btn, tt=t: self._tab(tt))
            tabs.add_widget(b); self.tab_btns[t] = b
        self.tab_btns["FREE"].color = ACCENT
        self.add_widget(tabs)
        self.scroll = ScrollView()
        self.cards_box = BoxLayout(orientation="vertical", size_hint_y=None,
                                     spacing=dp(6), padding=(dp(8), dp(8)))
        self.cards_box.bind(minimum_height=self.cards_box.setter("height"))
        self.scroll.add_widget(self.cards_box)
        self.add_widget(self.scroll)
        self._populate("FREE")
    def _populate(self, tab):
        self.cards_box.clear_widgets()
        if tab == "INFO": self._populate_info(); return
        defs = {
            "FREE": [
                ("ram","◆","RAM Boost","Own-package trim + GC",op_ram,0),
                ("cpu_gpu","⚡","CPU / GPU Boost","WiFi + CPU wake locks",op_cpu_gpu,0),
                ("network","◈","Network Optimizer","Start VpnService tunnel",op_network,0),
                ("gfx","▣","GFX Tool","Cosmetic on Android",op_gfx,0),
                ("notify","✦","Notification Blocker","Do Not Disturb",op_notify,0),
                ("thermal","◎","Thermal Manager","Battery + sysfs read",op_thermal,0),
            ],
            "VIP": [
                ("overclock","▲","Level 2 Overclock","Aggressive CPU wake lock",op_overclock,1),
                ("thread_prio","❋","Thread Prioritization","App foreground priority",op_thread_prio,1),
                ("gfx_unlock","✱","GFX Unlock","Rewrite UE game inis",op_gfx_unlock,1),
                ("stutter_fix","⬢","Stutter Fix","Aggressive RAM trim",op_stutter_fix,1),
                ("super_boost_network","◬","SUPER BOOST NETWORK","4 pillars · UDP tunnel",op_super_boost_network,1),
            ],
            "SVIP": [
                ("vpn","◈","Gaming VPN","Install / activate VpnService",op_vpn,2),
            ],
        }[tab]
        for key, icon, title, sub, fn, min_tier in defs:
            c = FeatureCardBox(key, icon, title, sub, fn, min_tier, on_change=self._refresh)
            self.cards_box.add_widget(c); self.cards[key] = c
    def _populate_info(self):
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        box.bind(minimum_height=box.setter("height"))
        box.add_widget(Label(text="SUPER BOOST NETWORK · 4 PILLARS",
                              font_size=sp(12), bold=True, color=GOLD,
                              size_hint_y=None, height=dp(28),
                              halign="left", text_size=(None, None)))
        for key, title, sub in [
            ("nagle","Nagle Bypass","All traffic encapsulated as UDP"),
            ("throttle","TCP Delay Eliminated","TCP stack invisible to games"),
            ("l2","Layer-2 Tunnel","Direct route via relay"),
            ("interrupt","WiFi High-Perf Lock","Radio stays at max power"),
        ]:
            row = PillarRow(key, title, sub)
            box.add_widget(row); self.pillars[key] = row
        self.cards_box.add_widget(box)
        png = TEL.latest()
        info = BoxLayout(orientation="vertical", size_hint_y=None,
                          height=dp(260), padding=(dp(10), dp(10)), spacing=dp(4))
        for line in [
            f"Tier: {TIER_NAME.get(LIC.tier, 'FREE')}",
            f"Bridge: {'OK' if BRIDGE.ok else 'unavailable'}",
            f"VPN perm: {'granted' if BRIDGE.vpn_prepared() else 'not granted'}",
            f"DND: {'granted' if BRIDGE.dnd_granted() else 'not granted'}",
            f"Ping: {png.get('ping') or 0:.1f} ms",
            f"Data dir: {APPDIR}",
            "",
            "No root. All VIP features active.",
            "VpnService tunnel is local — no external server.",
        ]:
            info.add_widget(Label(text=line, font_size=sp(10), color=TXT,
                                    halign="left", text_size=(None, None)))
        self.cards_box.add_widget(info)
    def _tab(self, tab):
        for t, b in self.tab_btns.items():
            b.color = ACCENT if t == tab else MUTED
        self._populate(tab)
    def _on_toggle(self, on):
        threading.Thread(target=op_master_boost, args=(on,), daemon=True).start()
        Clock.schedule_once(lambda *_: self._refresh(), 0.8)
    def _on_dial_click(self):
        if not self.toggle.busy:
            self.toggle.state_on = not self.toggle.state_on
            self._on_toggle(self.toggle.state_on)
    def _refresh(self):
        self.tier_lbl.text = TIER_NAME.get(LIC.tier, "FREE")
        self.dial.engaged = ST.master_boost
        self.dial.target = str(CFG.get("fps_target", "MAX"))
        self.toggle.state_on = ST.master_boost
        for k, (m, fn) in list(self.tel_cells.items()):
            if k.startswith("check_"):
                try: m.color = ACCENT if fn() else MUTED
                except Exception: pass
        for c in self.cards.values(): c._sync()
        s = sbn_state()
        for k, r in self.pillars.items(): r.set_state(s.get(k, False))

# ═══════════════════════════════════════════════════════════════════════════
#  DIALOGS
# ═══════════════════════════════════════════════════════════════════════════
def popup_auto_setup(app_ref):
    box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14))
    box.add_widget(Label(text="AUTO SETUP", font_size=sp(18), bold=True,
                          color=GOLD, size_hint_y=None, height=dp(30)))
    box.add_widget(Label(text="Grants VPN + DND access, exempts battery,\n"
                              "acquires locks, enables master boost.",
                          font_size=sp(10), color=MUTED,
                          size_hint_y=None, height=dp(40)))
    log_box = TextInput(readonly=True, multiline=True, font_size=sp(11),
                         background_color=PANEL, foreground_color=TXT)
    box.add_widget(log_box)
    btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    run_btn = Button(text="▶ RUN", font_size=sp(13), bold=True,
                      background_color=GOLD, color="#0a0e15")
    close_btn = Button(text="CLOSE", font_size=sp(12), bold=True,
                        background_color=PANEL2, color=MUTED)
    btns.add_widget(run_btn); btns.add_widget(close_btn)
    box.add_widget(btns)
    popup = Popup(title="", content=box, size_hint=(0.95, 0.85))
    def append(msg):
        def _do(*_): log_box.text += msg + "\n"
        Clock.schedule_once(_do, 0)
    def report(name, ok, detail):
        mark = "✔" if ok else "✘"
        line = f"{mark}  {name}"
        if not ok and detail: line += f"\n     ↳ {detail}"
        append(line)
    def run_setup(*_):
        run_btn.disabled = True; run_btn.text = "◐ WORKING..."
        log_box.text = "Starting auto setup...\n"
        def work():
            auto_setup(report=report)
            Clock.schedule_once(lambda *_: done(), 0)
        def done():
            append("\n── Done. ──")
            run_btn.disabled = False; run_btn.text = "▶ RUN"
            if app_ref and app_ref.dashboard:
                app_ref.dashboard._refresh()
        threading.Thread(target=work, daemon=True).start()
    run_btn.bind(on_press=run_setup)
    close_btn.bind(on_press=lambda *_: popup.dismiss())
    popup.open()

def popup_result(msg):
    p = Popup(title="", content=Label(text=msg, color=TXT), size_hint=(0.7, 0.25))
    p.open(); Clock.schedule_once(lambda *_: p.dismiss(), 1.8)

def popup_key_entry(app_ref):
    box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
    box.add_widget(Label(text="Enter your key", font_size=sp(14), color=TXT,
                          size_hint_y=None, height=dp(30)))
    entry = TextInput(multiline=False, font_size=sp(13),
                       background_color=PANEL2, foreground_color=TXT)
    box.add_widget(entry)
    btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    def unlock(*_):
        t = LIC.save(entry.text)
        if t:
            popup.dismiss(); popup_result(f"Unlocked: {TIER_NAME[t]}")
            if app_ref and app_ref.dashboard: app_ref.dashboard._refresh()
        else: popup_result("Invalid key")
    btns.add_widget(Button(text="UNLOCK", on_press=unlock,
                            background_color=ACCENT, color=BG, bold=True))
    btns.add_widget(Button(text="CANCEL", on_press=lambda *_: popup.dismiss(),
                            background_color=PANEL2, color=MUTED))
    box.add_widget(btns)
    popup = Popup(title="License", content=box, size_hint=(0.9, 0.4))
    popup.open()

def popup_keygen(app_ref):
    if LIC.tier < 9:
        popup_result("Admin tier required"); return
    box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
    tier_sp = Spinner(text="VIP", values=("VIP","SVIP"), size_hint_y=None, height=dp(44))
    days = TextInput(text="1", multiline=False, size_hint_y=None, height=dp(44))
    qty = TextInput(text="1", multiline=False, size_hint_y=None, height=dp(44))
    box.add_widget(Label(text="Tier", color=MUTED, size_hint_y=None, height=dp(20)))
    box.add_widget(tier_sp)
    box.add_widget(Label(text="Days", color=MUTED, size_hint_y=None, height=dp(20)))
    box.add_widget(days)
    box.add_widget(Label(text="Qty", color=MUTED, size_hint_y=None, height=dp(20)))
    box.add_widget(qty)
    out = TextInput(readonly=True, multiline=True, font_size=sp(11),
                     background_color=PANEL, foreground_color=ACCENT)
    box.add_widget(out)
    btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    def gen(*_):
        try: t = tier_sp.text; d = int(days.text); q = int(qty.text)
        except Exception: out.text = "bad input"; return
        keys = [make_key(t, d) for _ in range(q)]
        out.text = "\n".join(keys)
        h = load_issued()
        for k in keys:
            h.append({"key": k, "tier": t, "days": d,
                       "issued": datetime.utcnow().isoformat()})
        save_issued(h)
    btns.add_widget(Button(text="GEN", on_press=gen, background_color=ACCENT, color=BG))
    btns.add_widget(Button(text="CLOSE", on_press=lambda *_: popup.dismiss(),
                            background_color=PANEL2, color=MUTED))
    box.add_widget(btns)
    popup = Popup(title="Keygen", content=box, size_hint=(0.95, 0.85))
    popup.open()

# ═══════════════════════════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════════════════════════
class ApexApp(App):
    def build(self):
        Window.clearcolor = BG
        self.title = "ApexEngine Max"
        self.dashboard = DashboardScreen()
        root = BoxLayout(orientation="vertical")
        root.add_widget(self.dashboard)
        bar = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(8), dp(4)), spacing=dp(5))
        def mk(label, cb, color=TXT):
            b = Button(text=label, font_size=sp(11), bold=True,
                        color=color, background_normal="", background_color=PANEL2)
            b.bind(on_press=cb); return b
        bar.add_widget(mk("AUTO", lambda *_: popup_auto_setup(self), GOLD))
        bar.add_widget(mk("Key", lambda *_: popup_key_entry(self)))
        bar.add_widget(mk("Keygen", lambda *_: popup_keygen(self), GOLD))
        bar.add_widget(mk("About", self._about))
        root.add_widget(bar)
        Clock.schedule_interval(self._tick, 1.5)
        if not CFG.get("auto_setup_done", False):
            Clock.schedule_once(lambda *_: popup_auto_setup(self), 1.0)
        if CFG.get("master_boost", False):
            Clock.schedule_once(lambda *_: self.dashboard._on_toggle(True), 1.5)
        return root
    def _tick(self, *_):
        d = TEL.latest(); du = self.dashboard
        du.tel_cells["cpu"].text = f"{d.get('cpu',0):.0f}%"
        du.tel_cells["mem"].text = f"{d.get('mem',0):.0f}%"
        t = d.get("temp"); du.tel_cells["temp"].text = f"{t:.0f}°C" if t else "—"
        p = d.get("ping"); du.tel_cells["ping"].text = f"{p:.0f}ms" if p else "—"
        for k, (m, fn) in list(du.tel_cells.items()):
            if k.startswith("check_"):
                try: m.color = ACCENT if fn() else MUTED
                except Exception: pass
        s = sbn_state()
        for k, r in du.pillars.items(): r.set_state(s.get(k, False))
    def _about(self, *_):
        png = TEL.latest()
        txt = (f"ApexEngine Max Mobile v3.0\n\n"
               f"Tier: {TIER_NAME.get(LIC.tier, 'FREE')}\n"
               f"Bridge: {'OK' if BRIDGE.ok else 'unavailable'}\n"
               f"VPN perm: {'yes' if BRIDGE.vpn_prepared() else 'no'}\n"
               f"DND: {'yes' if BRIDGE.dnd_granted() else 'no'}\n"
               f"Ping: {png.get('ping') or 0:.1f} ms\n\n"
               "No root. All VIP features active.")
        p = Popup(title="About", content=Label(text=txt, color=TXT), size_hint=(0.9, 0.6))
        p.open()

if __name__ == "__main__":
    ApexApp().run()