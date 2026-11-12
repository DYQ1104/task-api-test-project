# 任务管理系统 API 自动化测试项目

## 项目简介

一个面向测试开发实践的轻量任务管理 REST API 与接口自动化测试项目。服务使用 FastAPI + SQLite；测试使用 pytest + requests；覆盖认证、项目/任务 CRUD、输入校验、越权访问和级联删除。

## 环境与启动

Python 3.11+。Windows PowerShell：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:TASK_API_DB = 'data/task_api.sqlite3'
$env:TASK_API_TOKEN_SECRET = 'local-only-change-this-secret'
uvicorn app.main:app --reload
```

API 文档：<http://127.0.0.1:8000/docs>；健康检查：`GET /health`。

## 自动化测试与报告

```powershell
python -m pytest
```

pytest fixture 会自行启动服务，使用单独的 `data/pytest.sqlite3` 测试库，完成后关闭服务。HTML 报告输出到 `reports/latest.html`。也可运行基础链路自测：`python scripts/self_test.py`；阶段验收：`python scripts/acceptance.py`。

## 核心规则

- 用户名 3–30 字符，大小写不敏感唯一；密码 8–64 字符并以 PBKDF2 哈希保存。
- 登录使用带 HMAC 签名与过期时间的 Bearer token。生产部署必须设置高熵 `TASK_API_TOKEN_SECRET`。
- 所有项目和任务资源必须认证；跨用户资源统一返回 404。
- 项目删除级联删除任务。任务状态限 `todo`、`doing`、`done`。
- SQLite 文件路径通过 `TASK_API_DB` 配置。

## 测试覆盖

当前 pytest 覆盖健康检查、注册冲突、错误密码、无 token/无效/过期 token、项目 CRUD、项目越权、任务状态、任务更新查询及项目级联删除。测试运行验证：11 passed。请求参数校验失败返回 400 与统一 VALIDATION_ERROR 结构。

## 缺陷案例（演示脚本）

可以将任务表的 `ON DELETE CASCADE` 暂时改为 `ON DELETE RESTRICT`，运行 `test_task_crud_and_cascade`，删除项目时会因残留任务失败；恢复级联规则后测试通过。该案例展示了业务规则、关联数据校验与回归验证过程。演示后不要保留错误规则。

## 持续集成

GitHub Actions 在 push 和 pull request 触发 pytest，并通过 artifact 上传 HTML 报告。失败时工作流失败，`if: always()` 确保报告步骤仍执行。

Security note: This is a learning project, not production-ready. APP_ENV=production requires a high-entropy TASK_API_TOKEN_SECRET; without it startup fails. Development uses an ephemeral process secret, so restart invalidates tokens. Rate limiting, token revocation, audit logging and production migrations are not implemented. CI uses Ubuntu and pytest starts the service through sys.executable with a per-session temporary database.
