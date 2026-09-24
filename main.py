from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

from dotenv import load_dotenv


load_dotenv()

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = Path(os.getenv("SKILLS_ROOT")).resolve()


from skill_registry.app import create_app

app = create_app({"SKILLS_DIR": str(SKILLS_ROOT)})


if __name__ == "__main__":
    print(f"Skill Registry 扫描目录：{SKILLS_ROOT}")
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
    )
