from __future__ import annotations

import os
import json
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .api_docs import (
    DISCOVER_SKILLS_OPENAPI_EXTRA,
    EXECUTE_RESOURCE_OPENAPI_EXTRA,
    LOAD_RESOURCE_OPENAPI_EXTRA,
    LOAD_SKILL_OPENAPI_EXTRA,
    SEARCH_SKILLS_OPENAPI_EXTRA,
)
from .expection import (
    InvalidResourcePathError,
    ResourceNotFoundError,
    SkillNotFoundError,
)
from .models import (
    ErrorResponse,
    ExecuteResourceResponse,
    LoadResourceResponse,
    LoadSkillResponse,
    NotImplementedResponse,
    SkillListResponse,
)

from .registry import Skill, SkillRegistry

router = APIRouter()


async def _json_payload(request: Request) -> dict[str, Any] | None:
    try:
        payload = await request.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


async def _request_value(request: Request, name: str, default: Any = None) -> Any:
    """Read a value from JSON first, then query/form parameters."""
    payload = await _json_payload(request)
    if payload is not None and name in payload:
        return payload[name]
    if name in request.query_params:
        return request.query_params[name]

    form = await request.form()
    return form.get(name, default)


async def _request_list_value(
    request: Request,
    name: str,
    default: list[str] | None = None,
) -> list[str] | None:
    """支持 JSON 数组、重复 query/form 参数及 JSON 编码的数组参数。"""
    payload = await _json_payload(request)
    from_params = False

    if payload is not None and name in payload:
        value = payload[name]
    elif name in request.query_params:
        value = request.query_params.getlist(name)
        from_params = True
    else:
        form = await request.form()
        if name in form:
            value = form.getlist(name)
            from_params = True
        else:
            value = default

    if value is None:
        return None

    if (
        from_params
        and isinstance(value, list)
        and len(value) == 1
        and isinstance(value[0], str)
        and value[0].lstrip().startswith("[")
    ):
        try:
            value = json.loads(value[0])
        except json.JSONDecodeError as exc:
            raise ValueError(f"{name} contains an invalid JSON array") from exc

    if not isinstance(value, list) or any(
        not isinstance(item, str) for item in value
    ):
        raise ValueError(f"{name} must be a list of strings")

    return [item.strip() for item in value if item.strip()]


async def _require_string(request: Request, name: str) -> str:
    value = await _request_value(request, name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required parameter: {name}")
    return value.strip()


def _registry(request: Request) -> SkillRegistry:
    return request.app.state.skill_registry


def _skill(registry: SkillRegistry, skill_name: str) -> Skill:
    try:
        return registry.skills[skill_name]
    except KeyError as error:
        raise SkillNotFoundError(f"Unknown skill: {skill_name}") from error


def _load_resource(
    registry: SkillRegistry,
    skill_name: str,
    relative_path: str,
) -> str:
    skill = _skill(registry, skill_name)
    skill_root = os.path.realpath(skill.root_dir)
    target = os.path.realpath(os.path.join(skill_root, relative_path))

    try:
        is_inside_skill = os.path.commonpath([skill_root, target]) == skill_root
    except ValueError:
        is_inside_skill = False

    if not is_inside_skill:
        raise InvalidResourcePathError(
            f"Resource path escapes skill root: {relative_path}"
        )
    if not os.path.isfile(target):
        raise ResourceNotFoundError(
            f"Resource not found for skill {skill_name}: {relative_path}"
        )

    return skill.load_resource(relative_path)


@router.post(
    "/discover_skills",
    tags=["技能注册表"],
    summary="发现技能",
    description=(
        "递归扫描指定目录并更新注册表。root_dir 可以通过 JSON 请求体、"
        "查询参数或表单提交；JSON 中的值优先。"
    ),
    response_model=SkillListResponse,
    response_description="扫描后注册表中的技能数量及摘要列表。",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "root_dir 不是有效的非空字符串。",
        }
    },
    openapi_extra=DISCOVER_SKILLS_OPENAPI_EXTRA,
)
async def discover_skills(request: Request) -> dict[str, Any]:
    root_dir = await _request_value(
        request,
        "root_dir",
        request.app.state.config["SKILLS_DIR"],
    )
    if not isinstance(root_dir, str) or not root_dir.strip():
        raise ValueError("root_dir must be a non-empty string")

    registry = _registry(request)
    await run_in_threadpool(registry.discover_skills, root_dir.strip())
    skills = registry.search_skills("")
    return {"count": len(skills), "skills": skills}


@router.post(
    "/add_skill",
    tags=["技能管理"],
    summary="新增技能",
    description="新增技能接口，当前尚未实现。",
    status_code=HTTPStatus.NOT_IMPLEMENTED,
    response_model=NotImplementedResponse,
    response_description="接口尚未实现。",
)
async def add_skill() -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        content={"code": "not_implemented", "message": "add_skill 接口正在开发中"},
    )


