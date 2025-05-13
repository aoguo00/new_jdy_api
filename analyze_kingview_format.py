import pandas as pd
import os

# --- 用户需要修改的部分 ---
# 请将下面的路径替换为您本地的亚控示例Excel文件（包含数据词典和IO Server表）的完整路径
# 例如: r"C:\\Users\\YourUser\\Desktop\\亚控导出示例.xlsx" 或 "/home/user/亚控导出示例.xlsx"
file_path = "./数据词典点表.xls"
# --- 修改结束 ---

def analyze_excel_structure(filepath):
    """
    读取Excel文件的结构：所有Sheet名称及其第一行（表头）的列名。

    参数:
        filepath (str): Excel文件的路径。
    """
    if not os.path.exists(filepath):
        print(f"错误：文件未找到 -> {filepath}")
        return

    print(f"开始分析文件: {filepath}\\n{'='*30}")

    try:
        xls = pd.ExcelFile(filepath)
        sheet_names = xls.sheet_names
        print(f"文件包含 {len(sheet_names)} 个 Sheet 页:")
        print("\\n".join([f"- {name}" for name in sheet_names]))
        print(f"\\n{'='*30}\\n各 Sheet 页的表头（第一行列名）：\\n")

        for sheet_name in sheet_names:
            try:
                # 读取第一个Sheet（nrows=0 只读取表头信息到 columns）
                df_header = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
                headers = list(df_header.columns)
                print(f"--- Sheet: '{sheet_name}' ---")
                print(f"列名: {headers}")
                print("-" * (len(sheet_name) + 12)) # 分隔线
                print() # 空行增加可读性

            except Exception as e_sheet:
                print(f"--- Sheet: '{sheet_name}' ---")
                print(f"读取表头时出错: {e_sheet}")
                print("-" * (len(sheet_name) + 12))
                print()

    except Exception as e_file:
        print(f"读取Excel文件时发生错误: {e_file}")

if __name__ == "__main__":
    if file_path == "请替换为您的亚控示例文件路径.xlsx":
        print("错误：请先修改脚本中的 'file_path' 变量，指向您的示例文件路径。")
    else:
        analyze_excel_structure(file_path) 