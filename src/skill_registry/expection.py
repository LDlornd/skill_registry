from __future__ import annotations

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .execution import SkillExecutionError


class SkillRegistryError(Exception):
    """Skill registry base exception."""


class SkillNotFoundError(SkillRegistryError):
    """Raised when a skill name is not present in the registry."""


class ResourceNotFoundError(SkillRegistryError):
    """Raised when a resource is missing or is not a regular file."""


class InvalidResourcePathError(SkillRegistryError):
    """Raised when a resource path escapes its skill root."""


async def handle_bad_request(
    _request: Request,
    error: ValueError,
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={"error": {"code": "bad_request", "message": str(error)}},
    )


async def handle_unknown_skill(
    _request: Request,
    error: SkillNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.NOT_FOUND,
        content={"error": {"code": "skill_not_found", "message": str(error)}},
    )


async def handle_unknown_resource(
    _request: Request,
    error: ResourceNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.NOT_FOUND,
        content={
            "error": {"code": "resource_not_found", "message": str(error)}
        },
    )


async def handle_invalid_resource_path(
    _request: Request,
    error: InvalidResourcePathError,
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={
            "error": {
                "code": "invalid_resource_path",
                "message": str(error),
            }
        },
    )


async def handle_skill_execution_error(
    _request: Request,
    error: SkillExecutionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "skill_execution_failed",
                "message": str(error),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the registry's exception-to-HTTP mappings to an application."""
    app.add_exception_handler(ValueError, handle_bad_request)
    app.add_exception_handler(SkillNotFoundError, handle_unknown_skill)
    app.add_exception_handler(ResourceNotFoundError, handle_unknown_resource)
    app.add_exception_handler(InvalidResourcePathError, handle_invalid_resource_path)
    app.add_exception_handler(SkillExecutionError, handle_skill_execution_error)
