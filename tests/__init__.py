"""StudyPilot 项目联调测试包。

本目录存放后端 API 集成测试（Flask test_client，无需单独启动服务）。

文件说明：
- integration_smoke.py   主路径冒烟：覆盖前端 6 大模块对应的核心接口 happy path
- integration_extended.py  扩展探测：鉴权、参数校验、分页边界、遥测链路等

运行方式（在项目根目录）：
    python -m tests.integration_smoke
    python -m tests.integration_extended
"""
