from pydantic import BaseModel, Field


class CVFields(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    raw_text: str = ""

    def to_db_fields(self) -> tuple[str, dict]:
        """Return (cv_text, cv_fields_json) for persistence."""
        return self.raw_text, self.model_dump(exclude={"raw_text"})