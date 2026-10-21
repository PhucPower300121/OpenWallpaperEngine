# OpenWallpaperEngine.py  |  pip install opencv-python pillow imageio-ffmpeg pycaw
# Copyright (C) 2026 Mắt Thần team. Free software under GNU GPLv3: https://www.gnu.org/licenses/gpl-3.0.html
import sys, os, ctypes, subprocess, time, json
from ctypes import wintypes as wt

u32, g32, k32, mm = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.kernel32, ctypes.windll.winmm
V = ctypes.c_void_p
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
u32.FindWindowW.restype = u32.FindWindowExW.restype = u32.GetForegroundWindow.restype = u32.GetDCEx.restype = k32.GetCurrentProcess.restype = V
u32.FindWindowExW.argtypes = [V, V, wt.LPCWSTR, wt.LPCWSTR]
u32.SendMessageTimeoutW.argtypes = [V, wt.UINT, V, V, wt.UINT, wt.UINT, V]
u32.GetDCEx.argtypes = [V, V, wt.DWORD]
u32.IsWindow.argtypes = u32.IsZoomed.argtypes = [V]
u32.GetWindowRect.argtypes = [V, ctypes.POINTER(wt.RECT)]
u32.GetClassNameW.argtypes = [V, wt.LPWSTR, ctypes.c_int]
g32.SetStretchBltMode.argtypes = [V, ctypes.c_int]
g32.StretchDIBits.argtypes = [V] + [ctypes.c_int] * 8 + [V, V, wt.UINT, wt.DWORD]
k32.SetPriorityClass.argtypes = [V, wt.DWORD]

APP = "OpenWallpaperEngine"
DATA = os.path.join(os.environ["APPDATA"], APP); os.makedirs(DATA, exist_ok=True)
PIDF, FRAME, CFG, AUD, UI = (os.path.join(DATA, n) for n in ("pid", "frame.png", "cfg.json", "audio.wav", "ui.json"))
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
mci = lambda c: mm.mciSendStringW(c, None, 0, None)

class BIH(ctypes.Structure):
    _fields_ = [(n, t) for n, t in zip("s w h p b c si x y u i".split(),
        [wt.DWORD, wt.LONG, wt.LONG, wt.WORD, wt.WORD] + [wt.DWORD, wt.DWORD, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD])]

def find_workerw():
    pm = u32.FindWindowW("Progman", None)
    u32.SendMessageTimeoutW(pm, 0x052C, 0, 0, 0, 1000, None)
    res = []
    def cb(h, _):
        if u32.FindWindowExW(h, None, "SHELLDLL_DefView", None):
            w = u32.FindWindowExW(None, h, "WorkerW", None)
            if w: res.append(w)
        return True
    u32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, V, V)(cb), 0)
    return res[0] if res else (u32.FindWindowExW(pm, None, "WorkerW", None) or pm)

def get_dc():
    hw = find_workerw(); dc = u32.GetDCEx(hw, None, 0x403)
    g32.SetStretchBltMode(dc, 4)
    return hw, dc

def log(e):
    try: open(os.path.join(DATA, "err.log"), "a").write(f"{time.ctime()} {e!r}\n")
    except Exception: pass

def exe_of(pid):  # tên file exe của tiến trình
    k32.OpenProcess.restype = V; k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.QueryFullProcessImageNameW.argtypes = [V, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    k32.CloseHandle.argtypes = [V]
    h = k32.OpenProcess(0x1000, False, pid)
    if not h: return ""
    buf = ctypes.create_unicode_buffer(520); n = wt.DWORD(520)
    k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)); k32.CloseHandle(h)
    return os.path.basename(buf.value).lower()

# app DSP/mixer/ảo hóa âm thanh phát lại tiếng của mọi app -> không tính là "nguồn khác" (khớp theo chuỗi con trong tên exe)
IGNORE = ["fxsound", "voicemeeter", "voicemod", "krisp", "nvidia broadcast", "audio router", "boom3d", "voxal"]
RESUME_AFTER = 3  # số lần check (1s/lần) phải yên lặng liên tục mới phát lại
def ign(ex): return any(k in ex for k in IGNORE)

