# Skill Registry

独立的本地 Skill 注册表，提供 Python API、HTTP API 和 Skill 资源执行接口。

## 安装

在 PowerShell 中，从本仓库目录运行：

```powershell
cd E:\lornd\skill_registry
uv venv
uv pip install -e .
```

其他 Python 项目可以通过 `uv add --editable E:\lornd\skill_registry` 安装本地仓库。Python 导入路径是 `skill_registry`，例如：

```python
from skill_registry.app import create_app
from skill_registry.client import SkillRegistryClient
from skill_registry.registry import SkillRegistry
```

## 启动服务

`SKILLS_DIR` 指向需要扫描的 Skill 目录；未指定时扫描启动目录下的 `.skills`。一个包含 `SKILL.md` 的目录会被识别为一个 Skill。

```powershell
cd E:\lornd\skill_registry
$env:SKILLS_DIR = 'E:\lornd\agentic-cua\.skills'
uv run skill-registry
```

服务默认监听 `0.0.0.0:5000`，OpenAPI 文档位于 `http://localhost:5000/docs`。可通过 `HOST` 和 `PORT` 环境变量修改监听地址和端口，也可使用 `uvicorn skill_registry.app:app` 启动。

`create_app({"SKILLS_DIR": "...", "EXECUTION_PROVIDER": provider})` 可用于嵌入其他服务。默认资源执行器在资源文件所在目录运行脚本；执行 `.py` 文件时使用当前服务的 Python 解释器。

## 技能热更新

服务运行期间会自动重新扫描已注册的技能根目录，默认间隔 1 秒。新增或删除 Skill、修改 `SKILL.md`、新增或删除资源文件后，后续请求会读取更新后的注册表；资源文件的内容本来就是按请求读取，因此内容修改无需等待扫描。通过 `/discover_skills` 添加的目录也会一起自动刷新。

可在启动前设置扫描间隔（秒）：

```powershell
$env:SKILLS_REFRESH_INTERVAL = '2'
```

如果扫描时某个 `SKILL.md` 暂时无法解析，服务会保留上一次完整快照，并在下一轮重试。此功能刷新的是 Skill 文件及注册表；修改注册中心自身的 Python 代码仍需重启服务。

## 项目结构

```text
skill_registry/
├── pyproject.toml
├── README.md
└── src/
    └── skill_registry/
        ├── app.py
        ├── client.py
        ├── registry.py
        ├── routes.py
        └── execution/
```
