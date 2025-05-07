"""SQL语句管理模块"""

# PLC模块相关SQL
PLC_SQL = {
    'CREATE_SERIES_TABLE': '''
    CREATE TABLE IF NOT EXISTS hollysys_plc_series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''',
    
    'CREATE_BACKPLANES_TABLE': '''
    CREATE TABLE IF NOT EXISTS hollysys_plc_backplanes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT NOT NULL,
        slots INTEGER NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''',
    
    'CREATE_MODULES_TABLE': '''
    CREATE TABLE IF NOT EXISTS hollysys_plc_modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id INTEGER,
        model TEXT NOT NULL,
        module_type TEXT NOT NULL,
        channels INTEGER DEFAULT 0,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (series_id) REFERENCES hollysys_plc_series (id) ON DELETE CASCADE
    )
    ''',
    
    'INSERT_SERIES': '''
    INSERT INTO hollysys_plc_series (name, description)
    VALUES (?, ?)
    ''',
    
    'DELETE_SERIES': '''
    DELETE FROM hollysys_plc_series WHERE id = ?
    ''',
    
    'GET_SERIES_BY_NAME': '''
    SELECT id, name, description, created_at
    FROM hollysys_plc_series 
    WHERE name = ?
    ''',
    
    'GET_ALL_SERIES': '''
    SELECT id, name, description, created_at
    FROM hollysys_plc_series 
    ORDER BY name
    ''',
    
    'INSERT_MODULE': '''
    INSERT INTO hollysys_plc_modules 
    (series_id, model, module_type, channels, description)
    VALUES (?, ?, ?, ?, ?)
    ''',
    
    'DELETE_MODULE': '''
    DELETE FROM hollysys_plc_modules 
    WHERE series_id = ? AND model = ?
    ''',
    
    'GET_MODULES_BY_TYPE': '''
    SELECT id, series_id, model, module_type, channels, description, created_at
    FROM hollysys_plc_modules
    WHERE series_id = ? AND module_type = ?
    ORDER BY model
    ''',
    
    'GET_MODULE_INFO': '''
    SELECT id, series_id, model, module_type, channels, description, created_at
    FROM hollysys_plc_modules
    WHERE series_id = ? AND model = ?
    ''',

    'GET_MODULES_BY_SERIES_ID': '''
    SELECT id, series_id, model, module_type, channels, description, created_at
    FROM hollysys_plc_modules
    WHERE series_id = ?
    ORDER BY model
    '''
}

# 设备模板相关SQL
TEMPLATE_SQL = {
    'CREATE_TEMPLATES_TABLE': '''
    CREATE TABLE IF NOT EXISTS third_device_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        prefix TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''',
    
    'CREATE_POINTS_TABLE': '''
    CREATE TABLE IF NOT EXISTS third_device_template_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER,
        var_suffix TEXT,
        desc_suffix TEXT,
        data_type TEXT,
        init_value TEXT DEFAULT '0',
        power_protection INTEGER DEFAULT 0,
        forcible INTEGER DEFAULT 1,
        soe_enabled INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    
    'GET_ALL_TEMPLATES': '''
    SELECT id, name, prefix, created_at, updated_at
    FROM third_device_templates
    ORDER BY name
    ''',
    
    'GET_TEMPLATE_BY_NAME': '''
    SELECT id, name, prefix, created_at, updated_at
    FROM third_device_templates
    WHERE name = ?
    '''
} 