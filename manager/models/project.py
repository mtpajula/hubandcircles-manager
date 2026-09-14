"""Project settings (project.json), chapter 5.1."""

from pydantic import BaseModel, ConfigDict, Field

from manager.models.common import Bbox, LangText


class Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github_repo: str
    issue_form: str


class ItrsScales(BaseModel):
    """Number of levels of the ITRS exposure and wilderness scales; None = not locked yet."""

    model_config = ConfigDict(extra="forbid")

    exposure: int | None = Field(default=None, gt=0)
    wilderness: int | None = Field(default=None, gt=0)


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: LangText
    subtitle: LangText
    area: Bbox
    municipality: str | None = None  # city filter of the Visit Finland importer (7.6)
    languages: list[str]
    default_language: str
    default_theme: str
    nearby_services_m: int = 500
    itrs_scales: ItrsScales = ItrsScales()
    feedback: Feedback | None = None
