"""简道云API处理模块"""

import configparser
import requests
import logging
from typing import List, Dict, Any

class JianDaoYunAPI:
    def __init__(self, config_file: str = 'config.ini'):
        self.config = configparser.ConfigParser()
        try:
            # 使用UTF-8编码读取配置文件
            self.config.read(config_file, encoding='utf-8')
            self.jdy_config = self.config['JianDaoYun']
            
            # 初始化API配置
            self.api_base_url = self.jdy_config['api_base_url']
            self.api_key = self.jdy_config['api_key']
            self.app_id = self.jdy_config['app_id']
            self.entry_id = self.jdy_config['entry_id']
            
            # 获取字段配置
            self.project_fields = self.jdy_config['project_fields'].split(',')
            
        except Exception as e:
            logging.error(f"读取配置文件失败: {str(e)}")
            raise
        
    def query_data(self, project_no: str = None) -> List[Dict[str, Any]]:
        """
        查询简道云数据
        :param project_no: 项目编号（用于过滤）
        :return: 数据列表
        """
        all_data = []
        last_data_id = None
        batch_size = 100  # API限制

        # 构建过滤条件
        filter_cond = []
        if project_no:
            filter_cond.append({
                "field": "_widget_1635777114935",  # 项目编号字段
                "type": "text",
                "method": "eq",
                "value": [project_no]
            })

        while True:
            # 构建请求参数
            params = {
                "app_id": self.app_id,
                "entry_id": self.entry_id,
                "fields": self.project_fields,  # 使用项目字段列表
                "limit": batch_size
            }
            
            # 添加过滤条件
            if filter_cond:
                params["filter"] = {
                    "rel": "and",
                    "cond": filter_cond
                }

            # 添加分页标识
            if last_data_id:
                params["data_id"] = last_data_id

            try:
                # 发送请求
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(
                    f"{self.api_base_url}/app/entry/data/list",
                    json=params,
                    headers=headers
                )
                response.raise_for_status()
                
                # 解析响应数据
                result = response.json()
                current_batch = result.get('data', [])
                
                # 添加到结果集
                all_data.extend(current_batch)
                
                # 检查是否需要继续获取下一页
                if len(current_batch) < batch_size:
                    break
                    
                # 获取最后一条数据的ID
                last_data_id = current_batch[-1]['_id']
                
            except Exception as e:
                logging.error(f"获取简道云数据失败: {str(e)}")
                raise

        return all_data

    def query_site_devices(self, site_name: str) -> List[Dict[str, Any]]:
        """
        获取场站的设备数据
        :param site_name: 场站名称
        :return: 设备数据列表
        """
        # print(f"\n开始查询场站 '{site_name}' 的设备数据")
        all_data = []
        last_data_id = None
        batch_size = 100  # API限制

        # 构建过滤条件
        filter_cond = [{
            "field": "_widget_1635777114991",  # 场站字段
            "type": "String",
            "method": "eq",
            "value": [site_name]
        }]

        while True:
            # 构建请求参数
            params = {
                "app_id": self.app_id,
                "entry_id": self.entry_id,
                "fields": ["_widget_1635777115095"],  # 设备清单字段
                "limit": batch_size,
                "filter": {
                    "rel": "and",
                    "cond": filter_cond
                }
            }

            # 添加分页标识
            if last_data_id:
                params["data_id"] = last_data_id

            # print("\n发送的请求参数:")
            # print(params)

            try:
                # 发送请求
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(
                    f"{self.api_base_url}/app/entry/data/list",
                    json=params,
                    headers=headers
                )
                response.raise_for_status()
                
                # 解析响应数据
                result = response.json()
                # print("\n收到的API响应:")
                # print(result)
                
                current_batch = result.get('data', [])
                # print(f"\n当前批次数据数量: {len(current_batch)}")
                
                # 添加到结果集
                all_data.extend(current_batch)
                
                # 检查是否需要继续获取下一页
                if len(current_batch) < batch_size:
                    break
                    
                # 获取最后一条数据的ID
                last_data_id = current_batch[-1]['_id']
                
            except Exception as e:
                # print(f"\n发生错误: {str(e)}")
                logging.error(f"获取场站设备数据失败: {str(e)}")
                raise

        # print(f"\n总共获取到 {len(all_data)} 条设备数据")
        return all_data

    def upload_hmi_points(self, points_data: List[Dict], hmi_type: str):
        """
        上传HMI点表（待实现）
        :param points_data: 点表数据
        :param hmi_type: HMI类型
        """
        pass

    def upload_plc_points(self, points_data: List[Dict], plc_type: str):
        """
        上传PLC点表（待实现）
        :param points_data: 点表数据
        :param plc_type: PLC类型
        """
        pass 