# -*- coding: utf-8 -*-
# venster_win.py - Windows-vensters vinden en inbedden (voor DraveOS).
# Copyright (C) 2026 Dravenlock (Roger & Claudio). Vrije software onder de GNU GPL v3.0.
"""Kleine ctypes-laag rond de Windows API: vensters van een proces (en zijn kinderen) vinden,
de rand/titelbalk weghalen (DraveOS tekent zijn eigen), en weer terugzetten."""
import ctypes
import sys

WIN = sys.platform == "win32"

if WIN:
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WS_SYSMENU = 0x00080000
    WS_POPUP = 0x80000000
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_DLGMODALFRAME = 0x00000001
    WS_EX_WINDOWEDGE = 0x00000100
    WS_EX_CLIENTEDGE = 0x00000200
    WS_EX_STATICEDGE = 0x00020000
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_FRAMECHANGED, SWP_SHOWWINDOW = 0x1, 0x2, 0x4, 0x20, 0x40
    GW_OWNER = 4
    WM_CLOSE = 0x0010
    SW_RESTORE, SW_SHOW = 9, 5
    TH32CS_SNAPPROCESS = 0x00000002

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.SetParent.restype = wintypes.HWND
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        _GetLong = user32.GetWindowLongPtrW
        _SetLong = user32.SetWindowLongPtrW
        _GetLong.restype = ctypes.c_ssize_t
        _SetLong.restype = ctypes.c_ssize_t
        _GetLong.argtypes = [wintypes.HWND, ctypes.c_int]
        _SetLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    else:
        _GetLong = user32.GetWindowLongW
        _SetLong = user32.SetWindowLongW

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def proces_familie(pid):
    """pid plus alle kind- en kleinkindprocessen (PyInstaller-onefile start een kindproces)."""
    if not WIN:
        return {pid}
    ouders = {}
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == wintypes.HANDLE(-1).value:
        return {pid}
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            ouders.setdefault(e.th32ParentProcessID, []).append(e.th32ProcessID)
            ok = kernel32.Process32NextW(snap, ctypes.byref(e))
    finally:
        kernel32.CloseHandle(snap)
    fam, rij = {pid}, [pid]
    while rij:
        p = rij.pop()
        for k in ouders.get(p, []):
            if k not in fam and k != 0:
                fam.add(k)
                rij.append(k)
    return fam


def titel(hwnd):
    if not WIN:
        return ""
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def grootte(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.right - r.left, r.bottom - r.top


def hoofdvenster(pids, negeer=()):
    """Het grootste zichtbare top-level venster (zonder eigenaar, met titel) van deze processen."""
    if not WIN:
        return None
    kandidaten = []

    def cb(hwnd, _):
        try:
            if hwnd in negeer or not user32.IsWindowVisible(hwnd):
                return True
            p = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value not in pids:
                return True
            if user32.GetWindow(hwnd, GW_OWNER):
                return True
            ex = _GetLong(hwnd, GWL_EXSTYLE)
            if ex & WS_EX_TOOLWINDOW:
                return True
            w, h = grootte(hwnd)
            if w < 200 or h < 120:
                return True
            kandidaten.append((w * h, hwnd))
        except Exception:
            pass
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    if not kandidaten:
        return None
    kandidaten.sort(reverse=True)
    return kandidaten[0][1]


def bestaat(hwnd):
    return bool(WIN and hwnd and user32.IsWindow(hwnd))


def kaal_maken(hwnd):
    """Haal titelbalk en rand weg (DraveOS tekent zijn eigen). Geeft de oude stijlen terug."""
    stijl = _GetLong(hwnd, GWL_STYLE)
    ex = _GetLong(hwnd, GWL_EXSTYLE)
    nieuw = stijl & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
    nieuw_ex = ex & ~(WS_EX_APPWINDOW | WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE)
    user32.ShowWindow(hwnd, SW_RESTORE)
    _SetLong(hwnd, GWL_STYLE, nieuw)
    _SetLong(hwnd, GWL_EXSTYLE, nieuw_ex)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
    return stijl, ex


def vrijlaten(hwnd, stijl, ex):
    """Venster weer een gewoon Windows-venster maken (bij afsluiten van DraveOS)."""
    if not bestaat(hwnd):
        return
    user32.SetParent(hwnd, 0)
    _SetLong(hwnd, GWL_STYLE, stijl)
    _SetLong(hwnd, GWL_EXSTYLE, ex)
    user32.SetWindowPos(hwnd, 0, 80, 80, 1100, 750, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
    user32.ShowWindow(hwnd, SW_SHOW)


def sluit(hwnd):
    if bestaat(hwnd):
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


if WIN:
    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", wintypes.HWND),
                    ("hwndFocus", wintypes.HWND), ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                    ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND), ("rcCaret", wintypes.RECT)]
    user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
    user32.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]


