#!/usr/bin/env python3
import os
import sys
import time
import argparse
from datetime import datetime
import subprocess
import shutil
import ctypes

DEFAULT_WINDOW_TITLE = "BRA-AL00"


def default_output_dir():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "screenshots")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def build_file_path(output_dir, fmt, monitor_index=None):
    name = f"screen_{timestamp()}"
    if monitor_index is not None:
        name += f"_m{monitor_index}"
    ext = "png" if fmt.lower() == "png" else "jpg" if fmt.lower() in ("jpg", "jpeg") else fmt.lower()
    return os.path.join(output_dir, f"{name}.{ext}")


def save_image_pil(image, path, fmt, quality):
    fmt = fmt.lower()
    params = {}
    if fmt in ("jpg", "jpeg"):
        params["quality"] = quality
        fmt = "JPEG"
    elif fmt == "png":
        fmt = "PNG"
        params["compress_level"] = 6
    image.save(path, format=fmt, **params)


def capture_with_pillow(all_monitors, fmt, quality, output_dir):
    try:
        from PIL import ImageGrab
    except Exception as e:
        return None, f"未找到 Pillow 库: {e}"
    try:
        # 尝试多显示器合并截图（Pillow新版本支持），否则退回主显示器
        img = None
        if all_monitors:
            try:
                img = ImageGrab.grab(all_screens=True)
            except TypeError:
                img = ImageGrab.grab()
        else:
            img = ImageGrab.grab()
        ensure_dir(output_dir)
        path = build_file_path(output_dir, fmt)
        save_image_pil(img, path, fmt, quality)
        return [path], None
    except Exception as e:
        return None, f"Pillow截图失败: {e}"


def capture_with_mss(all_monitors, fmt, quality, output_dir, monitor_index=None):
    try:
        import mss
        import mss.tools
    except Exception as e:
        return None, f"未找到 mss 库: {e}"
    try:
        ensure_dir(output_dir)
        paths = []
        with mss.mss() as sct:
            monitors = sct.monitors[1:]  # 跳过索引0（虚拟全屏），使用每个显示器
            if monitor_index is not None:
                if not (1 <= monitor_index <= len(monitors)):
                    return None, f"显示器索引超出范围：有效范围 1..{len(monitors)}"
                targets = [monitors[monitor_index - 1]]
            else:
                targets = monitors if all_monitors else monitors[:1]
            pil_available = False
            try:
                from PIL import Image
                pil_available = True
            except Exception:
                pil_available = False
            for idx, mon in enumerate(targets, start=1):
                img = sct.grab(mon)
                m_idx = monitor_index if monitor_index is not None else (idx if all_monitors else None)
                path = build_file_path(output_dir, fmt, monitor_index=m_idx)
                if fmt.lower() == "png":
                    mss.tools.to_png(img.rgb, img.size, output=path)
                else:
                    if not pil_available:
                        raise RuntimeError("保存为非PNG需要安装 Pillow（pip install pillow）")
                    im = Image.frombytes("RGB", (img.width, img.height), img.rgb)
                    save_image_pil(im, path, fmt, quality)
                paths.append(path)
        return paths, None
    except Exception as e:
        return None, f"mss截图失败: {e}"


def get_extended_frame_bounds(hwnd):
    """使用 DWM 扩展边界获取窗口的可见矩形（去除阴影与非客户区误差）。"""
    try:
        from ctypes import wintypes as wt
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        rect = wt.RECT()
        res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(rect),
            ctypes.sizeof(rect)
        )
        if res == 0:
            return {"left": rect.left, "top": rect.top, "width": rect.right - rect.left, "height": rect.bottom - rect.top}, None
        return None, f"DwmGetWindowAttribute 返回 {res}"
    except Exception as e:
        return None, f"DWM获取失败: {e}"


