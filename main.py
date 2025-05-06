"""
深化设计数据查询工具 - 主程序入口
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.third_device import template_db


def setup_logging():
    """配置日志系统"""
    # 使用简单的日志配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

if __name__ == '__main__':
    try:
        # 设置日志
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("应用程序启动")

        # 初始化数据库
        template_db.init_db()
        logger.info("数据库初始化完成")

        # 启动应用
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        logger.info("主窗口已显示")
        
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"程序发生异常: {str(e)}", exc_info=True)