def others(pid):  # có tiến trình khác đang phát âm thanh?
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
    for s in AudioUtilities.GetAllSessions():
        if s.ProcessId and s.ProcessId != pid and not ign(exe_of(s.ProcessId)):
            try:
                if s._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue() > .002: return True
            except Exception: pass
    return False

def endpoint():  # thiết bị phát mặc định (để đọc trạng thái mute của Windows)
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    d = AudioUtilities.GetSpeakers()
    if hasattr(d, "EndpointVolume"): return d.EndpointVolume
    return d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)

def play():
    import cv2
    cfg = json.load(open(CFG)); pid = os.getpid()
    try: IGNORE.extend(l.strip().lower() for l in open(os.path.join(DATA, "ignore.txt"), encoding="utf-8") if l.strip())
    except Exception: pass  # ignore.txt (tùy chọn): mỗi dòng 1 tên exe/từ khóa cần bỏ qua
    try:  # chỉ cho 1 bản chạy: tắt bản cũ (kiểm tra đúng exe để tránh trùng PID)
        old = int(open(PIDF).read())
        if old != pid and exe_of(old) == exe_of(pid):
            subprocess.run(["taskkill", "/F", "/PID", str(old)], capture_output=True, creationflags=0x08000000)
    except Exception: pass
    open(PIDF, "w").write(str(pid))
    k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)
    sw, sh = u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)
    while not u32.FindWindowW("Progman", None): time.sleep(.5)
    time.sleep(1); hw, dc = get_dc()
    try: cap = cv2.VideoCapture(cfg["p"], cv2.CAP_ANY, [cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY])
    except Exception: cap = cv2.VideoCapture(cfg["p"])
    fps = cap.get(5) or 30; dur = cap.get(7) / fps
    s = cfg["s"]; e = min(cfg["e"] or dur, dur); L = max(e - s, .1)
    au = cfg["a"] and os.path.exists(AUD); duck = cfg["d"] and au
    kp = cfg.get("k") and au; lp = 0; skipa = False; sm = False; epv = None; quiet = 0
    if au: mci(f'open "{AUD}" type waveaudio alias a')
    bi = BIH(40, 0, 0, 1, 24, 0, 0, 0, 0, 0, 0); geo = None
    cls, r = ctypes.create_unicode_buffer(32), wt.RECT()
    t0 = time.perf_counter(); cur = 0; chk = 0; hidden = False; resync = True; muted = False
    while True:
        now = time.perf_counter()
        if now >= chk:  # mỗi 1s
            chk = now + 1
            if not u32.IsWindow(hw): hw, dc = get_dc()
            if au:  # Windows đang mute -> dừng tiếng, bỏ qua mọi kiểm tra âm thanh khác
                try:
                    if epv is None: epv = endpoint()
                    mu = bool(epv.GetMute())
                except Exception as ex: epv = None; mu = sm; log(ex)
                if mu != sm:
                    sm = mu
                    if sm: mci("pause a")
                    elif (kp or not hidden) and not muted:
                        lp = (now - t0) % L; mci(f"play a from {int(lp * 1000)}")
            if duck and not sm and (kp or not hidden):  # nguồn khác phát -> pause, hết -> phát tiếp đúng vị trí
                try: m = others(pid)
                except Exception: m = False
                quiet = 0 if m else quiet + 1
                if m and not muted or (not m and muted and quiet >= RESUME_AFTER):
                    m = muted = bool(m)
                    if m: mci("pause a")
                    elif kp or not hidden: lp = (now - t0) % L; mci(f"play a from {int(lp * 1000)}")
            fg = u32.GetForegroundWindow(); hide = False
            if fg:
                u32.GetClassNameW(fg, cls, 32)
                if cls.value not in ("Progman", "WorkerW", "Shell_TrayWnd") and u32.GetWindowRect(fg, ctypes.byref(r)):
                    hide = r.left < sw // 2 < r.right and r.top < sh // 2 < r.bottom and (
                        u32.IsZoomed(fg) or (r.right - r.left >= sw and r.bottom - r.top >= sh))
            if hide:  # bị che: dừng vẽ; tiếng tùy chọn giữ
                if not hidden:
                    hidden = True; lp = (now - t0) % L
                    if au and not kp: mci("pause a")
                if kp:
                    p = (now - t0) % L
                    if p < lp and not sm and not muted: mci(f"play a from {int(p * 1000)}")  # hết vòng -> lặp tiếng
                    lp = p
                time.sleep(.5); chk = 0; continue
            if hidden: hidden = False; resync = True; skipa = kp and not sm and not muted  # tiếng đang chạy, chỉ seek hình
        pos = (now - t0) % L; fi = int((s + pos) * fps)
        if resync or fi < cur - 1 or fi - cur > 30:  # seek: resume / lặp / quá trễ
            cap.set(1, fi); cur = fi; resync = False
            if au and not skipa and not sm and not muted: mci(f"play a from {int(pos * 1000)}")
            skipa = False
        if fi < cur:  # frame này đã vẽ, chờ frame kế
            time.sleep(max(.001, cur / fps - s - pos)); continue
        while cur < fi: cap.grab(); cur += 1  # bỏ frame trễ, không giải mã màu
        ok = cap.grab(); cur += 1
        if not ok: resync = True; t0 = time.perf_counter(); continue
        ok, f = cap.retrieve()
        if not ok: continue
        h, w = f.shape[:2]
        if w & 3: f = cv2.copyMakeBorder(f, 0, 0, 0, 4 - (w & 3), cv2.BORDER_CONSTANT)
        if geo != (w, h):
            k = max(sw / w, sh / h); cw, ch = round(sw / k), round(sh / k)
            geo = (w, h); box = ((w - cw) // 2, (h - ch) // 2, cw, ch)
            bi.w, bi.h = f.shape[1], -h
        g32.StretchDIBits(dc, 0, 0, sw, sh, *box, f.ctypes.data, ctypes.byref(bi), 0, 0xCC0020)

def stop():
    try:
        subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq " + (os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "pythonw.exe"), "/PID", open(PIDF).read().strip()],
                       capture_output=True, creationflags=0x08000000)
        os.remove(PIDF)
    except Exception: pass

