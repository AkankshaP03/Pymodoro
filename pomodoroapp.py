import pygame
import sys
import csv
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from time import time

pygame.init()

# ---------------- Paths ----------------
ROOT = Path(__file__).parent
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)
ASSETS = ROOT / "assets"
SOUNDS = ASSETS / "sounds"
CONFIG_FILE = DATA / "config.json"
COUNTERS_FILE = DATA / "counters.csv"
TASKS_FILE = DATA / "tasks.json"

# ---------------- Fonts ----------------
def sysfont(names, size, bold=False):
    """
    Create a pygame SysFont with fallbacks.
    Parameters:
    - names (list or str): preferred font name(s)
    - size (int): font size in pixels
    - bold (bool): bold flag
    Returns:
    - pygame.font.Font: created system font
    """
    return pygame.font.SysFont(names, size, bold=bold)

FONT_BIG = sysfont(["Inter","SF Pro Display","Segoe UI","Arial"], 112, bold=True)
FONT_MED = sysfont(["Inter","Segoe UI","Arial"], 20)
FONT_UI = sysfont(["Inter","Segoe UI","Arial"], 16)
FONT_TITLE = sysfont(["Helvetica"], 28, bold=True)

# ---------------- Colors ----------------
BG = (250, 250, 252)  # main background
INK = (36, 38, 43)    # primary text
MUTED = (118, 122, 128)  # secondary text
ACCENT = (56, 120, 255)  # primary accent
ACCENT_DARK = (37, 99, 235)
RESET_RED = (220, 90, 90)
RESET_RED_DARK = (200, 60, 60)
HOVER = (244, 246, 250)   # subtle hover
CARD = (250, 250, 251)    # slightly off-white card
BORDER = (225, 228, 233)  # soft border
RING_TRACK = (237, 240, 242)
RING_WORK = (64, 222, 154)
RING_SBREAK = (255, 204, 92)
RING_LBREAK = (255, 110, 110)

# ---------------- Layout ----------------
WIDTH, HEIGHT = 1200, 720
PADDING = 24
GAP = 20
CHIP_H = 38
TITLE_H = 56
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pomodoro Timer ⏰")
CLOCK = pygame.time.Clock()
FPS = 60

# ---------------- Ring visuals ----------------
RING_THICKNESS = 14
RING_STEPS = 360

# ---------------- Models ----------------
@dataclass
class Config:
    """
    Application configuration settings.

    Attributes:
    - focus_level (str): "Traditional" or "Custom" set of durations.
    - pomodoro_min (int): Default pomodoro minutes for Traditional mode.
    - short_min (int): Default short break minutes for Traditional mode.
    - long_min (int): Default long break minutes for Traditional mode.
    - custom_pomodoro_min (int): Custom pomodoro minutes for Custom mode.
    - custom_short_min (int): Custom short break minutes for Custom mode.
    - custom_long_min (int): Custom long break minutes for Custom mode.
    - auto_start_pomodoros (bool): Auto-start focus after breaks.
    - auto_start_breaks (bool): Auto-start breaks after focus.
    - alarm_index (int): Index into available alarm sounds.
    - mute (bool): True to mute alarms.
    - long_break_every (int): After how many pomodoros to take a long break.
    """
    focus_level: str = "Traditional"  # "Traditional" | "Custom"
    pomodoro_min: int = 25
    short_min: int = 5
    long_min: int = 15
    custom_pomodoro_min: int = 25
    custom_short_min: int = 5
    custom_long_min: int = 15
    auto_start_pomodoros: bool = False
    auto_start_breaks: bool = False
    alarm_index: int = 0
    mute: bool = False
    long_break_every: int = 4

@dataclass
class Counters:
    """
    Day/session counters.

    Attributes:
    - pomodoros (int): Completed pomodoro sessions.
    - short_breaks (int): Completed short breaks.
    - long_breaks (int): Completed long breaks.
    """
    pomodoros: int = 0
    short_breaks: int = 0
    long_breaks: int = 0

# ---------------- Persistence ----------------
def load_config() -> Config:
    """
    Load configuration from CONFIG_FILE.

    Returns:
    - Config: Loaded configuration, or defaults on error/missing file.
    """
    try:
        if CONFIG_FILE.exists():
            return Config(**json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return Config()

def save_config(cfg: Config):
    """
    Save configuration to CONFIG_FILE.

    Parameters:
    - cfg (Config): Configuration to persist.
    """
    try:
        CONFIG_FILE.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
    except Exception:
        pass

def load_counters() -> Counters:
    """
    Load the last counters entry from COUNTERS_FILE (CSV).

    Returns:
    - Counters: Counters from last row, or defaults if not found/failed.
    """
    try:
        if COUNTERS_FILE.exists():
            with COUNTERS_FILE.open("r", newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                rows = list(r)
                if rows:
                    row = rows[-1]
                    return Counters(
                        pomodoros=int(row.get("pomodoros", 0)),
                        short_breaks=int(row.get("short_breaks", 0)),
                        long_breaks=int(row.get("long_breaks", 0)),
                    )
    except Exception:
        pass
    return Counters()

def save_counters(cnt: Counters):
    """
    Append counters as a row to COUNTERS_FILE.

    Parameters:
    - cnt (Counters): Counters snapshot to append.
    """
    try:
        write_header = not COUNTERS_FILE.exists()
        with COUNTERS_FILE.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["pomodoros","short_breaks","long_breaks"])
            if write_header:
                w.writeheader()
            w.writerow(asdict(cnt))
    except Exception:
        pass

def load_tasks():
    """
    Load tasks model from TASKS_FILE.

    Returns:
    - dict: Model with keys "tasks" (list) and "hide_completed" (bool).
    """
    try:
        if TASKS_FILE.exists():
            return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"tasks": [], "hide_completed": False}

def save_tasks(model):
    """
    Persist tasks model to TASKS_FILE.

    Parameters:
    - model (dict): Tasks model to save.
    """
    try:
        TASKS_FILE.write_text(json.dumps(model, indent=2), encoding="utf-8")
    except Exception:
        pass

def _sanitized_tasks_model(model):
    out = {"tasks": [], "hide_completed": model.get("hide_completed", False)}
    for t in model.get("tasks", []):
        clean = {k: v for k, v in t.items() if not (isinstance(k, str) and k.startswith("_"))}
        out["tasks"].append(clean)
    return out

