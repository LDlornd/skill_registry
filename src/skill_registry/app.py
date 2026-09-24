from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from .expection import register_exception_handlers
from .registry import SkillRegistry
from .routes import router


load_dotenv(dotenv_path=Path.cwd() / ".env")

OPENAPI_TAGS = [
    {
        "name": "技能注册表",
        "description": "技能发现、查询、内容加载和资源执行接口。",
    },
    {
        "name": "技能管理",
        "description": "技能新增和删除接口；当前仍在开发中。",
    },
]


def create_app(config: dict[str, Any] | None = None) -> FastAPI:
    settings: dict[str, Any] = {
        "SKILLS_DIR": os.getenv("SKILLS_DIR", str(Path.cwd() / ".skills")),
        "EXECUTION_PROVIDER": None,
    }
    if config:
        settings.update(config)

    app = FastAPI(
        title="技能注册表 API",
        description=(
            "用于发现、搜索、按需加载本地技能及执行 Skill 内资源。"
            "接口参数优先从 JSON 请求体读取，其次读取查询参数和表单参数。"
        ),
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
    )
    app.state.config = settings
    app.state.skill_registry = SkillRegistry(
        settings["SKILLS_DIR"],
        execution_provider=settings["EXECUTION_PROVIDER"],
    )
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
    )


if __name__ == "__main__":
    main()
