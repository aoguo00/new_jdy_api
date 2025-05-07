"""
深化设计数据查询工具 - 主程序入口
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.devices import TemplateManager  # 更新导入语句



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

def main():
    """主函数"""
    try:
        # 设置日志
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("应用程序启动")

        # 初始化模板管理器
        template_manager = TemplateManager()  # 创建实例
        logger.info("模板管理器初始化完成")

        
        # 启动应用
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        logger.info("主窗口已显示")
        
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"程序启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()