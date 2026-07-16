# Little LLM 项目版本记录

## v16 - 2026-07-04

### 版本状态
✅ **智能文件夹监控系统完成**

### 新增功能
**智能文件夹监控系统（folder_monitor.py）**：
- 用户指定一个或多个文件夹，系统自动长期监控
- 定时扫描（默认300秒）文件夹中所有文档
- 使用本地 DeepSeek-R1 模型理解文档内容，提取摘要和关键词
- 智能检测文件变更（MD5哈希比对），仅处理修改过的文件
- 自动向量化处理后的文档，增量更新向量数据库
- 后台线程自动运行，服务重启后自动恢复监控状态
- 文件元数据持久化到 `data/file_metadata.json`

### 新增 API 端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/monitor/status` | GET | 获取监控状态 |
| `/api/monitor/add_folder` | POST | 添加监控文件夹 |
| `/api/monitor/remove_folder` | POST | 移除监控文件夹 |
| `/api/monitor/set_interval` | POST | 设置扫描间隔 |
| `/api/monitor/enable` | POST | 启用监控 |
| `/api/monitor/disable` | POST | 禁用监控 |
| `/api/monitor/scan_now` | POST | 立即执行一次扫描 |
| `/api/monitor/files` | GET | 获取已监控文件列表 |

### 修改文件
- `backend/folder_monitor.py` - 新增智能文件夹监控模块
- `backend/main.py` - 集成监控API，服务启动时自动恢复监控

---

## v15 - 2026-07-04

### 版本状态
✅ **高优先级BUG修复完成 + 学习缓存系统**

### 修改内容
1. **修复启动BUG**：
   - main.py 第21行 LOG_LEVEL 未定义导致程序无法启动
   - 添加 `from config import LOG_LEVEL, API_PORT`

2. **修复端口配置不一致**：
   - main.py 第456行硬编码 port=8000
   - 改为使用配置项 `port=API_PORT`（9820）

3. **完善百度百科搜索**：
   - multi_sources.py 中 BaiduBaikeSource 原为示意代码
   - 改用 Wikipedia API 实现完整的搜索+摘要提取

4. **新增学习缓存系统**：
   - 新增 learning_cache.py：高频查询自动沉淀
   - 支持查询次数统计、过期淘汰、自动提升为常识

### 修改文件
- `backend/main.py` - 修复启动BUG，统一端口配置
- `backend/multi_sources.py` - 完善百度百科搜索实现
- `backend/learning_cache.py` - 新增学习缓存系统

---

## v14 - 2026-07-03

### 版本状态
✅ **GUI知识库管理功能完成**
