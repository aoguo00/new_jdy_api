# 验证打包后PLC配置保存功能

## 测试步骤

### 1. 准备测试环境
1. 将 `dist/main.exe` 复制到一个新的测试目录（例如：`C:\test_plc_app\`）
2. 确保测试目录有写入权限

### 2. 首次运行测试
1. 双击运行 `main.exe`
2. 程序应该正常启动（无控制台窗口）
3. 检查exe所在目录，应该自动创建以下结构：
   ```
   C:\test_plc_app\
   ├── main.exe
   ├── app.log (日志文件)
   └── db\
       └── plc_configs\  (PLC配置目录)
           └── backups\  (备份目录)
   ```

### 3. 保存PLC配置测试
1. 在程序中进行以下操作：
   - 输入项目编号查询项目
   - 选择一个场站
   - 切换到"PLC硬件配置"选项卡
   - 添加一些PLC模块配置
   - 点击"应用配置"保存

2. 检查配置文件是否生成：
   - 查看 `C:\test_plc_app\db\plc_configs\` 目录
   - 应该看到类似 `plc_config_场站名.json` 的文件
   - 还应该有对应的 `.full.json` 文件

### 4. 验证配置持久化
1. 关闭程序
2. 再次运行 `main.exe`
3. 选择相同的场站
4. 切换到"PLC硬件配置"选项卡
5. 之前保存的配置应该自动恢复

### 5. 检查日志
查看 `app.log` 文件，应该包含类似以下内容：
```
PLCConfigPersistence 初始化完成，配置目录: C:\test_plc_app\db\plc_configs
成功保存场站 'XXX' 的PLC配置到: C:\test_plc_app\db\plc_configs\plc_config_XXX.json
```

## 预期结果
✅ 程序能正常启动
✅ 自动创建必要的目录结构
✅ PLC配置能正确保存到exe所在目录的 `db\plc_configs\` 文件夹
✅ 重启程序后配置能自动恢复
✅ 日志文件记录正确的路径信息

## 故障排除
- 如果看不到配置文件，检查是否有权限问题
- 查看 `app.log` 中的错误信息
- 确保exe所在目录有写入权限 