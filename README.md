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

## Docker 部署

Dockerfile 直接安装 `skill-registry` Python 包，不进行 Nuitka 编译。构建上下文只包含项目安装需要的 `pyproject.toml`、`README.md`、`LICENSE` 和 `src/`。技能文件不打入镜像；启动时用 bind mount 将 **Docker 主机**上的技能目录挂载为容器内的 `/skills`，服务通过 `SKILLS_DIR=/skills` 扫描它。`HOST_SKILLS_DIR` 必须是 Docker 主机上已存在的绝对路径。每个技能目录需要有 `SKILL.md`，例如 `/srv/skills/my-skill/SKILL.md`。

在项目目录构建并启动本地镜像（PowerShell）：

```powershell
cd E:\lornd\skill_registry
docker build -t skill-registry:local .
$env:HOST_SKILLS_DIR = 'E:\path\to\skills'
docker compose up -d
Invoke-RestMethod http://127.0.0.1:5000/search_skills
```

如果 Docker 运行在 Linux 服务器上，可只把 `compose.yaml` 放到服务器，再指定已推送的镜像和服务器上的技能目录：

```sh
export REGISTRY_IMAGE='your-dockerhub-user/skill-registry:0.1.0'
export HOST_SKILLS_DIR='/srv/skills'
docker compose up -d
```

服务默认只在 Docker 主机的 `127.0.0.1:5000` 提供服务，文档位于 `http://127.0.0.1:5000/docs`。可用 `REGISTRY_PORT` 修改主机端口。现有 API 没有鉴权，并提供 `/discover_skills` 和 `/execute_resource`；若要从别的机器访问，应先设置网络访问控制或带鉴权的反向代理，再将 `REGISTRY_BIND_ADDRESS` 设为 `0.0.0.0`。

挂载默认只读。容器以 UID 10001 运行，主机目录及文件需要允许该用户读取，目录还需要允许遍历。技能脚本不能写入 `/skills`；如需写文件，应另行挂载输出目录并配置权限。技能目录变动仍由现有自动刷新机制读取。`.py` 技能资源会使用容器内运行服务的 Python 解释器执行。

如需把镜像推送到 Docker Hub，可在构建后执行：

```powershell
docker login
docker tag skill-registry:local your-dockerhub-user/skill-registry:0.1.0
docker push your-dockerhub-user/skill-registry:0.1.0
```

**源码可见性：**最终镜像包含 `skill_registry` 的 `.py` 模块。`.dockerignore` 排除了 `.env` 等无关构建文件，技能目录也未打入镜像，但公开镜像的拉取者可以查看注册中心源码。若源码不应公开，请使用 Docker Hub 私有仓库或其他私有镜像仓库。
