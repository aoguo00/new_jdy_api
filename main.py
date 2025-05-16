"""
深化设计数据查询工具 - 主程序入口
"""

import sys
import os
import logging
import configparser
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow



def setup_logging():
    """配置日志系统，从 config.ini 读取配置"""
    config = configparser.ConfigParser()
    # 通常 config.ini 应该位于项目根目录或者一个可预知的位置
    # 这里我们假设它在当前工作目录或脚本的上一级目录的 config.ini
    config_path = 'config.ini' 
    if not os.path.exists(config_path):
        # 如果 main.py 在某个子目录，config.ini 在项目根目录
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
        if not os.path.exists(config_path):
            print(f"警告: 配置文件 {config_path} 未找到，使用默认日志配置。")
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            return

    try:
        config.read(config_path, encoding='utf-8') # 指定UTF-8编码读取配置文件
        
        log_settings = config['Logging']
        log_level_str = log_settings.get('log_level', 'INFO').upper()
        log_file = log_settings.get('log_file', 'app.log')
        max_log_size = int(log_settings.get('max_log_size', 5*1024*1024)) # 默认5MB
        backup_count = int(log_settings.get('backup_count', 3))

        # 将字符串日志级别转换为 logging模块的常量
        numeric_level = getattr(logging, log_level_str, logging.INFO)

        # 获取根logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level) # 设置根logger的级别

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 创建并配置 RotatingFileHandler (用于文件输出)
        # 确保日志文件路径是绝对的或相对于一个已知的基础路径
        if not os.path.isabs(log_file):
            log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_file) # 假设log_file在main.py同级或相对路径
            # 或者，如果想让它在项目根目录的 db 文件夹旁边
            # log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), log_file)
        else:
            log_file_path = log_file
        
        # 确保日志文件所在的目录存在
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = RotatingFileHandler(
            log_file_path, 
            maxBytes=max_log_size, 
            backupCount=backup_count,
            encoding='utf-8' # 推荐使用utf-8编码
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level) # 文件处理器也遵循配置的级别
        root_logger.addHandler(file_handler)

        # 创建并配置 StreamHandler (用于控制台输出)
        # 控制台输出的级别也可以独立于文件日志级别，或者遵循全局级别
        # 如果希望控制台输出更少，可以将其级别设置得更高，例如 logging.WARNING
        # 这里我们让它也遵循 config.ini 中的 log_level
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level) # 控制台处理器也遵循配置的级别
        root_logger.addHandler(console_handler)
        
        # 如果之前使用了 basicConfig，它可能已经添加了一个默认的 StreamHandler。
        # 为避免重复输出到控制台，可以考虑移除根logger上已有的handlers（如果basicConfig被调用过）
        # 但由于我们是在 setup_logging 中完全重写，所以不需要太担心之前的basicConfig的影响，
        # 只要保证 setup_logging 是主要的日志配置入口。

        logging.info(f"日志系统已配置：级别={log_level_str}, 文件='{log_file_path}'")

    except Exception as e:
        # 如果日志配置失败，回退到基本配置，确保至少有日志输出
        print(f"配置日志系统时发生错误: {e}。将使用默认日志配置。")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    """主函数"""
    setup_logging() 
    logger = logging.getLogger(__name__)

    try:
        logger.info("应用程序启动")

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        logger.info("主窗口已显示")

        # 考虑在这里连接 aboutToQuit 信号来关闭日志，这是更Qt友好的方式
        # def on_about_to_quit():
        #     logger.info("QApplication aboutToQuit: 正在关闭日志...")
        #     logging.shutdown()
        # app.aboutToQuit.connect(on_about_to_quit)

        exit_code = app.exec()
        logger.info(f"应用程序事件循环结束，退出代码: {exit_code}")
        # 在这里关闭日志，覆盖正常退出路径
        logging.shutdown()
        sys.exit(exit_code)

    except SystemExit as se: 
        logger.info(f"应用程序通过 SystemExit 退出，代码: {se.code if se.code is not None else 'N/A'}")
        # 确保日志在退出前关闭
        logging.shutdown()
        raise 
    except Exception as e:
        logger.error(f"主函数中发生未捕获的顶层异常: {e}", exc_info=True)
        # 确保日志在退出前关闭
        logging.shutdown()
        sys.exit(1) 

if __name__ == '__main__':
    main()