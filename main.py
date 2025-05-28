"""
工控系统点表管理软件V1.0 - 主程序入口
"""

import sys
import os
import logging
import configparser
from logging.handlers import RotatingFileHandler
# 导入 Path 对象，用于更方便的路径操作
from pathlib import Path

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

# 新增：获取应用程序基础路径的函数
def get_app_base_path() -> Path:
    """
    获取应用程序的基准路径。
    - 如果程序是被冻结（打包）的，则返回可执行文件所在的目录。
    - 否则（作为脚本运行），返回 main.py 所在的目录。
      (根据实际项目结构，您可能需要调整脚本运行时的基准路径，例如 main.py 的上一级)
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的情况 (sys._MEIPASS 是临时解压目录，不应作为数据存储位置)
        # sys.executable 是可执行文件的路径
        return Path(sys.executable).parent
    else:
        # 作为脚本运行或非PyInstaller打包（例如Nuitka的--standalone模式可能不同）
        # 对于脚本运行，通常是 main.py 所在的目录。
        # 如果 config.ini 和 db 文件夹与 main.py 同级，这是合适的。
        # 如果它们在项目根目录，而 main.py 在子目录，则需要 Path(__file__).resolve().parent.parent
        return Path(__file__).resolve().parent


def setup_logging(base_path: Path): # 修改：接收一个 base_path 参数
    """配置日志系统，从 config.ini 读取配置"""
    config = configparser.ConfigParser()
    
    config_path = base_path / 'config.ini' # 使用 base_path 构建 config.ini 的路径

    if not config_path.exists():
        # 如果 main.py 在某个子目录，config.ini 在项目根目录 (这种情况现在由 get_app_base_path 控制)
        # 这里我们假设 get_app_base_path 返回的就是正确的包含 config.ini 的目录
        print(f"警告: 配置文件 {config_path} 未找到，使用默认日志配置。")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        return

    try:
        config.read(config_path, encoding='utf-8') # 指定UTF-8编码读取配置文件
        
        log_settings = config['Logging']
        log_level_str = log_settings.get('log_level', 'INFO').upper()
        log_file_name = log_settings.get('log_file', 'app.log') # 这是文件名或相对子路径
        max_log_size = int(log_settings.get('max_log_size', 5*1024*1024)) # 默认5MB
        backup_count = int(log_settings.get('backup_count', 3))

        numeric_level = getattr(logging, log_level_str, logging.INFO)
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 确保日志文件路径是绝对的，基于 base_path
        log_file_path = base_path / log_file_name # 直接在 base_path 下创建日志文件或其子目录
        
        # 确保日志文件所在的目录存在
        log_dir = log_file_path.parent
        if not log_dir.exists(): # Path.mkdir() 可以处理已存在的情况，但检查一下更明确
            log_dir.mkdir(parents=True, exist_ok=True) # parents=True, exist_ok=True 是好习惯
            
        file_handler = RotatingFileHandler(
            str(log_file_path), # RotatingFileHandler 需要字符串路径
            maxBytes=max_log_size, 
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
        
        logging.info(f"日志系统已配置：级别={log_level_str}, 文件='{log_file_path}'")

    except Exception as e:
        print(f"配置日志系统时发生错误: {e}。将使用默认日志配置。")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    """主函数"""
    # 1. 获取应用程序的基准路径
    app_base_path = get_app_base_path()

    # 2. 配置日志系统，传入基准路径
    setup_logging(app_base_path) 
    logger = logging.getLogger(__name__)

    # 3. 获取数据库路径
    db_path_str = "db/data.db" # 默认值，以防配置文件读取失败或无此项
    try:
        config = configparser.ConfigParser()
        config_file = app_base_path / 'config.ini'
        if config_file.exists():
            config.read(config_file, encoding='utf-8')
            db_path_str = config.get('Database', 'db_path', fallback=db_path_str)
        else:
            logger.warning(f"配置文件 {config_file} 未找到，将使用默认数据库路径: {db_path_str}")
    except Exception as e:
        logger.error(f"读取配置文件获取数据库路径失败: {e}。将使用默认数据库路径: {db_path_str}", exc_info=True)

    # 将从配置文件读取的相对路径（如 "db/data.db"）与 app_base_path 结合
    absolute_db_path = app_base_path / db_path_str
    
    # 确保数据库文件所在的目录存在
    db_dir = absolute_db_path.parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"数据库目录已创建: {db_dir}")

    logger.info(f"应用程序基准路径: {app_base_path}")
    logger.info(f"将使用的绝对数据库路径: {absolute_db_path}")

    try:
        logger.info("应用程序启动")

        app = QApplication(sys.argv)
        # 将绝对数据库路径传递给 MainWindow
        window = MainWindow(db_path=str(absolute_db_path)) # MainWindow 需要修改以接收 db_path
        window.show()
        logger.info("主窗口已显示")

        exit_code = app.exec()
        logger.info(f"应用程序事件循环结束，退出代码: {exit_code}")
        logging.shutdown()
        sys.exit(exit_code)

    except SystemExit as se: 
        logger.info(f"应用程序通过 SystemExit 退出，代码: {se.code if se.code is not None else 'N/A'}")
        logging.shutdown()
        raise 
    except Exception as e:
        logger.error(f"主函数中发生未捕获的顶层异常: {e}", exc_info=True)
        logging.shutdown()
        sys.exit(1) 

if __name__ == '__main__':
    main()