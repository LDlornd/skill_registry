from .registry import Skill

def build_skill_meta_prompt(skills: list[Skill]):
    parts = ["<available_skills>"]
    for skill in skills:
        parts.extend([
            "    <skill>",
            f"        <name>{skill.get('name')}</name>",
            f"        <description>{skill.get('description')}</description>",
            f"        <has_resources>{skill.get('has_resources')}</has_resources>",
            "    </skill>"
        ])
    parts.extend(["</available_skills>"])

    return "\n".join(parts)
