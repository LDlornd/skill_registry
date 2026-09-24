from __future__ import annotations

from loguru import logger
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event, Thread
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


def _refresh_loop(registry: SkillRegistry, stop: Event, interval: float) -> None:
    while not stop.wait(interval):
        try:
            registry.refresh()
        except Exception:
            # 保留上一次完整的技能快照，下一轮继续尝试。
            logger.exception("Failed to refresh skill directories")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    stop = Event()
    worker = Thread(
        target=_refresh_loop,
        args=(
            app.state.skill_registry,
            stop,
            app.state.config["SKILLS_REFRESH_INTERVAL"],
        ),
        name="skill-registry-refresh",
        daemon=True,
    )
    worker.start()
    try:
        yield
    finally:
        stop.set()
        worker.join(timeout=5)


def create_app(config: dict[str, Any] | None = None) -> FastAPI:
    settings: dict[str, Any] = {
        "SKILLS_DIR": os.getenv("SKILLS_DIR", str(Path.cwd() / ".skills")),
        "SKILLS_REFRESH_INTERVAL": os.getenv("SKILLS_REFRESH_INTERVAL", "1"),
        "EXECUTION_PROVIDER": None,
    }
    if config:
        settings.update(config)
    interval = float(settings["SKILLS_REFRESH_INTERVAL"])
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("SKILLS_REFRESH_INTERVAL must be a finite number greater than 0")
    settings["SKILLS_REFRESH_INTERVAL"] = interval

    app = FastAPI(
        title="技能注册表 API",
        description=(
            "用于发现、搜索、按需加载本地技能及执行 Skill 内资源。"
            "接口参数优先从 JSON 请求体读取，其次读取查询参数和表单参数。"
        ),
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=_lifespan,
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
