import os
import re
from pathlib import Path
from typing import Dict, Sequence

from .expection import (
    InvalidResourcePathError,
    ResourceNotFoundError,
    SkillNotFoundError,
)
from .execution import (
    ExecutionResult,
    LocalExecutionProvider,
    SkillExecutionProvider,
)

import yaml

_FRONTMATTER_RE = re.compile(
    r"\A(?:\ufeff)?---[ \t]*\r?\n"
    r"(.*?)"
    r"^---[ \t]*(?:\r?\n|\Z)"
    r"(.*)\Z",
    re.MULTILINE | re.DOTALL,
)


def parse_skill_md(text: str) -> tuple[dict, str]:
    """解析 SKILL.md，返回 (meta_dict, content_markdown)。"""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text.strip()

    frontmatter_raw, content = match.groups()
    meta = yaml.safe_load(frontmatter_raw)

    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise ValueError("SKILL.md 的 YAML frontmatter 必须是键值映射")

    return meta, content.strip()

def _parse_simple_yaml(raw: str) -> dict:
    result = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result

class Skill:
    def __init__(self, skill_name, meta, content, root_dir, resources = [], manifest={}):
        self.skill_name = skill_name
        self.meta = meta
        self.content = content
        self.root_dir = root_dir
        self.resources = resources

        self.id = skill_name
        self.descrption = meta.get("description")
        
        self.version = manifest.get("version")
        self.type = manifest.get("type")
        self.permissions = manifest.get("permissions")
        self.dependencies = manifest.get("dependencies")
        self.timeout = meta.get("timeout")



    @classmethod
    def from_root(cls, root_dir):
        skill_path = os.path.join(root_dir, "SKILL.md")
        if not os.path.exists(skill_path):
            skill_path = os.path.join(root_dir, "skill.md")

        with open(skill_path, "r", encoding="utf-8") as f:
            meta, content = parse_skill_md(f.read())

            skill_name = meta.get("name") or os.path.basename(root_dir)

            exclude_path = [skill_path, os.path.join(root_dir, "skill.manifest.yaml")]

            return cls(skill_name, meta, content, root_dir, cls._collect_resources(root_dir, exclude_path))

    @classmethod
    def _collect_resources(cls, skill_root: str, exclude_path: str) -> list[str]:
        """收集该 skill 根目录下除 SKILL.md 外的所有文件，返回相对路径列表（不读内容）"""
        resource_paths = []
        for root, dirs, files in os.walk(skill_root):
            for file in files:
                full_path = os.path.join(root, file)
                if full_path in exclude_path:
                    continue
                rel_path = os.path.relpath(full_path, skill_root)
                resource_paths.append(rel_path)

        return sorted(resource_paths)
    
    def load_resource(self, relative_path: str) -> str:
        """
        按需加载某个 skill 下的具体资源文件内容。
        做路径校验，防止越权访问 skill 目录之外的文件。
        """
        skill_root = os.path.realpath(self.root_dir)
        target = os.path.realpath(os.path.join(skill_root, relative_path))

        if os.path.commonpath([skill_root, target]) != skill_root:
            return f"ERROR: Resource path escapes skill root: {relative_path}"

        if not os.path.isfile(target):
            return f"ERROR: {relative_path} is not a file"

        with open(target, "r", encoding="utf-8") as f:
            return f.read()
        
    def format_meta(self):
        """
        暴露给大模型的第一层视图：只有 name / description / 是否有额外资源。
        不包含资源具体内容，保持“先看目录，再按需展开”的层次化结构。
        """
        return {
            "name": self.skill_name,
            "description": self.descrption,
            "has_resources": bool(len(self.resources) > 0)
        }


class SkillRegistry:
    SKILL_FILENAME = "SKILL.md"
    SKILL_MANIFEST_FILENAME = "skill.manifest.yaml"

    def __init__(
        self,
        skills_dir: str = os.path.join(".", "skills"),
        execution_provider: SkillExecutionProvider | None = None,
    ):
        self.skills: Dict[str, Skill] = {}
        self.execution_provider = (
            execution_provider
            if execution_provider is not None
            else LocalExecutionProvider()
        )

        self.discover_skills(skills_dir)

    def add_skill():
        # TODO: 添加 skill
        pass

    def delte_skill():
        # TODO: 删除 skill
        pass

    def discover_skills(self, root_dir: str):
        """
        只有目录同时包含 SKILL.md 和 skill.manifest.yaml 时，
        才将该目录识别为一个 skill 根目录。

        Skill 根目录下的其它文件和目录均作为资源处理，
        不再继续向下发现嵌套 skill。
        """
        required_files = {
            self.SKILL_FILENAME,
            # self.SKILL_MANIFEST_FILENAME,
        }

        for root, dirs, files in os.walk(root_dir):
            if not required_files.issubset(set(files)):
                continue

            new_skill = Skill.from_root(root)

            self.skills[new_skill.skill_name] = new_skill

            # 当前目录已经是 skill 根目录，不再扫描其 references、
            # scripts、assets 等子目录。
            dirs[:] = []

    def search_skills(self, query: str, exposed_skills: list[str] | None = None) -> list[str]:
        """
        搜索 skill, 返回 skill 名称列表
        如果用户没有指定 skill, 返回全部 skill。
        如果用户指定了 skill, 返回指定 skill 名称的 skill。
        """

        # 初版返回全部 skill
        if not exposed_skills:
            skill_list = self.skills
        else:
            skill_list = []
            for skill in self.skills:
                if skill.skill_name in exposed_skills:
                    skill_list.append(skill)

        return self.format_skill_meta(skill_list)

    def load_skill(self, skill_name: str) -> str:
        """加载 skill 的 SKILL.md 正文（入口文档，第一步该看的内容）"""
        return self.skills[skill_name].content

    def list_resources(self, skill_name: str) -> list[str]:
        """列出该 skill 下可按需加载的资源文件相对路径（reference、scripts 等）"""
        return self.skills[skill_name].resources

    def load_resource(self, skill_name: str, relative_path: str) -> str:
        """
        按需加载某个 skill 下的具体资源文件内容。
        """
        if skill_name not in self.skills.keys():
            return f"ERROR: Unknown skill: {skill_name}"

        return self.skills[skill_name].load_resource(relative_path)

    def execute_resource(
        self,
        skill_name: str,
        relative_path: str,
        arguments: Sequence[str] = (),
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute a resource through the configured execution provider."""
        try:
            skill = self.skills[skill_name]
        except KeyError as error:
            raise SkillNotFoundError(f"Unknown skill: {skill_name}") from error

        resource_path = self._resolve_resource_path(skill, relative_path)
        return self.execution_provider.execute(
            resource_path,
            arguments=arguments,
            timeout=timeout,
        )

    @staticmethod
    def _resolve_resource_path(skill: Skill, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("relative_path must be a non-empty string")

        skill_root = Path(skill.root_dir).resolve()
        resource_path = (skill_root / relative_path).resolve()
        try:
            resource_path.relative_to(skill_root)
        except ValueError as error:
            raise InvalidResourcePathError(
                f"Resource path escapes skill root: {relative_path}"
            ) from error

        if not resource_path.is_file():
            raise ResourceNotFoundError(
                f"Resource not found for skill {skill.skill_name}: {relative_path}"
            )
        return resource_path

    def format_skill_meta(self, skill_list) -> list[dict]:
        """
        暴露给大模型的第一层视图：只有 name / description / 是否有额外资源。
        不包含资源具体内容，保持“先看目录，再按需展开”的层次化结构。
        """
        return [self.skills[skill_name].format_meta() for skill_name in skill_list]
