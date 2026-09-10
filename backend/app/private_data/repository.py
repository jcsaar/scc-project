import json
from pathlib import Path

from pydantic import TypeAdapter

from app.domain.private import PrivateContext, SensitiveFact


class PrivateEntityNotFound(LookupError):
    """Raised without exposing any private facts."""


class SyntheticPrivateRepository:
    def __init__(self, dataset_path: Path) -> None:
        document = json.loads(dataset_path.read_text(encoding="utf-8"))
        self._synthetic_demo_data = document["synthetic_demo_data"] is True
        self._projects = {project["project_id"]: project for project in document["projects"]}

    def load_project(self, project_id: str) -> PrivateContext:
        project = self._projects.get(project_id)
        if project is None:
            raise PrivateEntityNotFound(f"Private project not found: {project_id}")
        return PrivateContext(
            project_id=project["project_id"],
            display_name=project["display_name"],
            classification=project["classification"],
            synthetic_demo_data=self._synthetic_demo_data,
            facts=TypeAdapter(tuple[SensitiveFact, ...]).validate_python(project["facts"]),
        )

    def find_fact(self, project_id: str, semantic_key: str) -> SensitiveFact:
        context = self.load_project(project_id)
        for fact in context.facts:
            if fact.semantic_key == semantic_key:
                return fact
        raise PrivateEntityNotFound(
            f"Private fact not found for project {project_id}: {semantic_key}"
        )