def get_window_rect_by_title(title, client_only=False):
    """返回窗口或客户区矩形 {left, top, width, height}，按标题包含匹配。"""
    # 优先使用 pywin32，便于获取准确客户区
    try:
        import win32gui
        import win32con
        matches = []
        title_lower = title.lower()
        def _enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                txt = win32gui.GetWindowText(hwnd)
                if txt and title_lower in txt.lower():
                    matches.append(hwnd)
        win32gui.EnumWindows(_enum_cb, None)
        if not matches:
            raise RuntimeError("pywin32未找到匹配窗口")
        hwnd = matches[0]
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        except Exception:
            pass
        if client_only:
            # 客户区坐标转换到屏幕坐标
            l, t, r, b = win32gui.GetClientRect(hwnd)
            # (0,0) 与 (r,b) 转换到屏幕坐标
            from win32gui import ClientToScreen
            x0, y0 = ClientToScreen(hwnd, (0, 0))
            x1, y1 = ClientToScreen(hwnd, (r, b))
            return {"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}, None
        else:
            # 先尝试 DWM 扩展边界，避免阴影和边框导致偏移
            rect_dwm, _ = get_extended_frame_bounds(hwnd)
            if rect_dwm:
                return rect_dwm, None
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            return {"left": l, "top": t, "width": r - l, "height": b - t}, None
    except Exception:
        # 回退到 pygetwindow（不支持客户区，返回整个窗口）
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle(title)
            wins = [w for w in wins if w.isVisible]
            if not wins:
                return None, f"未找到窗口：{title}"
            w = wins[0]
            try:
                w.restore()
            except Exception:
                pass
            return {"left": w.left, "top": w.top, "width": w.width, "height": w.height}, None
        except Exception as e:
            return None, f"窗口定位失败，需要 pywin32 或 pygetwindow：{e}"


def get_hwnd_by_title(title):
    """返回匹配窗口的句柄（可见窗口，包含匹配）。"""
    # 优先 pywin32
    try:
        import win32gui
        matches = []
        title_lower = title.lower()
        def _enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                txt = win32gui.GetWindowText(hwnd)
                if txt and title_lower in txt.lower():
                    matches.append(hwnd)
        win32gui.EnumWindows(_enum_cb, None)
        if matches:
            return matches[0], None
    except Exception as e:
        pass
    # 回退到 pygetwindow
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title)
        wins = [w for w in wins if w.isVisible]
        if wins:
            w = wins[0]
            hwnd = getattr(w, "_hWnd", None)
            if hwnd:
                return hwnd, None
    except Exception:
        pass
    return None, f"未找到窗口：{title}"


def enable_dpi_awareness():
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def bring_window_to_front(hwnd):
    try:
        import win32gui
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        # 临时置顶再恢复，确保不被遮挡
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        return True
    except Exception:
        return False


def capture_window_printwindow(hwnd, fmt, quality, output_dir, client_only=False):
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        from PIL import Image
        ensure_dir(output_dir)
        if client_only:
            l, t, r, b = win32gui.GetClientRect(hwnd)
            width, height = r - l, b - t
        else:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            width, height = r - l, b - t
        hwindc = win32gui.GetWindowDC(hwnd)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)
        flags = (win32con.PW_CLIENTONLY if client_only else 0)
        # 尝试全内容渲染标志（某些窗口支持）
        try:
            flags |= 0x00000002  # PW_RENDERFULLCONTENT
        except Exception:
            pass
        result = win32gui.PrintWindow(hwnd, memdc.GetHandleOutput(), flags)
        win32gui.ReleaseDC(hwnd, hwindc)
        memdc.DeleteDC()
        srcdc.DeleteDC()
        if result != 1:
            win32gui.DeleteObject(bmp.GetHandle())
            return None, "PrintWindow 未能捕获窗口内容"
        bmpinfo = bmp.GetInfo()
        bmpstr = bmp.GetBitmapBits(True)
        win32gui.DeleteObject(bmp.GetHandle())
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )
        path = build_file_path(output_dir, fmt)
        save_image_pil(img, path, fmt, quality)
        return [path], None
    except Exception as e:
        return None, f"PrintWindow 捕获失败：{e}"


