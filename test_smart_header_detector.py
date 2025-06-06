"""
测试智能表头检测器的适应性
"""

from core.document_parser.smart_header_detector import SmartHeaderDetector

def test_different_header_formats():
    """测试不同的表头格式"""
    detector = SmartHeaderDetector()
    
    # 测试用例1：标准格式
    print("=== 测试用例1：标准格式 ===")
    headers1 = ['序号', '仪表位号', '检测点名称', '信号类型', '信号范围', '数据范围', '单位', '备注']
    result1 = detector.detect_headers(headers1)
    print(f"结果: {result1}")
    
    # 测试用例2：英文格式
    print("\n=== 测试用例2：英文格式 ===")
    headers2 = ['No', 'Tag', 'Description', 'Type', 'Signal Range', 'Data Range', 'Unit', 'Remarks']
    result2 = detector.detect_headers(headers2)
    print(f"结果: {result2}")
    
    # 测试用例3：混合格式
    print("\n=== 测试用例3：混合格式 ===")
    headers3 = ['编号', '位号Tag', '名称Description', '类型Type', '量程', '工程值', '单位Unit', '说明']
    result3 = detector.detect_headers(headers3)
    print(f"结果: {result3}")
    
    # 测试用例4：变体格式
    print("\n=== 测试用例4：变体格式 ===")
    headers4 = ['NO', '设备位号', '功能描述', '通道类型', '输入范围', '测量值', '工程单位', '其他']
    result4 = detector.detect_headers(headers4)
    print(f"结果: {result4}")
    
    # 测试用例5：简化格式
    print("\n=== 测试用例5：简化格式 ===")
    headers5 = ['位号', '名称', '类型', '范围']
    result5 = detector.detect_headers(headers5)
    print(f"结果: {result5}")
    
    # 测试用例6：复杂格式（包含不相关列）
    print("\n=== 测试用例6：复杂格式 ===")
    headers6 = ['项目', '仪表位号', '检测点名称', '安装位置', '信号类型', '信号范围', '数据范围', '单位', '供电方式', '隔离器', '厂家', '备注']
    result6 = detector.detect_headers(headers6)
    print(f"结果: {result6}")

if __name__ == "__main__":
    test_different_header_formats()