# ---------------- Sounds ----------------
def init_mixer():
    try:
        pygame.mixer.init()
        return True
    except Exception:
        return False

ALARM_PATHS = [SOUNDS / "argon.mp3", SOUNDS / "echime.mp3", SOUNDS / "chime.mp3"]
ALARMS = [None, None, None]
if init_mixer():
    for i, p in enumerate(ALARM_PATHS):
        try:
            if p.exists():
                ALARMS[i] = pygame.mixer.Sound(str(p))
        except Exception:
            ALARMS[i] = None

def play_alarm(cfg: Config):
    if cfg.mute: return
    snd = ALARMS[cfg.alarm_index % len(ALARMS)]
    if snd:
        try: snd.play()
        except Exception: pass

def pre_play_alarm(alarm_index):
    snd = ALARMS[alarm_index % len(ALARMS)]
    if snd:
        try: snd.play()
        except Exception: pass

# ---------------- Timer engine ----------------
class TimerEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.mode = "Pomodoro"  # "Pomodoro" | "Short Break" | "Long Break"
        self.running = False
        self.remaining = self._mode_seconds()
        self.cycle_done = 0

    def _triplet(self):
        if self.cfg.focus_level == "Traditional":
            return (self.cfg.pomodoro_min, self.cfg.short_min, self.cfg.long_min)
        return (self.cfg.custom_pomodoro_min, self.cfg.custom_short_min, self.cfg.custom_long_min)

    def _mode_seconds(self):
        p, s, l = self._triplet()
        return (p if self.mode=="Pomodoro" else s if self.mode=="Short Break" else l) * 60

    def set_mode(self, m: str):
        self.mode = m
        self.running = False
        self.remaining = self._mode_seconds()

    def start(self): self.running = True
    def pause(self): self.running = False

    def stop(self):
        self.running = False
        self.remaining = self._mode_seconds()

    def skip_to_pomodoro(self):
        self.mode = "Pomodoro"
        self.remaining = self._mode_seconds()
        self.running = True

    def skip_to_break(self):
        next_is_long = (self.cycle_done + 1) % self.cfg.long_break_every == 0
        self.mode = "Long Break" if next_is_long else "Short Break"
        self.remaining = self._mode_seconds()
        self.running = True

    def tick(self, dt_sec: float) -> bool:
        if not self.running: return False
        self.remaining -= dt_sec
        if self.remaining <= 0:
            self.remaining = 0
            self.running = False
            return True
        return False

    def on_complete(self, counters: Counters):
        if self.mode == "Pomodoro":
            counters.pomodoros += 1
            self.cycle_done += 1
            if self.cfg.auto_start_breaks:
                self.skip_to_break()
            else:
                next_is_long = (self.cycle_done) % self.cfg.long_break_every == 0
                self.mode = "Long Break" if next_is_long else "Short Break"
                self.remaining = self._mode_seconds()
        elif self.mode == "Short Break":
            counters.short_breaks += 1
            self.mode = "Pomodoro"; self.remaining = self._mode_seconds()
            if self.cfg.auto_start_pomodoros: self.running = True
        else:
            counters.long_breaks += 1
            self.cycle_done = 0
            self.mode = "Pomodoro"; self.remaining = self._mode_seconds()
            if self.cfg.auto_start_pomodoros: self.running = True

# ---------------- Rect button ----------------
class RectButton:
    def __init__(self, rect, label, font, bg=(255,255,255), fg=INK, border=BORDER):
        self.rect = pygame.Rect(rect); self.label = label
        self.font = font; self.bg = bg; self.fg = fg; self.border = border
        self.press_anim = 0.0

    def draw(self, surf, hover=False, dt=0.0):
        color = self.bg if not hover else HOVER
        scale = 1.0
        if self.press_anim > 0:
            scale = 1.0 - 0.06 * self.press_anim
            self.press_anim = max(0.0, self.press_anim - dt * 6.0)
        if scale != 1.0:
            w, h = int(self.rect.width * scale), int(self.rect.height * scale)
            r = pygame.Rect(0,0,w,h); r.center = self.rect.center
            pygame.draw.rect(surf, color, r, border_radius=10)
            pygame.draw.rect(surf, self.border, r, width=1, border_radius=10)
            txt = self.font.render(self.label, True, self.fg)
            surf.blit(txt, txt.get_rect(center=r.center))
        else:
            pygame.draw.rect(surf, color, self.rect, border_radius=10)
            pygame.draw.rect(surf, self.border, self.rect, width=1, border_radius=10)
            txt = self.font.render(self.label, True, self.fg)
            surf.blit(txt, txt.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)

# ---------------- UI helpers ----------------
def fmt_time(sec: float):
    s = max(0, int(sec)); return f"{s//60:02d}:{s%60:02d}"

def draw_ring(surf, center, radius, progress, color):
    pygame.draw.circle(surf, RING_TRACK, center, radius, RING_THICKNESS)
    if progress <= 0:
        return
    rect = pygame.Rect(0,0,radius*2, radius*2); rect.center = center
    start = -math.pi/2
    end = start + max(0.0, min(1.0, progress)) * 2 * math.pi
    try:
        pygame.draw.arc(surf, color, rect, start, end, RING_THICKNESS)
    except Exception:
        steps = max(1, int(RING_STEPS * progress))
        for i in range(steps):
            a0 = start + (end - start) * (i/steps)
            a1 = start + (end - start) * ((i+1)/steps)
            pygame.draw.arc(surf, color, rect, a0, a1, RING_THICKNESS)

def ring_color(mode):
    return RING_WORK if mode=="Pomodoro" else (RING_SBREAK if mode=="Short Break" else RING_LBREAK)

# ---------------- Visual helpers ----------------
def draw_shadow(rect: pygame.Rect, offset=(4,4), radius=10, alpha=60):
    shadow = rect.inflate(12, 12).move(offset)
    srf = pygame.Surface(shadow.size, pygame.SRCALPHA)
    SCREEN.blit(srf, shadow.topleft)