def capture_window_by_title(title, fmt, quality, output_dir, client_only=False):
    # 优先尝试句柄 + PrintWindow（可在被遮挡时仍获取内容）
    hwnd, _ = get_hwnd_by_title(title)
    if hwnd:
        paths, err = capture_window_printwindow(hwnd, fmt, quality, output_dir, client_only=client_only)
        if paths:
            return paths, None
        # PrintWindow失败则尝试置顶后区域截图
        brought = bring_window_to_front(hwnd)
        if brought:
            try:
                import win32gui
                if client_only:
                    l, t, r, b = win32gui.GetClientRect(hwnd)
                    from win32gui import ClientToScreen
                    x0, y0 = ClientToScreen(hwnd, (0, 0))
                    x1, y1 = ClientToScreen(hwnd, (r, b))
                    rect = {"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}
                else:
                    # 尝试 DWM 可见边界
                    rect_dwm, _ = get_extended_frame_bounds(hwnd)
                    if rect_dwm:
                        rect = rect_dwm
                    else:
                        l, t, r, b = win32gui.GetWindowRect(hwnd)
                        rect = {"left": l, "top": t, "width": r - l, "height": b - t}
                # mss 区域截图
                try:
                    import mss, mss.tools
                    with mss.mss() as sct:
                        bbox = {"left": int(rect["left"]), "top": int(rect["top"]), "width": int(rect["width"]), "height": int(rect["height"]) }
                        img = sct.grab(bbox)
                        path = build_file_path(output_dir, fmt)
                        if fmt.lower() == "png":
                            mss.tools.to_png(img.rgb, img.size, output=path)
                        else:
                            from PIL import Image
                            im = Image.frombytes("RGB", (img.width, img.height), img.rgb)
                            save_image_pil(im, path, fmt, quality)
                        return [path], None
                except Exception:
                    pass
            except Exception:
                pass
    # 句柄不可用或以上失败，回退到原区域截图逻辑
    rect, err = get_window_rect_by_title(title, client_only=client_only)
    if not rect:
        return None, err
    ensure_dir(output_dir)
    try:
        from PIL import ImageGrab
        right = rect["left"] + rect["width"]
        bottom = rect["top"] + rect["height"]
        img = ImageGrab.grab(bbox=(int(rect["left"]), int(rect["top"]), int(right), int(bottom)))
        path = build_file_path(output_dir, fmt)
        save_image_pil(img, path, fmt, quality)
        return [path], None
    except Exception as pil_err:
        try:
            import mss, mss.tools
            with mss.mss() as sct:
                bbox = {"left": int(rect["left"]), "top": int(rect["top"]), "width": int(rect["width"]), "height": int(rect["height"]) }
                img = sct.grab(bbox)
                path = build_file_path(output_dir, fmt)
                if fmt.lower() == "png":
                    mss.tools.to_png(img.rgb, img.size, output=path)
                else:
                    from PIL import Image
                    im = Image.frombytes("RGB", (img.width, img.height), img.rgb)
                    save_image_pil(im, path, fmt, quality)
                return [path], None
        except Exception as mss_err:
            return None, f"窗口区域截图失败：Pillow错误={pil_err}；mss错误={mss_err}"


def resolve_adb_path(user_adb):
    if user_adb:
        return user_adb if os.path.exists(user_adb) else None
    path = shutil.which("adb")
    return path


def list_connected_devices(adb_path):
    try:
        proc = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if proc.returncode != 0:
            return []
        lines = proc.stdout.decode("utf-8", errors="ignore").splitlines()
        serials = []
        for line in lines:
            if "\tdevice" in line:
                serials.append(line.split("\t")[0].strip())
        return serials
    except Exception:
        return []


def capture_from_device(fmt, quality, output_dir, serial=None, adb_path=None):
    adb = resolve_adb_path(adb_path)
    if not adb:
        return None, "未找到 adb，请安装 Android 平台工具或通过 --adb 指定路径"
    if not serial:
        serials = list_connected_devices(adb)
        if not serials:
            return None, "未发现已授权设备，请连接并在手机上允许 USB 调试，或通过 --serial 指定设备"
        serial = serials[0]
    ensure_dir(output_dir)
    cmd = [adb, "-s", serial, "exec-out", "screencap", "-p"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if proc.returncode != 0 or not proc.stdout:
            err = proc.stderr.decode("utf-8", errors="ignore").strip()
            return None, f"设备截图失败：{err}"
        data = proc.stdout
        path = build_file_path(output_dir, fmt)
        if fmt.lower() == "png":
            with open(path, "wb") as f:
                f.write(data)
        else:
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(data)).convert("RGB")
            save_image_pil(im, path, fmt, quality)
        return [path], None
    except Exception as e:
        return None, f"设备截图异常：{e}"


def main():
    parser = argparse.ArgumentParser(description="Windows屏幕截图并保存")
    parser.add_argument("--output", "-o", default=default_output_dir(), help="保存目录（默认：脚本同目录下 screenshots）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="抓取所有显示器（mss会分别保存；Pillow可能合成为一张）")
    group.add_argument("--monitor", type=int, help="仅抓取指定显示器（1为主显示器，2为副屏等）")
    group.add_argument("--window", type=str, help="按窗口标题抓取指定程序窗口（支持包含匹配）")
    # 保留 --from-device 但默认不使用
    parser.add_argument("--client-only", action="store_true", help="仅截取窗口客户区（不含边框与标题栏）")
    parser.add_argument("--delay", type=float, default=0.0, help="截图前延迟秒数，便于切换窗口")
    parser.add_argument("--format", "-f", default="png", choices=["png", "jpg", "jpeg"], help="保存格式")
    parser.add_argument("--quality", type=int, default=90, help="JPEG质量（1-100，默认90）")
    args = parser.parse_args()

    enable_dpi_awareness()

    if args.delay > 0:
        time.sleep(args.delay)

    # 模式选择：若未指定任何组选项，则默认抓取名为 DEFAULT_WINDOW_TITLE 的窗口
    if not (args.window or args.monitor or args.all):
        title = DEFAULT_WINDOW_TITLE
        paths, err = capture_window_by_title(title, args.format, args.quality, args.output, client_only=args.client_only)
        if not paths:
            print("截图失败：")
            if err:
                print(f"- {err}")
            print("请安装依赖：pip install mss 或 pip install pillow；窗口定位推荐：pip install pywin32 或 pip install pygetwindow")
            sys.exit(1)
    elif args.window:
        paths, err = capture_window_by_title(args.window, args.format, args.quality, args.output, client_only=args.client_only)
        if not paths:
            print("截图失败：")
            if err:
                print(f"- {err}")
            print("请安装依赖：pip install mss 或 pip install pillow；窗口定位推荐：pip install pywin32 或 pip install pygetwindow")
            sys.exit(1)
    elif args.monitor is not None:
        paths, err = capture_with_mss(False, args.format, args.quality, args.output, monitor_index=args.monitor)
        if not paths:
            print("截图失败：")
            if err:
                print(f"- {err}")
            print("请先安装依赖：pip install mss")
            sys.exit(1)
    else:
        # 先尝试 Pillow，失败则回退到 mss
        paths, err = capture_with_pillow(args.all, args.format, args.quality, args.output)
        if not paths:
            paths, err2 = capture_with_mss(args.all, args.format, args.quality, args.output)
            if not paths:
                print("截图失败：")
                if err:
                    print(f"- {err}")
                if err2:
                    print(f"- {err2}")
                print("请先安装依赖：pip install pillow 或 pip install mss")
                sys.exit(1)

    print("截图完成，已保存：")
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()