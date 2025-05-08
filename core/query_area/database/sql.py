# core/query_area/database/sql.py
"""PLC模块相关的SQL语句"""

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