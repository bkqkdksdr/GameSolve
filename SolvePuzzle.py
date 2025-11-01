"""
SolvePuzzle.py
- 唯一功能：从截图中自动裁剪棋盘方格区域，并保存为 board_*.png 到 screenshots 文件夹。
- 依赖：opencv-python、numpy（用于图像处理）。
- 使用：
    1) 默认从 screenshots 目录中选择最新的 screen_*.png/jpg 作为输入：
       python SolvePuzzle.py
    2) 指定输入图片：
       python SolvePuzzle.py --input screenshots/screen_2025....png
    3) 手动指定棋盘矩形（x,y,w,h），当自动检测失败时：
       python SolvePuzzle.py --input <path> --board 80,240,360,360
"""
import os
import re
import sys
import argparse
from glob import glob

import cv2
import numpy as np

DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def latest_screenshot(output_dir: str) -> str | None:
    """返回 screenshots 目录下最新的 screen_*.png/jpg 文件路径。"""
    patterns = [os.path.join(output_dir, "screen_*.png"), os.path.join(output_dir, "screen_*.jpg"), os.path.join(output_dir, "screen_*.jpeg")]
    files = []
    for p in patterns:
        files.extend(glob(p))
    if not files:
        return None
    # 依据文件名中的时间戳排序（若失败则按修改时间）
    def key_func(f):
        m = re.search(r"screen_(\d{8}_\d{6}_\d+)", os.path.basename(f))
        if m:
            return m.group(1)
        return str(os.path.getmtime(f))
    files.sort(key=key_func)
    return files[-1]


def detect_board_rect(bgr: np.ndarray) -> tuple[int, int, int, int] | None:
    """自动检测棋盘方格区域，返回 (x,y,w,h)。
    思路：
    - HSV 颜色空间中，棋盘背景为低亮度（V低）、低饱和度的深灰色，做阈值得到掩膜；
    - 形态学闭运算合并方格；
    - 在掩膜中寻找近似正方形且面积较大的外接矩形，作为棋盘区域。
    """
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # 阈值范围：暗灰（低V），适度限制S以避免彩色星星
    low = np.array([0, 0, 0])
    high = np.array([180, 90, 110])  # S<=90, V<=110（可根据截图微调）
    mask = cv2.inRange(hsv, low, high)

    # 形态学：闭运算 + 开运算，平滑与填充小孔
    k = max(3, int(min(h, w) * 0.006))  # 自适应核大小
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # 轮廓寻找
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    img_area = h * w
    candidates: list[tuple[int, int, int, int, float]] = []  # (x,y,w,h,score)
    for c in cnts:
        x, y, ww, hh = cv2.boundingRect(c)
        area = ww * hh
        if area < img_area * 0.05:  # 太小跳过
            continue
        ar = ww / float(hh)
        if ar < 0.85 or ar > 1.15:  # 近似正方形
            continue
        # 评分：面积大 + 正方形程度好
        score = area * (1.0 - abs(ar - 1.0))
        candidates.append((x, y, ww, hh, score))

    if not candidates:
        return None
    # 选择评分最高者
    candidates.sort(key=lambda t: t[4])
    x, y, ww, hh, _ = candidates[-1]

    # 可选：轻微向外扩展，避免切到边缘（按比例扩 2%）
    pad = int(0.02 * min(ww, hh))
    x = max(0, x - pad)
    y = max(0, y - pad)
    ww = min(w - x, ww + 2 * pad)
    hh = min(h - y, hh + 2 * pad)
    return x, y, ww, hh


def crop_board(input_path: str, output_dir: str) -> tuple[str | None, str | None]:
    """对输入图片裁剪棋盘区域并保存，返回 (保存路径, 错误)。"""
    if not os.path.isfile(input_path):
        return None, f"找不到输入图片：{input_path}"
    bgr = cv2.imread(input_path)
    if bgr is None:
        return None, "读取图片失败（可能路径或格式问题）"
    rect = detect_board_rect(bgr)
    if rect is None:
        return None, "自动检测棋盘失败，可使用 --board x,y,w,h 手动指定"
    x, y, ww, hh = rect
    crop = bgr[y:y+hh, x:x+ww]

    ensure_dir(output_dir)
    out_path = os.path.join(output_dir, f"board_{os.path.splitext(os.path.basename(input_path))[0].replace('screen_','')}.png")
    cv2.imwrite(out_path, crop)
    return out_path, None


def crop_board_manual(input_path: str, output_dir: str, rect_str: str) -> tuple[str | None, str | None]:
    """手动指定矩形裁剪，rect_str 形如 "x,y,w,h"。"""
    try:
        parts = [int(p) for p in rect_str.split(',')]
        if len(parts) != 4:
            return None, "--board 需要4个整数：x,y,w,h"
        x, y, ww, hh = parts
    except Exception:
        return None, "--board 参数解析失败，应为 x,y,w,h"
    if not os.path.isfile(input_path):
        return None, f"找不到输入图片：{input_path}"
    bgr = cv2.imread(input_path)
    if bgr is None:
        return None, "读取图片失败"
    h, w = bgr.shape[:2]
    x = max(0, min(x, w-1))
    y = max(0, min(y, h-1))
    ww = max(1, min(ww, w-x))
    hh = max(1, min(hh, h-y))
    crop = bgr[y:y+hh, x:x+ww]

    ensure_dir(output_dir)
    out_path = os.path.join(output_dir, f"board_{os.path.splitext(os.path.basename(input_path))[0].replace('screen_','')}.png")
    cv2.imwrite(out_path, crop)
    return out_path, None


def main():
    parser = argparse.ArgumentParser(description="从截图中裁剪棋盘方格区域并保存为 board_*.png")
    parser.add_argument("--input", "-i", help="输入截图路径（默认取 screenshots 中最新 screen_* 文件）")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_DIR, help="输出目录（默认 screenshots）")
    parser.add_argument("--board", help="手动指定棋盘矩形 x,y,w,h（自动检测失败时使用）")
    args = parser.parse_args()

    input_path = args.input
    if not input_path:
        input_path = latest_screenshot(args.output)
        if not input_path:
            print("未找到任何截图（screen_*.png/jpg）。请先运行 GameScreenCapture.py 生成截图。")
            sys.exit(1)

    if args.board:
        out, err = crop_board_manual(input_path, args.output, args.board)
    else:
        out, err = crop_board(input_path, args.output)

    if not out:
        print("裁剪失败：")
        if err:
            print(f"- {err}")
        print("依赖安装：pip install opencv-python numpy")
        sys.exit(1)

    print("棋盘裁剪完成：")
    print(out)


if __name__ == "__main__":
    main()