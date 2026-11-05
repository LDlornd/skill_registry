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

维护者手动触发 GitHub Actions 发布镜像。测试人员从内网 Harbor 拉取 `172.16.0.131/thingo-enterprise-agent-platform/skill-registry:latest`，直接用 `docker run` 启动，无需克隆源码或复制 `compose.yaml`。

### 手动发布镜像

首次使用，在本仓库的 **Settings → Secrets and variables → Actions** 添加 `HARBOR_USERNAME` 和 `HARBOR_PASSWORD`，使用有 `thingo-enterprise-agent-platform` 项目推送权限的账号和密码或机器人令牌。隔壁仓库的 Secrets 不会自动共享。

将 [工作流](.github/workflows/publish-image.yml) 提交到默认分支 `main`。之后推送待发布的代码，进入 **Actions → Publish skill-registry image → Run workflow**，选择要发布的分支并运行。普通 `git push` 不会触发发布。

工作流用现有 Dockerfile 构建 `linux/amd64` 镜像，并通过 `agent-network` 工作流使用的地址推送到 `120.26.140.44:80/thingo-enterprise-agent-platform/skill-registry:latest`。运行成功后，在构建日志中查看推送的 digest。每次发布会更新同一标签，测试机上的容器由同事自行更新。镜像包含服务源码；`.env` 和宿主机上的技能文件不打入镜像。

测试命令假设 `120.26.140.44:80` 和 `172.16.0.131` 是同一个 Harbor 的发布和拉取入口。首次发布后，在测试机拉取并比较输出的 digest 与 Actions 日志是否一致。

### 拉取并启动测试容器

在能访问 Harbor 的 Linux amd64 Docker 主机上执行。若内网 Harbor 使用 HTTP，先按 [Docker 文档](https://docs.docker.com/reference/cli/dockerd/#insecure-registries) 将 `172.16.0.131` 加入测试机 Docker daemon 的 `insecure-registries`。私有镜像需先用有拉取权限的账号运行 `docker login 172.16.0.131`。在运行命令的目录创建 `.env`，例如：

```dotenv
SKILLS_REFRESH_INTERVAL=1
```

将 `HOST_SKILLS_DIR` 改为 **Docker 主机**上已存在的技能目录的绝对路径，例如 `/srv/skills`，其中可放置 `/srv/skills/my-skill/SKILL.md`。`--env-file` 只为容器设置环境变量；挂载源路径和主机端口在 `docker run` 命令中设置。镜像已设置 `SKILLS_DIR=/skills`、`HOST=0.0.0.0` 和 `PORT=5000`。

```sh
IMAGE=172.16.0.131/thingo-enterprise-agent-platform/skill-registry:latest
HOST_SKILLS_DIR=/srv/skills
docker pull "$IMAGE"
```

拉取成功后，如果旧服务由 Compose 启动，先到原部署目录用原来的环境配置执行 `docker compose stop skill-registry`，释放主机端口。如果已有用 `docker run` 创建的同名容器，先执行 `docker stop skill-registry && docker rm skill-registry`。然后在 `.env` 所在目录运行：

```sh
docker run -d \
  --name skill-registry \
  --restart unless-stopped \
  -p 127.0.0.1:5000:5000 \
  -e TZ=Asia/Shanghai \
  --env-file ./.env \
  --mount "type=bind,source=$HOST_SKILLS_DIR,target=/skills,readonly" \
  "$IMAGE"
```

以后更新也是先 `docker pull`，成功后停掉并删除旧容器，再用同一条 `docker run` 命令启动。只执行 `docker restart` 仍会使用旧镜像。技能文件在宿主机上，重建容器后继续挂载同一目录；容器以 UID 10001 运行，需能读取文件、遍历目录。技能目录变动仍会自动刷新。技能脚本需要写文件时，可另行挂载可写的输出目录。

启动后访问 `http://127.0.0.1:5000/docs`，应看到 API 文档。也可用已挂载的技能验证扫描结果，将 `my-skill` 替换为实际技能名：

```sh
curl -fsS 'http://127.0.0.1:5000/load_skill?skill_name=my-skill'
```

预期返回 HTTP 200 和 `skill` 对象。要修改主机端口，可将 `-p` 改为 `127.0.0.1:5001:5000`。服务默认只对 Docker 主机本机开放；API 未鉴权且可执行技能资源，如需允许其他机器访问，应先配置网络访问控制或带鉴权的反向代理，再调整端口绑定。
