#!/usr/bin/env python3
"""
数独求解主脚本
功能：一键完成屏幕截图、数独提取、识别和求解
使用方法：python SudokuSolver.py
"""

import os
import sys
import subprocess
import argparse

def main():
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="一键完成数独截图、提取、识别和求解")
    parser.add_argument("--output", "-o", default="screenshots", help="保存目录（默认：screenshots）")
    parser.add_argument("--delay", type=float, default=0.0, help="截图前延迟秒数，便于切换窗口")
    parser.add_argument("--format", "-f", default="png", choices=["png", "jpg", "jpeg"], help="保存格式")
    parser.add_argument("--quality", type=int, default=90, help="JPEG质量（1-100，默认90）")
    args = parser.parse_args()
    
    print("=" * 50)
    print("正在执行数独自动求解流程...")
    print("=" * 50)
    
    # 步骤1：执行截图和数独提取
    print("\n[步骤1/3] 屏幕截图并提取数独九宫格...")
    capture_cmd = [
        sys.executable, "GameScreenCapture.py",
        "--extract-sudoku",
        "--only-sudoku"
    ]
    
    try:
        # 使用正确的编码处理输出
        capture_result = subprocess.run(
            capture_cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            check=True
        )
        if capture_result.stdout:
            print(capture_result.stdout)
        if capture_result.stderr:
            print("警告:", capture_result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"截图和提取失败: {e}")
        if e.stdout:
            print(f"标准输出: {e.stdout}")
        if e.stderr:
            print(f"错误输出: {e.stderr}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"编码错误: {e}")
        # 尝试使用二进制模式重新运行命令
        try:
            capture_result = subprocess.run(
                capture_cmd, 
                capture_output=True, 
                check=True
            )
            print(f"标准输出: {capture_result.stdout.decode('utf-8', errors='replace')}")
            print(f"错误输出: {capture_result.stderr.decode('utf-8', errors='replace')}")
        except Exception as e2:
            print(f"重新运行命令时出错: {e2}")
        sys.exit(1)
    except Exception as e:
        print(f"执行截图脚本时出错: {e}")
        sys.exit(1)
    
    # 步骤2：执行数独识别和求解
    print("\n[步骤2/3] 识别数独并求解...")
    solve_cmd = [sys.executable, "SolvePuzzle.py"]
    
    try:
        # 使用正确的编码处理输出
        solve_result = subprocess.run(
            solve_cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            check=True
        )
        if solve_result.stdout:
            print(solve_result.stdout)
        if solve_result.stderr:
            print("警告:", solve_result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"数独识别和求解失败: {e}")
        if e.stdout:
            print(f"标准输出: {e.stdout}")
        if e.stderr:
            print(f"错误输出: {e.stderr}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"编码错误: {e}")
        # 尝试使用二进制模式重新运行命令
        try:
            solve_result = subprocess.run(
                solve_cmd, 
                capture_output=True, 
                check=True
            )
            print(f"标准输出: {solve_result.stdout.decode('utf-8', errors='replace')}")
            print(f"错误输出: {solve_result.stderr.decode('utf-8', errors='replace')}")
        except Exception as e2:
            print(f"重新运行命令时出错: {e2}")
        sys.exit(1)
    except Exception as e:
        print(f"执行求解脚本时出错: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("数独自动求解流程完成！")
    print("=" * 50)

if __name__ == "__main__":
    main()