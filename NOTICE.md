# 第三方依赖声明

本项目自身代码以 [MIT License](LICENSE) 发布。

## iztro

运行时会调用开源排盘库 iztro 完成星盘计算。

- 名称: iztro
- 作者: SylarLong
- 仓库: https://github.com/SylarLong/iztro
- 许可: MIT License
- 版权: Copyright (c) 2023-2026 iztro contributors

项目的排盘算法、星曜数据、农历转换等核心逻辑均来自 iztro。
本项目在其之上构建了 Python 桥接层、SQLite 数据层、REST API 与 Web 管理界面。

iztro 以 MIT 协议发布，与本项目协议兼容。

## 其他依赖

| 依赖 | 许可 |
|---|---|
| Next.js | MIT |
| React | MIT |
| FastAPI | MIT |
| Pydantic | MIT |
| Uvicorn | BSD-3-Clause |
| SQLite | Public Domain |

各依赖的具体许可条款请参见其各自的仓库。