def draw_background():
    top = BG
    bottom = (230, 230, 234)
    for i in range(HEIGHT):
        t = i / max(1, HEIGHT - 1)
        col = (
            int(top[0] * (1-t) + bottom[0] * t),
            int(top[1] * (1-t) + bottom[1] * t),
            int(top[2] * (1-t) + bottom[2] * t),
        )
        pygame.draw.line(SCREEN, col, (0, i), (WIDTH, i))

# ---------------- Init runtime ----------------
cfg = load_config()
cnt = load_counters()
tasks_model = load_tasks()
engine = TimerEngine(cfg)

# Layout split
left_w = int(WIDTH * 0.64)
right_w = WIDTH - left_w - (PADDING * 3)
LEFT = pygame.Rect(PADDING, TITLE_H, left_w, HEIGHT - TITLE_H - PADDING)
RIGHT = pygame.Rect(PADDING*2 + left_w, TITLE_H, right_w, HEIGHT - TITLE_H - PADDING)

# Top chips and controls
row_y = LEFT.y + 8
chip_w = (LEFT.width - GAP*2) // 3
chips = [
    RectButton(pygame.Rect(LEFT.x, row_y, chip_w, CHIP_H), "Pomodoro", FONT_MED),
    RectButton(pygame.Rect(LEFT.x + chip_w + GAP, row_y, chip_w, CHIP_H), "Short Break", FONT_MED),
    RectButton(pygame.Rect(LEFT.x + 2*(chip_w + GAP), row_y, chip_w, CHIP_H), "Long Break", FONT_MED),
]
row_y2 = row_y + CHIP_H + 18
start_btn = RectButton(pygame.Rect(0,0,260,44), "Start / Pause (Space)", FONT_MED, bg=(240,245,255))
start_btn.rect.center = (LEFT.centerx, row_y2 + 28)
row_y4 = start_btn.rect.bottom + 16
stop_btn = RectButton(pygame.Rect(0,0,200,36), "Stop (reset current)", FONT_UI)
stop_btn.rect.center = (LEFT.centerx, row_y4 + 18)

# Customize dropdown states
cust_menu_open = False
cust_menu_rect = None
cust_btn_rect = None
__cust_items = []
cust_flyout_open = None
cust_flyout_rect = None
__cust_fly_items = []
_show_custom_panel = False

# Reset session UI state
reset_btn_rect = None
reset_confirm_open = False
reset_confirm_items = []

# Tasks panel states
add_rect = pygame.Rect(RIGHT.x + 14, RIGHT.y + 44, RIGHT.width - 28, 38)
adding_task = False
new_task = ""
caret_timer = 0.0
caret_vis = True
tasks_menu_open = False
tasks_menu_rect = None
dots_rect = None
ui_task_rows = []
tasks_menu_items = []

# Subtitle under digits
custom_subtitle = ""
editing_title = False
title_text = ""

