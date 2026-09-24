from __future__ import annotations

from typing import Any

from .models import DiscoverSkillsRequest, ExecuteResourceRequest


def _query_parameter(
    name: str,
    description: str,
    *,
    required: bool = False,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "in": "query",
        "required": required,
        "description": description,
        "schema": schema or {"type": "string"},
    }


ROOT_DIR_PARAMETER = _query_parameter(
    "root_dir",
    "要递归扫描的技能根目录；不传时使用服务配置的默认目录。",
    schema={"type": "string", "example": "C:/my-project/.skills"},
)
QUERY_PARAMETER = _query_parameter(
    "query",
    "技能搜索文本；空字符串表示返回当前可见的全部技能。",
    schema={"type": "string", "default": "", "example": "日历"},
)
EXPOSED_SKILLS_PARAMETER = _query_parameter(
    "exposed_skills",
    "可选的技能名称白名单；可以重复传入该参数。",
    schema={
        "type": "array",
        "items": {"type": "string"},
        "example": ["lark-calendar", "lark-im"],
    },
)
SKILL_NAME_PARAMETER = _query_parameter(
    "skill_name",
    "要加载的技能名称，必须与注册表中的名称完全一致。",
    required=True,
    schema={"type": "string", "example": "lark-calendar"},
)
RELATIVE_PATH_PARAMETER = _query_parameter(
    "relative_path",
    "资源相对于该技能根目录的路径，不允许使用 .. 逃逸技能目录。",
    required=True,
    schema={"type": "string", "example": "references/api.md"},
)
ARGUMENTS_PARAMETER = _query_parameter(
    "arguments",
    "传递给可执行资源的命令行参数；可以重复传入该参数。",
    schema={
        "type": "array",
        "items": {"type": "string"},
        "example": ["--input", "data.csv"],
    },
)
TIMEOUT_PARAMETER = _query_parameter(
    "timeout",
    "可选的执行超时秒数，必须大于 0。",
    schema={"type": "number", "exclusiveMinimum": 0, "example": 120},
)

DISCOVER_SKILLS_OPENAPI_EXTRA = {
    "parameters": [ROOT_DIR_PARAMETER],
    "requestBody": {
        "required": False,
        "description": "可选请求体；也可以改用上方的 root_dir 查询参数。",
        "content": {
            "application/json": {
                "schema": DiscoverSkillsRequest.model_json_schema()
            },
            "application/x-www-form-urlencoded": {
                "schema": DiscoverSkillsRequest.model_json_schema()
            },
        },
    },
}
SEARCH_SKILLS_OPENAPI_EXTRA = {
    "parameters": [QUERY_PARAMETER, EXPOSED_SKILLS_PARAMETER]
}
LOAD_SKILL_OPENAPI_EXTRA = {"parameters": [SKILL_NAME_PARAMETER]}
LOAD_RESOURCE_OPENAPI_EXTRA = {
    "parameters": [SKILL_NAME_PARAMETER, RELATIVE_PATH_PARAMETER]
}
EXECUTE_RESOURCE_OPENAPI_EXTRA = {
    "parameters": [
        SKILL_NAME_PARAMETER,
        RELATIVE_PATH_PARAMETER,
        ARGUMENTS_PARAMETER,
        TIMEOUT_PARAMETER,
    ],
    "requestBody": {
        "required": False,
        "content": {
            "application/json": {
                "schema": ExecuteResourceRequest.model_json_schema()
            }
        },
    },
}
