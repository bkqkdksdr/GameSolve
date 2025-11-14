import cv2
import numpy as np
import pytesseract
from PIL import Image
import matplotlib.pyplot as plt
import os  # 导入os模块用于文件操作

pytesseract.pytesseract.tesseract_cmd = r'D:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_sudoku_image(image_path):
    """预处理数独图片"""
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"无法读取图片: {image_path}")
        return None
    
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 高斯模糊
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 自适应阈值处理
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    return thresh, gray

def find_sudoku_grid(image):
    """查找数独网格"""
    # 查找轮廓
    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 找到最大的轮廓（应该是数独网格）
    if not contours:
        return None
    
    largest_contour = max(contours, key=cv2.contourArea)
    
    # 近似轮廓为多边形
    epsilon = 0.02 * cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    if len(approx) == 4:
        return approx
    return None

def extract_cells(warped, grid_size=9):
    """提取数独的每个单元格"""
    height, width = warped.shape
    cell_height = height // grid_size
    cell_width = width // grid_size
    
    cells = []
    positions = []
    
    for row in range(grid_size):
        row_cells = []
        row_positions = []
        for col in range(grid_size):
            # 计算单元格边界（添加一些边距以避免边界线）
            margin = 5
            y1 = row * cell_height + margin
            y2 = (row + 1) * cell_height - margin
            x1 = col * cell_width + margin
            x2 = (col + 1) * cell_width - margin
            
            # 提取单元格
            cell = warped[y1:y2, x1:x2]
            row_cells.append(cell)
            row_positions.append((row, col))
        
        cells.append(row_cells)
        positions.append(row_positions)
    
    return cells, positions

def recognize_digit(cell_image):
    """识别单个单元格中的数字"""
    # 调整图像大小以提高OCR准确率
    cell_resized = cv2.resize(cell_image, (50, 50))
    
    # 转换为PIL图像
    pil_image = Image.fromarray(cell_resized)
    
    # 使用pytesseract识别数字
    config = '--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789'
    digit = pytesseract.image_to_string(pil_image, config=config)
    
    # 清理识别结果
    digit = digit.strip()
    
    # 如果识别为空或不是单个数字，则返回0（表示空单元格）
    if not digit or len(digit) != 1 or not digit.isdigit():
        return 0
    
    return int(digit)

def recognize_sudoku_from_image(image_path):
    """从图片中识别数独"""
    print("正在处理数独图片...")
    
    # 预处理图片
    result = preprocess_sudoku_image(image_path)
    if result is None:
        return None
    
    thresh, gray = result
    
    # 查找数独网格
    grid_contour = find_sudoku_grid(thresh)
    if grid_contour is None:
        print("未找到数独网格")
        return None
    
    # 透视变换以校正图像
    points = grid_contour.reshape(4, 2)
    rect = np.zeros((4, 2), dtype="float32")
    
    # 对点进行排序：[左上，右上，右下，左下]
    s = points.sum(axis=1)
    rect[0] = points[np.argmin(s)]
    rect[2] = points[np.argmax(s)]
    
    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]
    rect[3] = points[np.argmax(diff)]
    
    # 计算新图像的尺寸
    width = max(np.linalg.norm(rect[0] - rect[1]), np.linalg.norm(rect[2] - rect[3]))
    height = max(np.linalg.norm(rect[0] - rect[3]), np.linalg.norm(rect[1] - rect[2]))
    
    dst = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ], dtype="float32")
    
    # 计算透视变换矩阵并应用
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(gray, M, (int(width), int(height)))
    
    # 再次二值化校正后的图像
    warped_thresh = cv2.adaptiveThreshold(warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 11, 2)
    
    # 提取单元格
    cells, positions = extract_cells(warped_thresh)
    
    # 识别每个单元格的数字
    sudoku_grid = [[0 for _ in range(9)] for _ in range(9)]
    
    print("正在识别数字...")
    for i in range(9):
        for j in range(9):
            cell = cells[i][j]
            digit = recognize_digit(cell)
            sudoku_grid[i][j] = digit
    
    return sudoku_grid

def print_sudoku_grid(grid):
    """美观地打印数独网格"""
    print("\n识别到的数独:")
    print("+" + "---+" * 9)
    for i in range(9):
        row_str = "|"
        for j in range(9):
            cell = grid[i][j]
            if cell == 0:
                row_str += "   |"
            else:
                row_str += f" {cell} |"
        print(row_str)
        if (i + 1) % 3 == 0 and i != 8:
            print("+" + "---+" * 9)
        else:
            print("+" + "---+" * 9)
    print("+" + "---+" * 9)

# 使用示例
if __name__ == "__main__":
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建screenshots文件夹路径
    screenshots_dir = os.path.join(current_dir, "screenshots")
    
    # 查找screenshots文件夹中所有符合sudoku_grid_*.png格式的文件
    sudoku_files = []
    if os.path.exists(screenshots_dir):
        for file in os.listdir(screenshots_dir):
            if file.startswith("sudoku_grid_") and file.endswith(".png"):
                sudoku_files.append(file)
    
    # 如果找到符合条件的文件，选择最新的一个
    if sudoku_files:
        # 根据文件修改时间排序，最新的在最后
        sudoku_files.sort(key=lambda x: os.path.getmtime(os.path.join(screenshots_dir, x)))
        # 获取最新的文件
        latest_file = sudoku_files[-1]
        # 构建完整路径
        image_path = os.path.join(screenshots_dir, latest_file)
        print(f"使用最新的数独图片: {latest_file}")
    else:
        print("未找到符合条件的数独图片(sudoku_grid_*.png)")
        exit(1)
    
    try:
        # 识别数独
        sudoku_grid = recognize_sudoku_from_image(image_path)
        
        if sudoku_grid:
            # 打印结果
            print_sudoku_grid(sudoku_grid)
            
            # 同时以数组形式打印
            print("\n数组形式:")
            for row in sudoku_grid:
                print(row)
        else:
            print("未能成功识别数独")
    except Exception as e:
        print(f"处理数独图片时出错: {e}")
        print("请确保已安装必要的库: opencv-python, pytesseract, PIL")
        print("并且已安装Tesseract OCR")