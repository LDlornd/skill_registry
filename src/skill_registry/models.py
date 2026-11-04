from __future__ import annotations

from pydantic import BaseModel, Field


class DiscoverSkillsRequest(BaseModel):
    """发现技能时使用的请求参数。"""

    root_dir: str = Field(
        description="要递归扫描的技能根目录；省略请求体时使用服务配置的默认目录。",
        examples=["C:/my-project/.skills"],
    )


class SkillSummary(BaseModel):
    """技能的摘要信息。"""

    name: str = Field(description="技能名称。", examples=["lark-calendar"])
    description: str | None = Field(
        default=None,
        description="技能用途的简短说明。",
        examples=["管理飞书日历及日程。"],
    )
    has_resources: bool = Field(
        description="该技能是否包含可按需加载的附加资源。",
        examples=[True],
    )


class SkillListResponse(BaseModel):
    """技能发现或搜索接口的返回值。"""

    count: int = Field(description="返回的技能数量。", examples=[1])
    skills: list[SkillSummary] = Field(description="技能摘要列表。")


class LoadedSkill(BaseModel):
    """已加载的技能内容。"""

    name: str = Field(description="技能名称。", examples=["lark-calendar"])
    content: str = Field(
        description="SKILL.md 中除元数据以外的 Markdown 指令正文。"
    )
    resources: list[str] = Field(
        description="该技能下可通过 load_resource 加载的资源相对路径列表。",
        examples=[["references/api.md", "scripts/example.py"]],
    )


class LoadSkillResponse(BaseModel):
    """加载技能接口的返回值。"""

    skill: LoadedSkill = Field(description="已加载的技能。")


class ErrorDetail(BaseModel):
    """错误的机器可读代码和中文或英文详情。"""

    code: str = Field(
        description="稳定的机器可读错误代码。",
        examples=["skill_not_found"],
    )
    message: str = Field(description="便于定位问题的错误详情。")


class LoadResourceResponse(BaseModel):
    """资源读取的业务结果；成功和失败均通过 HTTP 200 返回。"""

    success: bool = Field(description="是否成功读取资源文件。")
    skill_name: str | None = Field(
        default=None, description="资源所属的技能名称；参数缺失时为 null。"
    )
    relative_path: str | None = Field(
        default=None, description="资源相对于技能根目录的路径；参数缺失时为 null。"
    )
    content: str | None = Field(
        default=None, description="成功时为 UTF-8 文本（允许空字符串），失败时为 null。"
    )
    error: ErrorDetail | None = Field(
        default=None, description="失败时的错误代码和详情；成功时为 null。"
    )


class ExecuteResourceRequest(BaseModel):
    """执行 Skill 内资源时使用的请求参数。"""

    skill_name: str = Field(
        min_length=1,
        description="资源所属的 Skill 名称。",
        examples=["data-analysis"],
    )
    relative_path: str = Field(
        min_length=1,
        description="可执行资源相对于 Skill 根目录的路径。",
        examples=["scripts/analyze.py"],
    )
    arguments: list[str] = Field(
        default_factory=list,
        description="传递给可执行资源的命令行参数。",
        examples=[["--input", "data.csv"]],
    )
    timeout: float | None = Field(
        default=None,
        gt=0,
        description="可选的执行超时秒数。",
        examples=[120],
    )


class ExecuteResourceResponse(BaseModel):
    """Skill 资源的结构化执行结果。"""

    skill_name: str = Field(description="资源所属的 Skill 名称。")
    relative_path: str = Field(description="被执行资源的相对路径。")
    provider: str = Field(description="实际使用的执行 Provider。")
    success: bool = Field(description="进程是否在超时前以退出码 0 结束。")
    exit_code: int | None = Field(description="进程退出码；超时时为 null。")
    stdout: str = Field(description="进程的标准输出。")
    stderr: str = Field(description="进程的标准错误输出。")
    timed_out: bool = Field(description="执行是否因超时而终止。")
    duration_ms: int = Field(description="执行耗时，单位为毫秒。")


class ErrorResponse(BaseModel):
    """参数错误、技能不存在或资源不存在时的返回值。"""

    error: ErrorDetail = Field(description="错误信息。")


class NotImplementedResponse(BaseModel):
    """接口尚未实现时的返回值。"""

    code: str = Field(description="错误代码。", examples=["not_implemented"])
    message: str = Field(description="接口当前状态的说明。")
