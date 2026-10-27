"""
schema.py - СХЕМА СУТНОСТЕЙ: описує, які факти ми хочемо витягти з тексту.
Pydantic-моделі передаються в Gemini як response_schema, тож модель відповідає
саме у цій структурі (JSON).
Типи сутностей: Person, Machine, Organization, Place (4 типи).
Типи зв'язків: designed, worked_at, built_at, influenced, collaborated_with (5 типів).
"""
from pydantic import BaseModel, Field


class Fact(BaseModel):
    subject: str = Field(description="Name of the first entity, exactly as in the text")
    subject_type: str = Field(description="One of: Person, Machine, Organization, Place")
    relation: str = Field(description="One of: designed, worked_at, built_at, influenced, collaborated_with")
    object: str = Field(description="Name of the second entity, exactly as in the text")
    object_type: str = Field(description="One of: Person, Machine, Organization, Place")
    evidence: str = Field(description="Short exact quote (one sentence) from the text that supports the fact")


class FactList(BaseModel):
    facts: list[Fact]