def focus_venster():
    """Het venster dat nu toetsenbordfocus heeft (in de voorgrond-thread), of None."""
    if not WIN:
        return None
    g = GUITHREADINFO()
    g.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not user32.GetGUIThreadInfo(0, ctypes.byref(g)):
        return None
    return g.hwndFocus or g.hwndActive


def hoort_bij(ouder, hwnd):
    return bool(WIN and hwnd and ouder and (hwnd == ouder or user32.IsChild(ouder, hwnd)))


def heeft_dialoog(pids):
    """Heeft een van deze processen een zichtbaar los venster (bv. 'Wil je opslaan?')?
    Het ingebedde hoofdvenster telt niet mee: dat is nu een kindvenster van DraveOS."""
    if not WIN:
        return False
    gevonden = []

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            p = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value in pids:
                w, h = grootte(hwnd)
                if w > 50 and h > 30:
                    gevonden.append(hwnd)
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return bool(gevonden)


def stop_proces(pid):
    """Proces + kinderen hard stoppen (alleen als netjes sluiten niet lukte)."""
    import subprocess
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=10)
    except Exception:
        pass


def zichtbaar(hwnd):
    return bool(WIN and hwnd and user32.IsWindowVisible(hwnd))


# ------------------------------------------------------------------ grote pictogrammen uit een .exe
if WIN:
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    user32.PrivateExtractIconsW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                            ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.UINT),
                                            wintypes.UINT, wintypes.UINT]
    user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON, ctypes.c_int,
                                  ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT]
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]


def exe_icoon(pad, maat=256):
    """Het pictogram van een .exe op groot formaat. Geeft (bytes BGRA, maat, heeft_alpha) of None."""
    if not WIN:
        return None
    hicon = wintypes.HICON()
    nr = wintypes.UINT()
    try:
        n = user32.PrivateExtractIconsW(pad, 0, maat, maat, ctypes.byref(hicon), ctypes.byref(nr), 1, 0)
    except Exception:
        return None
    if n < 1 or not hicon:
        return None
    hdc = gdi32.CreateCompatibleDC(None)
    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = maat, -maat, 1, 32
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    data = None
    try:
        if hbmp and bits:
            oud = gdi32.SelectObject(hdc, hbmp)
            user32.DrawIconEx(hdc, 0, 0, hicon, maat, maat, 0, None, 3)
            data = ctypes.string_at(bits, maat * maat * 4)
            gdi32.SelectObject(hdc, oud)
    finally:
        if hbmp:
            gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        user32.DestroyIcon(hicon)
    if not data:
        return None
    alpha = any(data[i] for i in range(3, len(data), 4 * 97))
    return data, maat, alpha


def windows_achtergrond():
    """Pad van de huidige Windows-bureaubladachtergrond (of '')."""
    if not WIN:
        return ""
    buf = ctypes.create_unicode_buffer(520)
    try:
        user32.SystemParametersInfoW(0x0073, 520, buf, 0)
    except Exception:
        return ""
    return buf.value


# ------------------------------------------------------------------ Windows' eigen programma's
if WIN:
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND


def exe_van(pid):
    """Bestandsnaam (klein) van het programma achter een proces, bv. 'notepad.exe'."""
    if not WIN:
        return ""
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return ""
    try:
        b = ctypes.create_unicode_buffer(520)
        n = wintypes.DWORD(520)
        if kernel32.QueryFullProcessImageNameW(h, 0, b, ctypes.byref(n)):
            import os
            return os.path.basename(b.value).lower()
    finally:
        kernel32.CloseHandle(h)
    return ""


def klasse(hwnd):
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, b, 256)
    return b.value


def pid_van(hwnd):
    p = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value


def alle_vensters():
    """Alle zichtbare top-level vensters (hwnd's) van dit moment."""
    if not WIN:
        return set()
    r = set()

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            r.add(hwnd)
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return r


def nieuw_venster(voor, exes=(), klassen=(), negeer=()):
    """Het grootste NIEUWE zichtbare top-level venster (niet in 'voor') van een van deze programma's
    of vensterklassen. Voor programma's die via een ander proces starten (Kladblok uit de Store,
    Verkenner, Configuratiescherm)."""
    if not WIN:
        return None
    exes = {e.lower() for e in exes}
    kandidaten = []

    def cb(hwnd, _):
        try:
            if hwnd in voor or hwnd in negeer or not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, GW_OWNER):
                return True
            w, h = grootte(hwnd)
            if w < 200 or h < 120:
                return True
            ok = (klassen and klasse(hwnd) in klassen) or (exes and exe_van(pid_van(hwnd)) in exes)
            if ok:
                kandidaten.append((w * h, hwnd))
        except Exception:
            pass
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    if not kandidaten:
        return None
    kandidaten.sort(reverse=True)
    return kandidaten[0][1]


def is_ingebed(hwnd):
    return bool(WIN and hwnd and user32.GetParent(hwnd))