def autostart(cmd=None):
    import winreg
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE)
    try:
        if cmd: winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, cmd)
        else: winreg.DeleteValue(k, APP)
    except OSError: pass
    winreg.CloseKey(k)

def set_static(path):
    u32.SystemParametersInfoW(20, 0, os.path.abspath(path), 3)

def extract_audio(src, s, e):
    import imageio_ffmpeg
    if os.path.exists(AUD): os.remove(AUD)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-ss", str(s), "-t", str(e - s), "-i", src,
                    "-vn", "-ac", "2", "-ar", "44100", AUD], capture_output=True, creationflags=0x08000000)
    return os.path.exists(AUD)

def main():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import cv2
    from PIL import Image, ImageTk, ImageOps
    sw, sh = u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)

    root = tk.Tk(); root.title("OpenWallpaperEngine"); root.geometry("760x560"); root.minsize(700, 540)
    try: root.iconbitmap(default=os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "app.ico"))
    except Exception: pass
    keys = ("img", "frame", "vid", "about")
    sbar = tk.Frame(root, bg="#2b2b2b"); sbar.pack(side="left", fill="y")
    about = tk.Label(sbar, text="  About", anchor="w", font=("Segoe UI", 11), bg="#2b2b2b", fg="#ddd", pady=10, cursor="hand2")
    about.pack(side="bottom", fill="x")
    side = tk.Listbox(sbar, width=18, exportselection=False, activestyle="none", font=("Segoe UI", 11), bd=0,
                      highlightthickness=0, bg="#2b2b2b", fg="#ddd", selectbackground="#3584e4", selectforeground="#fff")
    for n in ("  Pictures", "  Video frame", "  Animated"): side.insert("end", n)
    side.pack(fill="both", expand=True)
    about.bind("<Button-1>", lambda e: (side.selection_clear(0, "end"), sel(3)))
    body = ttk.Frame(root); body.pack(side="left", fill="both", expand=True, padx=12, pady=12)
    bar = ttk.Frame(body); bar.pack(side="bottom", fill="x", pady=(10, 0))
    P, PRE, T, cur = {}, {}, {}, [0]
    sc = ss = se = None
    au, dk, kp, cut = tk.BooleanVar(value=True), tk.BooleanVar(value=True), tk.BooleanVar(value=False), tk.StringVar()

    def get_img(k, t=None):
        f = P[k].get()
        if not f: return None
        if k == "img": return Image.open(f).convert("RGB")
        cap = cv2.VideoCapture(f)
        if k == "frame": cap.set(1, int(sc.get() * max(int(cap.get(7)) - 1, 0)))
        else: cap.set(0, (ss.get() if t is None else t) * 1000)
        ok, fr = cap.read(); cap.release()
        return Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)) if ok else None

    def show(k, t=None):
        im = get_img(k, t)
        if im:
            im.thumbnail((500, 280)); ph = ImageTk.PhotoImage(im)
            PRE[k].config(image=ph, width=500, height=280); PRE[k].img = ph

    def cutmove(which):
        if se.get() < ss.get() + .5:
            (se if which == "s" else ss).set(ss.get() + .5 if which == "s" else se.get() - .5)
        cut.set(f"Trim: {ss.get():.1f}s → {se.get():.1f}s  (length {se.get() - ss.get():.1f}s)")
        show("vid", ss.get() if which == "s" else se.get())

    def pick(k):
        ft = [("Pictures", "*.png *.jpg *.jpeg *.bmp *.webp")] if k == "img" else [("Videos", "*.mp4 *.mkv *.avi *.mov *.webm")]
        f = filedialog.askopenfilename(filetypes=ft)
        if not f: return
        P[k].set(f)
        if k == "vid":
            c = cv2.VideoCapture(f); d = c.get(7) / (c.get(5) or 30); c.release()
            ss.config(to=d); se.config(to=d); ss.set(0); se.set(d); cutmove("s")
        show(k)

    def apply():
        k = keys[cur[0]]; f = P[k].get()
        if not f: return messagebox.showinfo("", "No file selected")
        save(); stop()
        if k == "img": autostart(None); return set_static(f)
        s, e = (ss.get(), se.get()) if k == "vid" else (0, 0)
        ImageOps.fit(get_img(k, s), (sw, sh), Image.LANCZOS).save(FRAME)  # frame đầu đoạn cắt -> nền tĩnh
        set_static(FRAME)
        if k == "frame": return autostart(None)
        a = au.get()
        if a and not extract_audio(f, s, e):
            a = False; messagebox.showwarning("", "Could not extract audio (video has no sound?)")
        json.dump({"p": f, "s": s, "e": e, "a": a, "d": dk.get(), "k": kp.get()}, open(CFG, "w"))
        if getattr(sys, "frozen", False): cmd = f'"{sys.executable}" --play'  # bản exe: tự gọi lại chính nó
        else:
            exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(exe): exe = sys.executable
            cmd = f'"{exe}" "{os.path.abspath(__file__)}" --play'
        autostart(cmd)
        subprocess.Popen(cmd, creationflags=0x08000008)

    for k in keys[:3]:
        t = T[k] = ttk.Frame(body)
        PRE[k] = tk.Label(t, bg="#222", fg="#888", text="No preview", width=60, height=17); PRE[k].pack(fill="both", expand=True)
        r = ttk.Frame(t); r.pack(fill="x", pady=8)
        P[k] = tk.StringVar()
        ttk.Button(r, text="Browse…", command=lambda k=k: pick(k)).pack(side="left")
        ttk.Label(r, textvariable=P[k]).pack(side="left", padx=8)
        if k == "frame":
            ttk.Label(t, text="Frame position").pack(anchor="w")
            sc = ttk.Scale(t, from_=0, to=1, command=lambda _: show("frame")); sc.pack(fill="x")
        if k == "vid":
            ttk.Label(t, textvariable=cut).pack(anchor="w")
            ss = ttk.Scale(t, from_=0, to=1, command=lambda _: cutmove("s")); ss.pack(fill="x")
            se = ttk.Scale(t, from_=0, to=1, command=lambda _: cutmove("e")); se.pack(fill="x", pady=(0, 6))
            ttk.Checkbutton(t, text="Enable audio", variable=au).pack(anchor="w")
            ttk.Checkbutton(t, text="Mute when other apps play sound", variable=dk).pack(anchor="w")
            ttk.Checkbutton(t, text="Keep audio while hidden behind windows", variable=kp).pack(anchor="w")
    ttk.Button(bar, text="Stop animation", command=lambda: (stop(), autostart(None))).pack(side="left")
    ttk.Button(bar, text="Apply", command=apply).pack(side="right")

    import webbrowser
    ab = T["about"] = ttk.Frame(body)
    ttk.Label(ab, text="OpenWallpaperEngine v1.1", font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(8, 0))
    ttk.Label(ab, text="A free, lightweight animated wallpaper engine for Windows.").pack(anchor="w", pady=(2, 14))
    def sec(h, txt, url=None):
        ttk.Label(ab, text=h, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(ab, text=txt, wraplength=480, justify="left").pack(anchor="w")
        if url:
            l = ttk.Label(ab, text=url, foreground="#3584e4", cursor="hand2", font=("Segoe UI", 9, "underline")); l.pack(anchor="w")
            l.bind("<Button-1>", lambda e: webbrowser.open(url))
    sec("License", "Free software licensed under the GNU General Public License v3.0 (GPLv3). "
        "You can use, study, modify and share it. It comes with no warranty.", "https://www.gnu.org/licenses/gpl-3.0.html")
    sec("Developed by", "Mắt Thần team")
    sec("Author:", "Phúc Power:  the person who conceived the idea, developed, designed, and maintains the project.",
        "https://github.com/PhucPower300121")

    def sel(i):
        cur[0] = i
        for t in T.values(): t.pack_forget()
        bar.pack_forget()
        if i < 3: bar.pack(side="bottom", fill="x", pady=(10, 0))
        T[keys[i]].pack(fill="both", expand=True)
        about.config(bg="#3584e4" if i == 3 else "#2b2b2b", fg="#fff" if i == 3 else "#ddd")
    side.bind("<<ListboxSelect>>", lambda e: side.curselection() and sel(side.curselection()[0]))

    def save():  # nhớ lựa chọn lần trước
        try:
            json.dump({"P": {k: P[k].get() for k in P}, "f": sc.get(), "s": ss.get(), "e": se.get(),
                       "a": au.get(), "d": dk.get(), "k": kp.get(), "t": min(cur[0], 2)}, open(UI, "w"))
        except Exception: pass
    i = 0
    try:
        u = json.load(open(UI))
        for k, v in u["P"].items():
            if v and os.path.exists(v): P[k].set(v)
        au.set(u["a"]); dk.set(u["d"]); kp.set(u["k"]); sc.set(u["f"])
        v = P["vid"].get()
        if v:
            c = cv2.VideoCapture(v); d = c.get(7) / (c.get(5) or 30); c.release()
            ss.config(to=d); se.config(to=d); se.set(min(u["e"], d)); ss.set(u["s"])
        for k in P:
            if P[k].get(): show(k)
        i = min(int(u["t"]), 2)
    except Exception: pass
    if i < 3: side.selection_set(i)
    sel(i)
    root.protocol("WM_DELETE_WINDOW", lambda: (save(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--play": play()
    else: main()
