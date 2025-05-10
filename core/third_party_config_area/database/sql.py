# core/third_party_config_area/database/sql.py
"""设备模板和已配置点表相关的SQL语句"""

TEMPLATE_SQL = {
    'CREATE_TEMPLATES_TABLE': '''
    CREATE TABLE IF NOT EXISTS third_device_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE, -- 模板名称需要唯一
        prefix TEXT, -- 保留此列以避免修改现有表结构，但应用层不再使用
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
        sll_setpoint TEXT,
        sl_setpoint TEXT,
        sh_setpoint TEXT,
        shh_setpoint TEXT,
        FOREIGN KEY(template_id) REFERENCES third_device_templates(id) ON DELETE CASCADE
    )
    ''',
    
    'INSERT_TEMPLATE': '''
    INSERT INTO third_device_templates (name)
    VALUES (?)
    ''',
    
    'UPDATE_TEMPLATE': '''
    UPDATE third_device_templates 
    SET name = ?, updated_at = CURRENT_TIMESTAMP
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
    (template_id, var_suffix, desc_suffix, data_type, sll_setpoint, sl_setpoint, sh_setpoint, shh_setpoint)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''',

    'GET_TEMPLATE_BY_ID': '''
    SELECT id, name, created_at, updated_at
    FROM third_device_templates
    WHERE id = ?
    ''',
    
    'GET_ALL_TEMPLATES': '''
    SELECT id, name, created_at, updated_at
    FROM third_device_templates
    ORDER BY name
    ''',
    
    'GET_TEMPLATE_BY_NAME': '''
    SELECT id, name, created_at, updated_at
    FROM third_device_templates
    WHERE name = ?
    ''',

    'GET_POINTS_BY_TEMPLATE_ID': '''
    SELECT id, template_id, var_suffix, desc_suffix, data_type, sll_setpoint, sl_setpoint, sh_setpoint, shh_setpoint
    FROM third_device_template_points
    WHERE template_id = ?
    '''
}

CONFIGURED_DEVICE_SQL = {
    'CREATE_CONFIGURED_POINTS_TABLE': '''
    CREATE TABLE IF NOT EXISTS configured_device_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL, -- 使用的模板名称 (快照)
        variable_prefix TEXT NOT NULL, -- 应用模板时指定的变量前缀
        description_prefix TEXT NOT NULL DEFAULT '', -- 应用模板时指定的描述前缀
        var_suffix TEXT NOT NULL,    -- 来自模板的点位变量名后缀 (快照)
        desc_suffix TEXT NOT NULL,   -- 来自模板的点位描述后缀 (快照)
        data_type TEXT NOT NULL,     -- 来自模板的点位数据类型 (快照)
        sll_setpoint TEXT,
        sl_setpoint TEXT,
        sh_setpoint TEXT,
        shh_setpoint TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 配置生成时间
        UNIQUE (template_name, variable_prefix, description_prefix, var_suffix) -- 确保在同一配置实例下变量后缀唯一
    )
    ''',

    'INSERT_CONFIGURED_POINTS_BATCH': '''
    INSERT INTO configured_device_points
    (template_name, variable_prefix, description_prefix, var_suffix, desc_suffix, data_type, sll_setpoint, sl_setpoint, sh_setpoint, shh_setpoint)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', # 用于 executemany

    'GET_ALL_CONFIGURED_POINTS': '''
    SELECT id, template_name, variable_prefix, description_prefix, var_suffix, desc_suffix, data_type, sll_setpoint, sl_setpoint, sh_setpoint, shh_setpoint, created_at
    FROM configured_device_points
    ORDER BY template_name, variable_prefix, description_prefix, var_suffix
    ''',

    'DELETE_ALL_CONFIGURED_POINTS': '''
    DELETE FROM configured_device_points
    ''',

    'DELETE_CONFIGURED_POINTS_BY_TEMPLATE_AND_PREFIXES': '''
    DELETE FROM configured_device_points
    WHERE template_name = ? AND variable_prefix = ? AND description_prefix = ?
    ''',

    'GET_CONFIGURATION_SUMMARY_RAW': '''
    SELECT template_name, variable_prefix, description_prefix, COUNT(*) as point_count
    FROM configured_device_points
    GROUP BY template_name, variable_prefix, description_prefix
    ORDER BY template_name, variable_prefix, description_prefix
    ''',

    'CHECK_CONFIGURATION_EXISTS': '''
    SELECT 1 
    FROM configured_device_points
    WHERE template_name = ? AND variable_prefix = ? AND description_prefix = ?
    LIMIT 1
    '''
} 