# core/third_party_config_area/database/sql.py
"""设备模板和已配置点表相关的SQL语句"""

TEMPLATE_SQL = {
    'CREATE_TEMPLATES_TABLE': '''
    CREATE TABLE IF NOT EXISTS third_device_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE, -- 模板名称需要唯一
        prefix TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''',
    
    'CREATE_POINTS_TABLE': '''
    CREATE TABLE IF NOT EXISTS third_device_template_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        var_suffix TEXT NOT NULL,
        desc_suffix TEXT NOT NULL,
        data_type TEXT NOT NULL,
        init_value TEXT DEFAULT '0',
        power_protection INTEGER DEFAULT 0,
        forcible INTEGER DEFAULT 1,
        soe_enabled INTEGER DEFAULT 0,
        FOREIGN KEY(template_id) REFERENCES third_device_templates(id) ON DELETE CASCADE
    )
    ''',
    
    'INSERT_TEMPLATE': '''
    INSERT INTO third_device_templates (name, prefix)
    VALUES (?, ?)
    ''',
    
    'UPDATE_TEMPLATE': '''
    UPDATE third_device_templates 
    SET name = ?, prefix = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    ''',
    
    'DELETE_TEMPLATE': '''
    DELETE FROM third_device_templates WHERE id = ?
    ''',

    'DELETE_POINTS_BY_TEMPLATE_ID': '''
    DELETE FROM third_device_template_points WHERE template_id = ?
    ''', 
    
    'INSERT_POINT': '''
    INSERT INTO third_device_template_points
    (template_id, var_suffix, desc_suffix, data_type, init_value, power_protection, forcible, soe_enabled)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''',

    'GET_TEMPLATE_BY_ID': '''
    SELECT id, name, prefix, created_at, updated_at
    FROM third_device_templates
    WHERE id = ?
    ''',
    
    'GET_ALL_TEMPLATES': '''
    SELECT id, name, prefix, created_at, updated_at
    FROM third_device_templates
    ORDER BY name
    ''',
    
    'GET_TEMPLATE_BY_NAME': '''
    SELECT id, name, prefix, created_at, updated_at
    FROM third_device_templates
    WHERE name = ?
    ''',

    'GET_POINTS_BY_TEMPLATE_ID': '''
    SELECT id, template_id, var_suffix, desc_suffix, data_type, 
           init_value, power_protection, forcible, soe_enabled
    FROM third_device_template_points
    WHERE template_id = ?
    '''
}

CONFIGURED_DEVICE_SQL = {
    'CREATE_CONFIGURED_POINTS_TABLE': '''
    CREATE TABLE IF NOT EXISTS configured_device_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL, -- 使用的模板名称 (快照)
        device_prefix TEXT NOT NULL, -- 应用模板时指定设备/变量前缀
        var_suffix TEXT NOT NULL,    -- 来自模板的点位变量名后缀 (快照)
        desc_suffix TEXT NOT NULL,   -- 来自模板的点位描述后缀 (快照)
        data_type TEXT NOT NULL,     -- 来自模板的点位数据类型 (快照)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 配置生成时间
        -- 可以考虑添加 UNIQUE (device_prefix, var_suffix) 约束，如果一个前缀下的变量后缀必须唯一
    )
    ''',

    'INSERT_CONFIGURED_POINTS_BATCH': '''
    INSERT INTO configured_device_points
    (template_name, device_prefix, var_suffix, desc_suffix, data_type)
    VALUES (?, ?, ?, ?, ?)
    ''', # 用于 executemany

    'GET_ALL_CONFIGURED_POINTS': '''
    SELECT id, template_name, device_prefix, var_suffix, desc_suffix, data_type, created_at
    FROM configured_device_points
    ORDER BY device_prefix, var_suffix -- 或其他排序方式
    ''',

    'DELETE_ALL_CONFIGURED_POINTS': '''
    DELETE FROM configured_device_points
    ''',

    'GET_CONFIGURATION_SUMMARY': '''
    SELECT template_name, device_prefix, COUNT(*) as point_count
    FROM configured_device_points
    GROUP BY template_name, device_prefix
    ORDER BY template_name, device_prefix
    '''
} 