@router.post(
    "/delete_skill",
    tags=["技能管理"],
    summary="删除技能",
    description="删除技能接口，当前尚未实现。",
    status_code=HTTPStatus.NOT_IMPLEMENTED,
    response_model=NotImplementedResponse,
    response_description="接口尚未实现。",
)
async def delete_skill() -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        content={
            "code": "not_implemented",
            "message": "delete_skill 接口正在开发中",
        },
    )


@router.get(
    "/search_skills",
    tags=["技能注册表"],
    summary="搜索技能",
    description=(
        "返回注册表中的技能摘要，不加载技能正文。query 会传给注册表的"
        "搜索实现，exposed_skills 用于限制允许返回的技能范围。"
    ),
    response_model=SkillListResponse,
    response_description="返回的技能数量及摘要列表。",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "query 不是字符串，或 exposed_skills 格式不正确。",
        }
    },
    openapi_extra=SEARCH_SKILLS_OPENAPI_EXTRA,
)
async def search_skills(request: Request) -> dict[str, Any]:
    query = await _request_value(request, "query", "")
    exposed_skills = await _request_list_value(request, "exposed_skills")
    if not isinstance(query, str):
        raise ValueError("query must be a string")

    skills = _registry(request).search_skills(query)
    if exposed_skills:
        exposed_names = set(exposed_skills)
        skills = [skill for skill in skills if skill["name"] in exposed_names]
    return {"count": len(skills), "skills": skills}


@router.get(
    "/load_skill",
    tags=["技能注册表"],
    summary="加载技能",
    description="加载指定技能的 Markdown 指令正文和可用资源路径。",
    response_model=LoadSkillResponse,
    response_description="技能正文及其资源路径列表。",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "缺少有效的 skill_name。",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ErrorResponse,
            "description": "注册表中不存在指定技能。",
        },
    },
    openapi_extra=LOAD_SKILL_OPENAPI_EXTRA,
)
async def load_skill(request: Request) -> dict[str, Any]:
    skill_name = await _require_string(request, "skill_name")
    skill = _skill(_registry(request), skill_name)
    return {
        "skill": {
            "name": skill_name,
            "content": skill.content,
            "resources": skill.resources,
        }
    }


@router.get(
    "/load_resource",
    tags=["技能注册表"],
    summary="加载技能资源",
    description=(
        "读取指定技能下的一个 UTF-8 文本资源。路径会经过边界检查，"
        "不能访问技能根目录之外的文件。"
    ),
    response_model=LoadResourceResponse,
    response_description="资源所属技能、相对路径和文本内容。",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "缺少参数，或资源路径逃逸技能根目录。",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ErrorResponse,
            "description": "技能或资源文件不存在。",
        },
    },
    openapi_extra=LOAD_RESOURCE_OPENAPI_EXTRA,
)
async def load_resource(request: Request) -> dict[str, str]:
    skill_name = await _require_string(request, "skill_name")
    relative_path = await _require_string(request, "relative_path")
    return {
        "skill_name": skill_name,
        "relative_path": relative_path,
        "content": _load_resource(
            _registry(request),
            skill_name,
            relative_path,
        ),
    }


@router.post(
    "/execute_resource",
    tags=["技能注册表"],
    summary="执行 Skill 内资源",
    description=(
        "通过配置的执行 Provider 运行 Skill 内的可执行资源。"
        "本地 Provider 会将工作目录设置为该资源所在目录；"
        "资源路径必须位于已注册 Skill 的根目录内。"
    ),
    response_model=ExecuteResourceResponse,
    response_description="资源的退出码、标准输出、标准错误和耗时。",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "请求参数无效，或资源路径逃逸 Skill 根目录。",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Skill 或资源文件不存在。",
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "执行 Provider 无法启动资源。",
        },
    },
    openapi_extra=EXECUTE_RESOURCE_OPENAPI_EXTRA,
)
async def execute_resource(request: Request) -> dict[str, Any]:
    skill_name = await _require_string(request, "skill_name")
    relative_path = await _require_string(request, "relative_path")
    arguments = await _request_list_value(request, "arguments", [])
    timeout_value = await _request_value(request, "timeout")

    if timeout_value in (None, ""):
        timeout = None
    else:
        if isinstance(timeout_value, bool):
            raise ValueError("timeout must be a number greater than 0")
        try:
            timeout = float(timeout_value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "timeout must be a number greater than 0"
            ) from error
        if timeout <= 0:
            raise ValueError("timeout must be a number greater than 0")

    registry = _registry(request)
    result = await run_in_threadpool(
        registry.execute_resource,
        skill_name,
        relative_path,
        arguments or [],
        timeout,
    )
    return {
        "skill_name": skill_name,
        "relative_path": relative_path,
        "provider": result.provider,
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
        "duration_ms": result.duration_ms,
    }
