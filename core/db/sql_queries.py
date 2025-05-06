"""SQL语句管理模块"""

# PLC模块相关SQL
PLC_SQL = {
    'CREATE_SERIES_TABLE': '''
    CREATE TABLE IF NOT EXISTS plc_series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    ''',
    
    'CREATE_BACKPLANES_TABLE': '''
    CREATE TABLE IF NOT EXISTS backplanes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id INTEGER NOT NULL,
        model TEXT NOT NULL,
        slots INTEGER NOT NULL,
        description TEXT,
        UNIQUE(series_id, model),
        FOREIGN KEY(series_id) REFERENCES plc_series(id)
    )
    ''',
    
    'CREATE_MODULES_TABLE': '''
    CREATE TABLE IF NOT EXISTS modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id INTEGER NOT NULL,
        model TEXT NOT NULL,
        module_type TEXT NOT NULL,
        channels INTEGER NOT NULL,
        description TEXT,
        UNIQUE(series_id, model),
        FOREIGN KEY(series_id) REFERENCES plc_series(id)
    )
    ''',
    
    'INSERT_SERIES': '''
    INSERT INTO plc_series (name, description)
    VALUES (?, ?)
    ''',
    
    'DELETE_SERIES': '''
    DELETE FROM plc_series WHERE id = ?
    ''',
    
    'GET_SERIES_BY_NAME': '''
    SELECT id, name, description 
    FROM plc_series 
    WHERE name = ?
    ''',
    
    'GET_ALL_SERIES': '''
    SELECT name, description 
    FROM plc_series 
    ORDER BY name
    ''',
    
    'INSERT_MODULE': '''
    INSERT INTO modules 
    (series_id, model, module_type, channels, description)
    VALUES (?, ?, ?, ?, ?)
    ''',
    
    'DELETE_MODULE': '''
    DELETE FROM modules 
    WHERE series_id = ? AND model = ?
    ''',
    
    'GET_MODULES_BY_TYPE': '''
    SELECT model, module_type, channels, description
    FROM modules
    WHERE series_id = ? AND module_type = ?
    ORDER BY model
    ''',
    
    'GET_MODULE_INFO': '''
    SELECT model, module_type, channels, description
    FROM modules
    WHERE series_id = ? AND model = ?
    '''
}

# 设备模板相关SQL
TEMPLATE_SQL = {
    'CREATE_TEMPLATES_TABLE': '''
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''',
    
    'CREATE_POINTS_TABLE': '''
    CREATE TABLE IF NOT EXISTS points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        data_type TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(template_id) REFERENCES templates(id)
    )
    ''',
    
    'INSERT_TEMPLATE': '''
    INSERT INTO templates (name, description)
    VALUES (?, ?)
    ''',
    
    'UPDATE_TEMPLATE': '''
    UPDATE templates 
    SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    ''',
    
    'DELETE_TEMPLATE': '''
    DELETE FROM templates WHERE id = ?
    ''',
    
    'GET_ALL_TEMPLATES': '''
    SELECT id, name, description, created_at, updated_at
    FROM templates
    ORDER BY name
    ''',
    
    'GET_TEMPLATE_BY_NAME': '''
    SELECT id, name, description, created_at, updated_at
    FROM templates
    WHERE name = ?
    '''
} 