# 数据库脚本

## 1 默认形态：SQLite

开发与演示默认使用 SQLite，连接串见 `.env` 的 `DATABASE_URL`，默认 `sqlite:///./data/se_emoji.db`，相对路径以仓库根目录为基准。数据库开启 WAL，支持外键约束与检查约束。

表结构由 SQLAlchemy 模型定义，`backend/app/db/base.py` 的 `create_all` 负责建表，`backend/scripts/seed_demo.py` 负责初始化演示数据：

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\seed_demo.py --reset     # 重建
..\.venv\Scripts\python.exe scripts\seed_demo.py --refresh   # 只平移演示课堂时间
```

## 2 可选形态：MySQL 8

`schema_mysql.sql` 由 SQLAlchemy 模型生成，字段、唯一约束、检查约束与索引与 SQLite 版本一致，差异仅在自增主键为 `BIGINT`、字符集为 `utf8mb4`、存储引擎为 InnoDB。

```bash
mysql -u root -p -e "CREATE DATABASE se_emoji CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
mysql -u root -p se_emoji < db/schema_mysql.sql
```

切换连接串：

```text
DATABASE_URL=mysql+pymysql://se_emoji:change_me@127.0.0.1:3306/se_emoji?charset=utf8mb4
```

该形态需要额外安装驱动：`pip install -r backend/requirements-mysql.txt`。初始化数据仍使用 `seed_demo.py`，不要手工拼接密码哈希。

**如实说明**：MySQL 形态只完成建表脚本与连接配置，未在 MySQL 实例上执行全量回归测试。结题报告与部署说明按此表述，不写成已完整验证。

## 3 表清单

| 表 | 用途 | 关键约束 |
| --- | --- | --- |
| `users` | 用户与角色 | 用户名唯一；角色与状态枚举检查 |
| `courses` | 课程与授课教师 | 同一教师课程名唯一 |
| `class_sessions` | 课堂时间、班级、AI 阈值 | 课程外键；开始时间索引 |
| `schedule_users` | 课堂名单 | 课堂与用户联合唯一 |
| `emoji_records` | 手动与 AI 表情记录 | 事件 ID 唯一；用户、课堂、时间片联合唯一；来源形状检查 |
| `audit_logs` | 关键操作审计 | 结果枚举检查；操作者可为空 |

完整字段与索引见 `schema_mysql.sql`，ER 图与统计口径见 `docs/03-概要设计说明书.md` 与 `docs/04-数据库设计说明书.md`。
