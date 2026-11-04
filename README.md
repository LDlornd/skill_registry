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

## 资源读取协议

`GET /load_resource?skill_name=mesh-analysis&relative_path=scripts/mesh_tool.py` 读取指定技能目录内的单个 UTF-8 文本文件。先通过 `/load_skill` 获取 `skill.resources`，再使用其中的具体文件路径；目录本身不能作为资源读取。

`/load_resource` 的读取成功和业务失败均返回 **HTTP 200**，调用方必须检查 JSON 的 `success`，不能只根据 HTTP 状态判断成功。其他接口的状态码约定保持不变。

成功响应保留原有的 `skill_name`、`relative_path`、`content` 字段：

```json
{
  "success": true,
  "skill_name": "mesh-analysis",
  "relative_path": "scripts/mesh_tool.py",
  "content": "资源文件内容",
  "error": null
}
```

失败响应的 `content` 为 `null`，错误放在 `error.code` 和 `error.message` 中：

```json
{
  "success": false,
  "skill_name": "mesh-analysis",
  "relative_path": ".",
  "content": null,
  "error": {
    "code": "resource_not_file",
    "message": "Resource path is a directory for skill mesh-analysis: '.'. Choose a file path from /load_skill skill.resources."
  }
}
```

错误代码包括 `bad_request`（参数无效）、`skill_not_found`、`resource_not_found`、`resource_not_file`（目标是目录）、`invalid_resource_path`（越界）、`invalid_resource_encoding`（非 UTF-8 文本）和 `resource_read_failed`（文件读取失败）。参数缺失时，对应的请求字段为 `null`。空文件仍是成功结果，`content` 为 `""`。

注册中心自带的 `SkillRegistryClient.load_resource()` 继续返回原有的 `success: 1/0` 和 `content` 或 `message` 包装。直接使用 `Skill.load_resource()` 时，读取失败会抛出异常，而不再返回 `ERROR: ...` 文本。

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