# ---------------- Draw routines ----------------
def draw_title_bar():
    global cust_btn_rect, reset_btn_rect
    pygame.draw.rect(SCREEN, (15,58,99), pygame.Rect(0,0,WIDTH,TITLE_H))
    t = FONT_TITLE.render("PyModoro", True, (244,246,249))
    SCREEN.blit(t, (16, (TITLE_H - t.get_height())//2))
    label = "Customize"
    pill_w, pill_h = 110, 32
    cust_btn_rect = pygame.Rect(WIDTH - pill_w - 16, (TITLE_H - pill_h)//2, pill_w, pill_h)
    hovered = cust_btn_rect.collidepoint(pygame.mouse.get_pos())
    col = ACCENT if not hovered else ACCENT_DARK
    pygame.draw.rect(SCREEN, col, cust_btn_rect, border_radius=18)
    inner = cust_btn_rect.inflate(-6, -6)
    inner_s = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
    pygame.draw.rect(inner_s, (255,255,255,24), inner_s.get_rect(), border_radius=14)
    SCREEN.blit(inner_s, inner.topleft)
    txt = FONT_UI.render(label, True, (255,255,255))
    SCREEN.blit(txt, txt.get_rect(center=cust_btn_rect.center))
    r_w, r_h = 140, 32
    reset_btn_rect = pygame.Rect(cust_btn_rect.left - 8 - r_w, (TITLE_H - r_h)//2, r_w, r_h)
    hovered_r = reset_btn_rect.collidepoint(pygame.mouse.get_pos())
    colr = RESET_RED if not hovered_r else RESET_RED_DARK
    pygame.draw.rect(SCREEN, colr, reset_btn_rect, border_radius=16)
    txt2 = FONT_UI.render("Reset Session", True, (255,255,255))
    SCREEN.blit(txt2, txt2.get_rect(center=reset_btn_rect.center))

def draw_customize_menu(mouse):
    global cust_menu_rect, __cust_items, reset_confirm_open
    __cust_items = []
    if not cust_menu_open or reset_confirm_open:
        cust_menu_rect = None
        return
    w, row_h, pad = 220, 36, 8
    rows = [("Focus Level", "focus"), ("Auto Start", "auto"), ("Alarm", "alarm"), ("Quick Actions", "quick")]
    height = pad + len(rows)*row_h + pad
    x = (WIDTH - w) // 2
    y = (HEIGHT - height) // 2 - 40
    cust_menu_rect = pygame.Rect(x, y, w, height)
    draw_shadow(cust_menu_rect, offset=(2,4), radius=10, alpha=60)
    pygame.draw.rect(SCREEN, (255,255,255), cust_menu_rect, border_radius=8)
    pygame.draw.rect(SCREEN, BORDER, cust_menu_rect, width=1, border_radius=8)
    y_cursor = cust_menu_rect.y + pad
    for label, key in rows:
        r = pygame.Rect(cust_menu_rect.x + 8, y_cursor, cust_menu_rect.width - 16, row_h)
        if r.collidepoint(mouse): pygame.draw.rect(SCREEN, HOVER, r, border_radius=6)
        SCREEN.blit(FONT_UI.render(label, True, INK), (r.x + 10, r.y + 8))
        __cust_items.append((r, key))
        y_cursor += row_h

def draw_reset_confirm(mouse):
    global reset_confirm_items
    reset_confirm_items = []
    if not reset_confirm_open:
        return
    w, h = 420, 140
    rect = pygame.Rect((WIDTH - w)//2, (HEIGHT - h)//2 - 20, w, h)
    draw_shadow(rect, offset=(2,4), radius=10, alpha=60)
    pygame.draw.rect(SCREEN, (255,255,255), rect, border_radius=8)
    pygame.draw.rect(SCREEN, BORDER, rect, width=1, border_radius=8)
    msg1 = FONT_MED.render("Reset session to defaults?", True, INK)
    msg2 = FONT_MED.render("This will reset timers and counts.", True, INK)
    SCREEN.blit(msg1, (rect.x + 16, rect.y + 18))
    SCREEN.blit(msg2, (rect.x + 16, rect.y + 48))
    btn_w, btn_h = 120, 36
    yes = pygame.Rect(rect.centerx - btn_w - 8, rect.bottom - 12 - btn_h, btn_w, btn_h)
    no  = pygame.Rect(rect.centerx + 8, rect.bottom - 12 - btn_h, btn_w, btn_h)
    for rr, label in ((yes, "Yes"), (no, "No")):
        if rr.collidepoint(mouse): pygame.draw.rect(SCREEN, HOVER, rr, border_radius=8)
        pygame.draw.rect(SCREEN, BORDER, rr, width=1, border_radius=8)
        SCREEN.blit(FONT_UI.render(label, True, INK), (rr.centerx - 12, rr.y + 8))
        reset_confirm_items.append((rr, label))

def draw_customize_flyout(mouse):
    global cust_flyout_rect, __cust_fly_items
    __cust_fly_items = []
    if not cust_menu_open or not cust_flyout_open or not cust_menu_rect:
        cust_flyout_rect = None
        return

    def build_sections():
        if cust_flyout_open == "focus":
            return [("Traditional Timer","focus_trad"),("Customise Timer","focus_custom_panel")], 260
        if cust_flyout_open == "auto":
            return [
                (f"Auto-start Pomodoros: {'On' if cfg.auto_start_pomodoros else 'Off'}","auto_pomo"),
                (f"Auto-start Breaks: {'On' if cfg.auto_start_breaks else 'Off'}","auto_break"),
            ], 260
        if cust_flyout_open == "alarm":
            return [("Argon","alarm_1"),("Chime","alarm_2"),("Celebration","alarm_3"),
                    (f"Mute: {'On' if cfg.mute else 'Off'}","mute_toggle")], 260
        return [("Skip to Break","skip_break"),("Skip to Pomodoro","skip_pomo")], 220

    sections, w = build_sections()
    h = 8 + len(sections)*36 + 8
    idx = {"focus":0,"auto":1,"alarm":2,"quick":3}[cust_flyout_open]
    anchor_y = cust_menu_rect.y + 8 + idx*36
    x = cust_menu_rect.right + 8
    y = anchor_y
    x = max(8, min(x, WIDTH - w - 8))
    y = max(TITLE_H + 4, min(y, HEIGHT - h - 8))
    cust_flyout_rect = pygame.Rect(x, y, w, h)
    draw_shadow(cust_flyout_rect, offset=(2,4), radius=10, alpha=60)
    pygame.draw.rect(SCREEN, (255,255,255), cust_flyout_rect, border_radius=8)
    pygame.draw.rect(SCREEN, BORDER, cust_flyout_rect, width=1, border_radius=8)
    y_cursor = cust_flyout_rect.y + 8
    for label, key in sections:
        r = pygame.Rect(cust_flyout_rect.x + 8, y_cursor, cust_flyout_rect.width - 16, 32)
        if r.collidepoint(mouse): pygame.draw.rect(SCREEN, HOVER, r, border_radius=6)
        SCREEN.blit(FONT_UI.render(label, True, INK), (r.x + 10, r.y + 8))
        __cust_fly_items.append((r, key))
        y_cursor += 36

    if cust_flyout_open == "focus" and _show_custom_panel:
        p, s, l = cfg.custom_pomodoro_min, cfg.custom_short_min, cfg.custom_long_min
        step_h, pad = 32, 8
        labels = [("Pomodoro","p",p), ("Short Break","s",s), ("Long Break","l",l)]
        w2 = 280; h2 = 8 + len(labels)*step_h + pad + 8
        x2 = cust_menu_rect.right + 8
        y2 = cust_flyout_rect.y
        x2 = max(8, min(x2, WIDTH - w2 - 8))
        y2 = max(TITLE_H + 4, min(y2, HEIGHT - h2 - 8))
        cust_flyout_rect.update(x2, y2, w2, h2)
        shadow = cust_flyout_rect.inflate(12,12).move(2,4)
        srf = pygame.Surface(shadow.size, pygame.SRCALPHA)
        pygame.draw.rect(srf, (0,0,0,0), srf.get_rect(), border_radius=10)
        SCREEN.blit(srf, shadow.topleft)
        pygame.draw.rect(SCREEN, (255,255,255), cust_flyout_rect, border_radius=8)
        pygame.draw.rect(SCREEN, BORDER, cust_flyout_rect, width=1, border_radius=8)
        y_cursor = cust_flyout_rect.y + 8
        __cust_fly_items = []
        for label, key_short, val in labels:
            r_label = pygame.Rect(cust_flyout_rect.x + 8, y_cursor, 150, step_h)
            SCREEN.blit(FONT_UI.render(f"{label}: {val} minutes", True, INK), (r_label.x, r_label.y + 6))
            btn_w = 28
            r_minus = pygame.Rect(cust_flyout_rect.right - 2*btn_w - 12, y_cursor, btn_w, step_h)
            r_plus  = pygame.Rect(cust_flyout_rect.right - btn_w - 8, y_cursor, btn_w, step_h)
            for rr, sym in ((r_minus,"-"), (r_plus,"+")):
                if rr.collidepoint(mouse): pygame.draw.rect(SCREEN, (246,248,252), rr, border_radius=6)
                pygame.draw.rect(SCREEN, BORDER, rr, width=1, border_radius=6)
                SCREEN.blit(FONT_UI.render(sym, True, INK), (rr.centerx - 5, rr.y + 6))
            __cust_fly_items.append((r_minus, f"dec_{key_short}"))
            __cust_fly_items.append((r_plus,  f"inc_{key_short}"))
            y_cursor += step_h

def draw_left(mouse, dt):
    for b in chips:
        is_active = (engine.mode == b.label)
        b.draw(SCREEN, b.hit(mouse) or is_active, dt)
    start_btn.draw(SCREEN, start_btn.hit(mouse), dt)
    stop_btn.draw(SCREEN, stop_btn.hit(mouse), dt)
    center = (LEFT.centerx, (stop_btn.rect.bottom + LEFT.bottom)//2 - 16)
    total = engine._mode_seconds()
    done = total - engine.remaining
    progress = max(0.0, min(1.0, done / total if total else 0.0))
    ring_r = min(LEFT.width//3 + 60, (LEFT.height - (stop_btn.rect.bottom - LEFT.y))//2 - 30)
    draw_ring(SCREEN, center, ring_r, progress, ring_color(engine.mode))
    digits = FONT_BIG.render(fmt_time(engine.remaining), True, INK)
    SCREEN.blit(digits, digits.get_rect(center=center))
    sub = title_text if editing_title else (custom_subtitle.strip() or engine.mode)
    sub_surf = FONT_MED.render(sub, True, MUTED)
    sub_y = center[1] + int(ring_r * 0.55)
    SCREEN.blit(sub_surf, sub_surf.get_rect(center=(center[0], sub_y)))
    return pygame.Rect(center[0]-280//2, center[1] + ring_r - 34, 280, 28)

def draw_right(mouse, dt):
    pygame.draw.rect(SCREEN, CARD, RIGHT, border_radius=12)
    pygame.draw.rect(SCREEN, BORDER, RIGHT, width=1, border_radius=12)
    hdr = FONT_TITLE.render("To-do Tasks", True, INK)
    SCREEN.blit(hdr, (RIGHT.x + 14, RIGHT.y + 8))
    global dots_rect, tasks_menu_rect
    dots_rect = pygame.Rect(RIGHT.right - 34, RIGHT.y + 10, 24, 24)
    pygame.draw.circle(SCREEN, (230,232,236), dots_rect.center, 12)
    for i in (-6, 0, 6): pygame.draw.circle(SCREEN, (80,84,88), (dots_rect.centerx + i, dots_rect.centery), 2)
    global tasks_menu_items
    tasks_menu_items = []
    if tasks_menu_open:
        w, h = 360, 140
        tasks_menu_rect = pygame.Rect((WIDTH - w)//2, (HEIGHT - h)//2 - 20, w, h)
        draw_shadow(tasks_menu_rect, offset=(2,4), radius=10, alpha=60)
        pygame.draw.rect(SCREEN, (255,255,255), tasks_menu_rect, border_radius=8)
        pygame.draw.rect(SCREEN, BORDER, tasks_menu_rect, width=1, border_radius=8)
        items = [
            ("Hide Completed Tasks" if not tasks_model.get("hide_completed") else "Show Completed Tasks", "hide_show"),
            ("Remove Completed Tasks", "remove_completed"),
            ("Clear All Tasks", "remove_all")
        ]
        for idx, (label, key) in enumerate(items):
            r = pygame.Rect(tasks_menu_rect.x + 12, tasks_menu_rect.y + 12 + idx*38, tasks_menu_rect.width - 24, 34)
            if r.collidepoint(mouse): pygame.draw.rect(SCREEN, HOVER, r, border_radius=6)
            SCREEN.blit(FONT_UI.render(label, True, INK), (r.x + 8, r.y + 8))
            tasks_menu_items.append((r, key))
    else:
        tasks_menu_rect = None
    pygame.draw.rect(SCREEN, (255,255,255), add_rect, border_radius=8)
    pygame.draw.rect(SCREEN, BORDER, add_rect, width=1, border_radius=8)
    global caret_timer, caret_vis
    if not adding_task:
        ph = FONT_UI.render("+ Add a task (Enter to save)", True, MUTED)
        SCREEN.blit(ph, ph.get_rect(midleft=(add_rect.x + 12, add_rect.centery)))
    else:
        txt = FONT_UI.render(new_task, True, INK)
        SCREEN.blit(txt, txt.get_rect(midleft=(add_rect.x + 12, add_rect.centery)))
        caret_timer += dt
        if caret_timer >= 0.5:
            caret_timer = 0.0; caret_vis = not caret_vis
        if caret_vis:
            cx = min(add_rect.right-12, add_rect.x + 12 + txt.get_width() + 2)
            pygame.draw.line(SCREEN, INK, (cx, add_rect.y+8), (cx, add_rect.bottom-8), 2)
    y = add_rect.bottom + 12
    row_h = 30
    ui_task_rows.clear()
    for idx, t in enumerate(tasks_model["tasks"]):
        if tasks_model.get("hide_completed") and t.get("done"): continue
        row = pygame.Rect(RIGHT.x + 14, y, RIGHT.width - 28, row_h)
        if row.collidepoint(mouse): pygame.draw.rect(SCREEN, HOVER, row, border_radius=6)
        cb = pygame.Rect(row.x + 6, row.y + 6, 18, 18)
        pygame.draw.rect(SCREEN, BORDER, cb, width=2, border_radius=4)
        if t.get("done"):
            pygame.draw.line(SCREEN, (60, 160, 90), (cb.left + 3, cb.centery), (cb.centerx, cb.bottom - 4), 3)
            pygame.draw.line(SCREEN, (60, 160, 90), (cb.centerx, cb.bottom - 4), (cb.right - 3, cb.top + 4), 3)
        color = (150,150,150) if t.get("done") else INK
        txt = FONT_UI.render(t.get("title",""), True, color)
        SCREEN.blit(txt, (cb.right + 8, row.y + (row_h - txt.get_height())//2))
        if t.get("done"):
            y_mid = row.y + row_h//2
            pygame.draw.line(SCREEN, (170,170,170), (cb.right + 6, y_mid), (row.right - 8, y_mid), 1)
        ui_task_rows.append((row, cb, idx))
        y += row_h + 6

# ---------------- Minimal music popup ----------------
SONGS = ASSETS / "songs"
_AUDIO_EXTS = {".mp3", ".ogg", ".wav"}

def _scan_songs_simple():
    try:
        if SONGS.exists():
            return [p for p in sorted(SONGS.iterdir()) if p.is_file() and p.suffix.lower() in _AUDIO_EXTS]
    except Exception:
        pass
    return []

_playlist = _scan_songs_simple()
_music_idx = 0
_music_playing = False
_music_started_ms = 0
_music_elapsed_pause = 0.0
_music_volume = 0.8
_music_total_guess = 0.0

music_popup_open = False
_music_btn = None
_music_panel = None
_music_play_rect = None
_music_next_rect = None
_music_seek_rect = None
_music_vol_rect = None

def _music_guess_length(path):
    try:
        snd = pygame.mixer.Sound(str(path))
        return float(snd.get_length())
    except Exception:
        return 0.0

def _music_set(i):
    global _music_idx, _music_started_ms, _music_elapsed_pause, _music_playing, _music_total_guess
    if not _playlist: return
    _music_idx = max(0, min(i, len(_playlist)-1))
    try:
        pygame.mixer.music.load(str(_playlist[_music_idx]))
        pygame.mixer.music.set_volume(_music_volume)
        _music_total_guess = _music_guess_length(_playlist[_music_idx])
        _music_started_ms = pygame.time.get_ticks()
        _music_elapsed_pause = 0.0
        _music_playing = False
    except Exception:
        pass

def _music_play():
    global _music_playing, _music_started_ms
    if not _playlist: return
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(_music_volume)
            _music_started_ms = pygame.time.get_ticks()
        else:
            pygame.mixer.music.unpause()
        _music_playing = True
    except Exception:
        pass

def _music_pause():
    global _music_playing, _music_elapsed_pause
    try:
        pygame.mixer.music.pause()
        _music_elapsed_pause = (pygame.time.get_ticks() - _music_started_ms) / 1000.0
        _music_playing = False
    except Exception:
        pass

def _music_toggle():
    if not _playlist: return
    if pygame.mixer.music.get_busy() and _music_playing:
        _music_pause()
    else:
        if not pygame.mixer.music.get_busy():
            _music_set(_music_idx)
        _music_play()

def _music_next():
    if not _playlist: return
    _music_set((_music_idx + 1) % len(_playlist))
    _music_play()

def _music_elapsed():
    if _music_playing:
        return _music_elapsed_pause + (pygame.time.get_ticks() - _music_started_ms)/1000.0
    return _music_elapsed_pause

def _music_seek_to(progress_01):
    if not _playlist: return
    total = _music_total_guess if _music_total_guess > 0 else 30.0
    pos = max(0.0, min(1.0, progress_01)) * total
    try:
        pygame.mixer.music.play(loops=0, start=pos)
        global _music_started_ms, _music_elapsed_pause, _music_playing
        _music_started_ms = pygame.time.get_ticks()
        _music_elapsed_pause = pos
        _music_playing = True
    except Exception:
        pass

def _music_set_volume(v):
    global _music_volume
    _music_volume = max(0.0, min(1.0, v))
    try:
        pygame.mixer.music.set_volume(_music_volume)
    except Exception:
        pass

def _fmt_mmss(sec):
    s = max(0, int(sec)); return f"{s//60:02d}:{s%60:02d}"

def _draw_music_toggle():
    global _music_btn
    w, h = 100, 32
    x = WIDTH - w - 16
    y = HEIGHT - h - 16
    _music_btn = pygame.Rect(x, y, w, h)
    hovered = _music_btn.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(SCREEN, (242,245,248) if not hovered else (235,240,246), _music_btn, border_radius=8)
    pygame.draw.rect(SCREEN, BORDER, _music_btn, 1, border_radius=8)
    lbl = "Music" if not music_popup_open else "Close"
    t = FONT_UI.render(lbl, True, INK)
    SCREEN.blit(t, t.get_rect(center=_music_btn.center))

def _draw_music_popup():
    global _music_panel, _music_play_rect, _music_next_rect, _music_seek_rect, _music_vol_rect
    if not music_popup_open:
        _music_panel = None
        _music_play_rect = None
        _music_next_rect = None
        _music_seek_rect = None
        _music_vol_rect = None
        return
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((10,12,16,140))
    SCREEN.blit(ov, (0,0))
    w, h = 520, 200
    _music_panel = pygame.Rect((WIDTH - w)//2, (HEIGHT - h)//2, w, h)
    pygame.draw.rect(SCREEN, (255,255,255), _music_panel, border_radius=12)
    pygame.draw.rect(SCREEN, BORDER, _music_panel, 1, border_radius=12)
    SCREEN.blit(FONT_MED.render("Music", True, INK), (_music_panel.x + 16, _music_panel.y + 14))
    track = "(No songs)" if not _playlist else _playlist[_music_idx].stem
    SCREEN.blit(FONT_MED.render(track, True, INK if _playlist else MUTED), (_music_panel.x + 16, _music_panel.y + 48))
    y = _music_panel.y + 88
    _music_play_rect = pygame.Rect(_music_panel.x + 16, y, 100, 36)
    _music_next_rect = pygame.Rect(_music_play_rect.right + 10, y, 100, 36)
    for rr, label in ((_music_play_rect, "Play" if not _music_playing else "Pause"), (_music_next_rect, "Next")):
        hovered = rr.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(SCREEN, (242,245,248) if not hovered else (235,240,246), rr, border_radius=8)
        pygame.draw.rect(SCREEN, BORDER, rr, 1, border_radius=8)
        t = FONT_UI.render(label, True, INK)
        SCREEN.blit(t, t.get_rect(center=rr.center))
    _music_seek_rect = pygame.Rect(_music_next_rect.right + 24, y + 14, _music_panel.right - 24 - (_music_next_rect.right + 24), 8)
    pygame.draw.rect(SCREEN, (234,238,242), _music_seek_rect, border_radius=4)
    elapsed = _music_elapsed()
    total = _music_total_guess if _music_total_guess > 0 else max(elapsed, 1.0)
    prog = max(0.0, min(1.0, elapsed / total))
    fill = pygame.Rect(_music_seek_rect.x, _music_seek_rect.y, int(_music_seek_rect.width * prog), _music_seek_rect.height)
    pygame.draw.rect(SCREEN, ACCENT, fill, border_radius=4)
    tl = FONT_UI.render(_fmt_mmss(elapsed), True, MUTED)
    tr = FONT_UI.render(_fmt_mmss(total), True, MUTED)
    SCREEN.blit(tl, (_music_seek_rect.x, _music_seek_rect.y - tl.get_height() - 4))
    SCREEN.blit(tr, (_music_seek_rect.right - tr.get_width(), _music_seek_rect.y - tr.get_height() - 4))
    vy = _music_panel.bottom - 36
    SCREEN.blit(FONT_UI.render("Vol", True, MUTED), (_music_panel.x + 16, vy - 8))
    _music_vol_rect = pygame.Rect(_music_panel.x + 52, vy, _music_panel.width - 68, 6)
    pygame.draw.rect(SCREEN, (234,238,242), _music_vol_rect, border_radius=3)
    kx = _music_vol_rect.x + int(_music_volume * _music_vol_rect.width)
    pygame.draw.circle(SCREEN, ACCENT, (kx, _music_vol_rect.centery), 7)

if _playlist:
    _music_set(0)

# ---------------- Input handlers ----------------
def handle_mouse(pos):
    global adding_task, new_task, editing_title, title_text
    global tasks_menu_open, cust_menu_open, cust_flyout_open, _show_custom_panel
    global reset_confirm_open, music_popup_open

    if cust_btn_rect and cust_btn_rect.collidepoint(pos):
        cust_menu_open = not cust_menu_open
        if not cust_menu_open:
            cust_flyout_open = None; _show_custom_panel = False
        return

    if reset_btn_rect and reset_btn_rect.collidepoint(pos):
        reset_confirm_open = True
        cust_menu_open = False
        cust_flyout_open = None
        _show_custom_panel = False
        tasks_menu_open = False
        return

    if reset_confirm_open:
        w, h = 420, 140
        rect = pygame.Rect((WIDTH - w)//2, (HEIGHT - h)//2 - 20, w, h)
        if rect.collidepoint(pos):
            for r, key in reset_confirm_items:
                if r.collidepoint(pos):
                    if key == "Yes":
                        _do_reset_session()
                        reset_confirm_open = False
                        return
                    else:
                        reset_confirm_open = False
                        return
        else:
            reset_confirm_open = False
            return

    if cust_menu_open and cust_menu_rect and cust_menu_rect.collidepoint(pos):
        for r, key in __cust_items:
            if r.collidepoint(pos):
                cust_flyout_open = key
                _show_custom_panel = False
                return

    if cust_menu_open and cust_flyout_open and cust_flyout_rect and cust_flyout_rect.collidepoint(pos):
        for r, key in __cust_fly_items:
            if r.collidepoint(pos):
                if key == "focus_trad":
                    cfg.focus_level = "Traditional"; save_config(cfg); engine.set_mode(engine.mode)
                    _show_custom_panel = False
                elif key == "focus_custom_panel":
                    cfg.focus_level = "Custom"; save_config(cfg); _show_custom_panel = True; engine.set_mode(engine.mode)
                elif key == "auto_pomo":
                    cfg.auto_start_pomodoros = not cfg.auto_start_pomodoros; save_config(cfg)
                elif key == "auto_break":
                    cfg.auto_start_breaks = not cfg.auto_start_breaks; save_config(cfg)
                elif key == "alarm_1":
                    pre_play_alarm(0); cfg.alarm_index = 0; save_config(cfg)
                elif key == "alarm_2":
                    pre_play_alarm(1); cfg.alarm_index = 1; save_config(cfg)
                elif key == "alarm_3":
                    pre_play_alarm(2); cfg.alarm_index = 2; save_config(cfg)
                elif key == "mute_toggle":
                    cfg.mute = not cfg.mute; save_config(cfg)
                elif key == "skip_break":
                    engine.skip_to_break()
                elif key == "skip_pomo":
                    engine.skip_to_pomodoro()
                elif key == "dec_p":
                    cfg.focus_level = "Custom"
                    cfg.custom_pomodoro_min = max(1, cfg.custom_pomodoro_min - 1); save_config(cfg); engine.set_mode(engine.mode)
                elif key == "inc_p":
                    cfg.focus_level = "Custom"
                    cfg.custom_pomodoro_min = min(100, cfg.custom_pomodoro_min + 1); save_config(cfg); engine.set_mode(engine.mode)
                elif key == "dec_s":
                    cfg.focus_level = "Custom"
                    cfg.custom_short_min = max(1, cfg.custom_short_min - 1); save_config(cfg); engine.set_mode(engine.mode)
                elif key == "inc_s":
                    cfg.focus_level = "Custom"
                    cfg.custom_short_min = min(100, cfg.custom_short_min + 1); save_config(cfg); engine.set_mode(engine.mode)
                elif key == "dec_l":
                    cfg.focus_level = "Custom"
                    cfg.custom_long_min = max(1, cfg.custom_long_min - 1); save_config(cfg); engine.set_mode(engine.mode)
                elif key == "inc_l":
                    cfg.focus_level = "Custom"
                    cfg.custom_long_min = min(100, cfg.custom_long_min + 1); save_config(cfg); engine.set_mode(engine.mode)
                return

    if cust_menu_open and not (cust_menu_rect and cust_menu_rect.collidepoint(pos)) and not (cust_flyout_rect and cust_flyout_rect.collidepoint(pos)):
        cust_menu_open = False; cust_flyout_open = None; _show_custom_panel = False

    if chips[0].hit(pos) and not engine.running:
        chips[0].press_anim = 1.0; engine.set_mode("Pomodoro")
    elif chips[1].hit(pos) and not engine.running:
        chips[1].press_anim = 1.0; engine.set_mode("Short Break")
    elif chips[2].hit(pos) and not engine.running:
        chips[2].press_anim = 1.0; engine.set_mode("Long Break")
    elif start_btn.hit(pos):
        start_btn.press_anim = 1.0
        engine.running = not engine.running
        if engine.running and engine.remaining <= 0:
            engine.remaining = engine._mode_seconds()
    elif stop_btn.hit(pos):
        stop_btn.press_anim = 1.0
        engine.stop()

    center = (LEFT.centerx, (stop_btn.rect.bottom + LEFT.bottom)//2 - 16)
    ring_r = min(LEFT.width//3 + 60, (LEFT.height - (stop_btn.rect.bottom - LEFT.y))//2 - 30)
    sub_rect = pygame.Rect(center[0]-280//2, center[1] + ring_r - 34, 280, 28)
    if sub_rect.collidepoint(pos):
        global editing_title, title_text
        editing_title = True; title_text = custom_subtitle

    if dots_rect and dots_rect.collidepoint(pos):
        tasks_menu_open = not tasks_menu_open
        return

    if tasks_menu_open:
        if tasks_menu_rect and tasks_menu_rect.collidepoint(pos):
            for r, key in tasks_menu_items:
                if r.collidepoint(pos):
                    if key == "hide_show":
                        tasks_model["hide_completed"] = not tasks_model.get("hide_completed", False)
                        save_tasks(_sanitized_tasks_model(tasks_model))
                    elif key == "remove_completed":
                        tasks_model["tasks"] = [t for t in tasks_model["tasks"] if not t.get("done")]
                        save_tasks(_sanitized_tasks_model(tasks_model))
                    elif key == "remove_all":
                        tasks_model["tasks"].clear()
                        save_tasks(_sanitized_tasks_model(tasks_model))
                    tasks_menu_open = False
                    return
        else:
            tasks_menu_open = False

    if add_rect.collidepoint(pos):
        adding_task = True; new_task = ""

    for row, cb, idx in ui_task_rows:
        if cb and cb.collidepoint(pos):
            tasks_model["tasks"][idx]["done"] = not tasks_model["tasks"][idx].get("done", False)
            save_tasks(_sanitized_tasks_model(tasks_model))
            break

    # Music interactions
    if _music_btn and _music_btn.collidepoint(pos):
        music_popup_open = not music_popup_open
        return

    if music_popup_open:
        if _music_panel and not _music_panel.collidepoint(pos):
            music_popup_open = False
            return
        if _music_play_rect and _music_play_rect.collidepoint(pos):
            _music_toggle()
            return
        if _music_next_rect and _music_next_rect.collidepoint(pos):
            _music_next()
            return
        if _music_seek_rect and _music_seek_rect.collidepoint(pos):
            progress = (pos[0] - _music_seek_rect.x) / max(1, _music_seek_rect.width)
            _music_seek_to(progress)
            return
        if _music_vol_rect and _music_vol_rect.collidepoint(pos):
            vol = (pos[0] - _music_vol_rect.x) / max(1, _music_vol_rect.width)
            _music_set_volume(max(0.0, min(1.0, vol)))
            return

def handle_keydown(ev):
    global adding_task, new_task, editing_title, title_text, music_popup_open
    if ev.key == pygame.K_SPACE:
        engine.running = not engine.running
        if engine.running and engine.remaining <= 0:
            engine.remaining = engine._mode_seconds()
    if adding_task:
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if new_task.strip():
                tasks_model["tasks"].append({"title": new_task.strip(), "done": False})
                save_tasks(_sanitized_tasks_model(tasks_model))
            adding_task = False; new_task = ""
        elif ev.key == pygame.K_BACKSPACE:
            new_task = new_task[:-1]
        else:
            if ev.unicode and ev.unicode.isprintable():
                new_task += ev.unicode
    if editing_title:
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            globals()["custom_subtitle"] = title_text.strip()
            editing_title = False
        elif ev.key == pygame.K_BACKSPACE:
            title_text = title_text[:-1]
        else:
            if ev.unicode and ev.unicode.isprintable():
                title_text += ev.unicode
    # Music shortcuts
    if ev.key == pygame.K_m:
        music_popup_open = not music_popup_open
    elif ev.key == pygame.K_SLASH:
        _music_toggle()
    elif ev.key == pygame.K_PERIOD:
        _music_next()

def _overwrite_counters(cnt_obj: Counters):
    try:
        write_header = not COUNTERS_FILE.exists()
        with COUNTERS_FILE.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["pomodoros","short_breaks","long_breaks"])
            if write_header:
                w.writeheader()
            w.writerow(asdict(cnt_obj))
    except Exception:
        pass

def _do_reset_session():
    global cfg, cnt, engine, custom_subtitle, tasks_model
    cfg = Config()
    save_config(cfg)
    cnt = Counters()
    _overwrite_counters(cnt)
    tasks_model = {"tasks": [], "hide_completed": False}
    save_tasks(tasks_model)
    engine = TimerEngine(cfg)
    engine.mode = "Pomodoro"
    engine.remaining = engine._mode_seconds()
    custom_subtitle = ""

# ---------------- Main loop ----------------
last = time()
if _playlist:
    _music_set(0)

while True:
    now = time(); dt = now - last; last = now
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_counters(cnt)
            pygame.quit(); sys.exit()
        elif event.type == pygame.KEYDOWN:
            handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handle_mouse(event.pos)

    if engine.tick(dt):
        play_alarm(cfg)
        engine.on_complete(cnt)
        save_counters(cnt)

    if _playlist and _music_playing and not pygame.mixer.music.get_busy():
        _music_next()

    draw_background()
    draw_title_bar()

    draw_shadow(LEFT, offset=(6,6), radius=12, alpha=28)
    pygame.draw.rect(SCREEN, CARD, LEFT, border_radius=12)
    pygame.draw.rect(SCREEN, BORDER, LEFT, width=1, border_radius=12)
    draw_left(pygame.mouse.get_pos(), dt)

    draw_shadow(RIGHT, offset=(6,6), radius=12, alpha=20)
    draw_right(pygame.mouse.get_pos(), dt)

    draw_customize_menu(pygame.mouse.get_pos())
    draw_customize_flyout(pygame.mouse.get_pos())
    draw_reset_confirm(pygame.mouse.get_pos())

    foot = FONT_UI.render(f"Pomodoros: {cnt.pomodoros} Short: {cnt.short_breaks} Long: {cnt.long_breaks}", True, MUTED)
    fx = LEFT.x + (LEFT.width - foot.get_width()) // 2
    fy = HEIGHT - foot.get_height() - 8 - 28
    SCREEN.blit(foot, (fx, fy))

    _draw_music_toggle()
    _draw_music_popup()

    pygame.display.update()
    CLOCK.tick(FPS)
