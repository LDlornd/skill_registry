from __future__ import annotations

from typing import Any, Literal

import requests


class SkillRegistryClientError(RuntimeError):
    """远程 Skill Registry 请求失败或返回数据不符合约定。"""


class SkillRegistryClient:
    """面向文件型 Skill Registry 服务的轻量 HTTP 客户端。"""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10,
        session: requests.Session | None = None,
    ):
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("skill_registry.base_url 必须是非空字符串")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("skill_registry.timeout 必须大于 0")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Network 可能并发执行多个 Agent，默认不共享可变的 requests.Session。
        # 测试或明确需要复用连接时，调用方仍可主动传入 Session。
        self._session = session


    def _get(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("get", path, payload)

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        request_timeout: float | None = None,
    ) -> dict[str, Any]:
        return self._request("post", path, payload, request_timeout)

    def _request(
        self,
        method: Literal["get", "post"],
        path: str,
        payload: dict[str, Any],
        request_timeout: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        try:
            requester = self._session or requests
            request = getattr(requester, method)
            response = request(
                url,
                json=payload,
                timeout=request_timeout or self.timeout,
            )
        except requests.RequestException as error:
            raise SkillRegistryClientError(
                f"Skill Registry 请求失败：{url}：{error}"
            ) from error

        try:
            data = response.json()
        except ValueError as error:
            raise SkillRegistryClientError(
                f"Skill Registry 返回的不是 JSON：{url} "
                f"（HTTP 状态码={response.status_code}）"
            ) from error

        if not isinstance(data, dict):
            raise SkillRegistryClientError(
                f"Skill Registry 返回的数据结构无效：{url}"
            )

        if not response.ok or "error" in data:
            registry_error = data.get("error")

            if isinstance(registry_error, dict):
                code = registry_error.get("code", "unknown_error")
                message = registry_error.get(
                    "message",
                    "Skill Registry 请求失败",
                )
            else:
                code = f"http_{response.status_code}"
                message = str(
                    registry_error
                    or data.get("message")
                    or response.reason
                )

            raise SkillRegistryClientError(
                f"Skill Registry 错误 [{code}]：{message}"
            )

        return data

    def search_skills(self, query: str) -> list[dict[str, Any]]:
        try:
            # query = self._require_string("query", query)
            query = query or ""
            data = self._get("/search_skills", {"query": query})
        except Exception as error:
            return {
                "success": 0,
                "message": str(error)
            }
        
        return {
            "success": 1,
            "skills": data.get("skills", [])
        }

    def load_skill(self, skill_name: str) -> dict[str, Any]:
        try:
            skill_name = self._require_string("skill_name", skill_name)
            data = self._get("/load_skill", {"skill_name": skill_name})
        except Exception as error:
            return {
                "success": 0,
                "message": str(error)
            }
        
        skill = data.get("skill")
        
        return {
            "success": 1,
            "skill": skill
        }

    def load_resource(self, skill_name: str, relative_path: str) -> str:
        try:
            skill_name = self._require_string("skill_name", skill_name)
            relative_path = self._require_string("relative_path", relative_path)
            data = self._get(
                "/load_resource",
                {
                    "skill_name": skill_name,
                    "relative_path": relative_path,
                },
            )
        except Exception as error:
            return {
                "success": 0,
                "message": str(error)
            }
        
        content = data.get("content")

        return {
            "success": 1,
            "content": content
        }

    def execute_resource(
        self,
        skill_name: str,
        relative_path: str,
        arguments: list[str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        try:
            skill_name = self._require_string("skill_name", skill_name)
            relative_path = self._require_string("relative_path", relative_path)
            if arguments is None:
                arguments = []
            if not isinstance(arguments, list) or any(
                not isinstance(argument, str) for argument in arguments
            ):
                raise ValueError("参数 arguments 必须是字符串列表")
            if timeout is not None and (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or timeout <= 0
            ):
                raise ValueError("参数 timeout 必须是大于 0 的数字")

            payload: dict[str, Any] = {
                "skill_name": skill_name,
                "relative_path": relative_path,
                "arguments": arguments,
            }
            if timeout is not None:
                payload["timeout"] = timeout
            request_timeout = (
                max(self.timeout, timeout + 5) if timeout is not None else None
            )
            data = self._post(
                "/execute_resource",
                payload,
                request_timeout=request_timeout,
            )
        except Exception as error:
            return {
                "success": 0,
                "message": str(error),
            }

        return {
            "success": 1,
            "execution": data,
        }

    @staticmethod
    def _require_string(name: str, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"参数 {name} 必须是非空字符串")
        return value.strip()

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
