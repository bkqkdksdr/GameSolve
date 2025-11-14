# GameSolve - 数独自动求解系统

GameSolve是一个功能强大的数独自动求解系统，能够从屏幕截图中自动识别数独并快速求解。

## 功能特性

- 📸 **屏幕截图**：支持全屏或指定窗口截图
- 🔍 **数独检测**：自动从图像中检测数独九宫格
- 📝 **数字识别**：使用OCR技术识别数独中的数字
- 🧠 **智能求解**：采用回溯算法快速求解数独
- 💻 **命令行界面**：提供丰富的命令行参数，方便自定义使用

## 安装要求

### 依赖库

```bash
pip install opencv-python numpy pillow pytesseract mss pywin32
```

### 外部依赖

- **Tesseract OCR**：用于数字识别
  - 下载地址：https://github.com/tesseract-ocr/tesseract
  - 安装后需要将Tesseract的安装路径添加到环境变量中，或在代码中修改`tesseract_cmd`路径

## 使用方法

### 快速开始

最简单的使用方法是直接运行主脚本：

```bash
python SudokuSolver.py
```

这将执行完整的数独求解流程：
1. 屏幕截图
2. 提取数独九宫格
3. 识别数字
4. 求解数独
5. 显示结果

### 命令行参数

主脚本支持以下参数：

```
--output, -o     保存目录（默认：screenshots）
--delay          截图前延迟秒数，便于切换窗口（默认：0.0）
--format, -f     保存格式（默认：png，可选：jpg/jpeg）
--quality        JPEG质量（1-100，默认：90）
```

### 示例

```bash
# 延迟2秒后截图，保存为JPEG格式
python SudokuSolver.py --delay 2 --format jpg --quality 80

# 自定义保存目录
python SudokuSolver.py --output my_screenshots
```

## 工作流程

1. **屏幕截图**：使用Pillow或mss库进行屏幕截图
2. **图像预处理**：
   - 转换为灰度图
   - 高斯模糊去除噪声
   - 自适应阈值二值化
3. **数独检测**：
   - 查找图像中的轮廓
   - 识别四边形轮廓（数独九宫格）
   - 重新排序四个角点
4. **透视变换**：将数独九宫格校正为正方形
5. **数字识别**：
   - 提取每个单元格
   - 使用Tesseract OCR识别数字
6. **数独求解**：使用回溯算法求解数独
7. **结果显示**：打印识别的数独和求解结果

## 项目结构

```
GameSolve/
├── GameScreenCapture.py   # 屏幕截图和数独提取模块
├── SolvePuzzle.py         # 数独识别和求解模块
├── SudokuSolver.py        # 主脚本，整合所有功能
└── screenshots/           # 截图保存目录（自动创建）
```

### 模块说明

#### GameScreenCapture.py
负责屏幕截图和数独九宫格的提取，主要功能包括：
- 多显示器截图支持
- 窗口截图支持
- 图像预处理
- 数独九宫格检测和校正

#### SolvePuzzle.py
负责数独的数字识别和求解，主要功能包括：
- 图像预处理
- 单元格提取
- OCR数字识别
- 回溯法数独求解

#### SudokuSolver.py
主脚本，整合前两个模块的功能，提供统一的命令行接口。

## 注意事项

1. 确保Tesseract OCR已正确安装并配置
2. 截图时尽量确保数独清晰可见，避免模糊或倾斜
3. 对于复杂背景的数独图片，识别准确率可能会降低
4. 程序会自动在当前目录创建`screenshots`文件夹保存截图

## 故障排除

### 常见问题

1. **TesseractNotFoundError**：
   - 确保Tesseract已正确安装
   - 检查Tesseract的安装路径是否正确
   - 可以在SolvePuzzle.py中手动设置`tesseract_cmd`路径

2. **无法找到数独网格**：
   - 确保截图中包含完整的数独九宫格
   - 尝试调整截图区域或提高图像质量

3. **数字识别错误**：
   - 确保数独图像清晰可见
   - 避免光线过暗或过亮
   - 可以尝试手动修改识别错误的数字后再次求解

## 扩展功能

该项目可以进一步扩展，例如：
- 添加图形用户界面(GUI)
- 支持实时视频流中的数独识别
- 增加更多的图像预处理算法提高识别准确率
- 支持更多类型的数独变体

## 许可证

本项目采用MIT许可证。