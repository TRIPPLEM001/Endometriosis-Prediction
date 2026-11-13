"""
screening.py (schemas)

Request and response shapes for the screening endpoints.

Field names deliberately match the model's feature names (Age, BMI,
Dysmenorrhea_Score, ...), so the same vocabulary is used by the request,
the stored answers, the explanation factors and the models themselves.
A test checks these classes stay in sync with the loaded models.

The ranges below reject impossible values (an age of 400, a pain score of
-3). They are broad sanity limits, not clinical judgements; the scores are
0-10 because the models were trained on 0-10 integer scales.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, computed_field, model_validator

from app.services.explanation import (
    DISCLAIMER,
    PROTOTYPE_NOTICE,
    format_probability,
    recommendation_message,
)
from app.services.prediction import Recommendation

YES_NO_FIELDS = ("Family_History", "Infertility_Status")


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class _NumbersAreNotBooleans(BaseModel):
    """
    Pydantic's lenient integer/float parsing accepts `true` as 1. For a pain
    score or a lab value that would silently turn a mistake into a real
    answer, so a boolean is rejected everywhere except the yes/no fields.
    """

    @model_validator(mode="before")
    @classmethod
    def _reject_booleans_in_numeric_fields(cls, data):
        if isinstance(data, dict):
            for name, value in data.items():
                if isinstance(value, bool) and name not in YES_NO_FIELDS:
                    raise ValueError(f"{name} must be a number, not true/false.")
        return data


class SymptomAnswers(_NumbersAreNotBooleans):
    """Tier 1 answers. Unknown fields are rejected so typos don't pass silently."""

    model_config = ConfigDict(extra="forbid")

    Age: int = Field(ge=12, le=65, description="Age in years")
    BMI: float = Field(ge=12, le=70, allow_inf_nan=False)
    Cycle_Length: int = Field(ge=15, le=90, description="Typical menstrual cycle length in days")
    Age_of_Menarche: int = Field(ge=8, le=20, description="Age at first period")
    Dysmenorrhea_Score: int = Field(ge=0, le=10, description="Period pain, 0 (none) to 10 (worst)")
    Pelvic_Pain_Score: int = Field(ge=0, le=10)
    Dyspareunia_Score: int = Field(ge=0, le=10, description="Pain during sex")
    Dyschezia_Score: int = Field(ge=0, le=10, description="Painful bowel movements")
    Urinary_Symptoms_Score: int = Field(ge=0, le=10)
    Family_History: StrictBool = Field(description="Family history of endometriosis")
    Infertility_Status: StrictBool = Field(description="Currently experiencing infertility")
    Mental_Health_Score: int = Field(ge=0, le=10)

    def to_model_inputs(self) -> dict:
        """Plain dict in the form the models (and the database) use: yes/no as 1/0."""
        data = self.model_dump()
        for name in YES_NO_FIELDS:
            data[name] = int(data[name])
        return data


class LabResults(_NumbersAreNotBooleans):
    """Tier 2 follow-up. Both values are required together."""

    model_config = ConfigDict(extra="forbid")

    CA_125_Level: float = Field(ge=0, le=5000, allow_inf_nan=False, description="CA-125, U/mL")
    CRP_Level: float = Field(ge=0, le=500, allow_inf_nan=False, description="CRP, mg/L")

    def to_model_inputs(self) -> dict:
        return self.model_dump()


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #
class FactorOut(BaseModel):
    feature: str
    label: str
    direction: str  # increases | decreases | influential


class ScreeningSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    recommendation: str
    tier1_probability: float
    tier1_flagged: bool
    tier2_probability: float | None
    tier2_flagged: bool | None

    @computed_field
    @property
    def tier1_probability_display(self) -> str:
        return format_probability(self.tier1_probability)

    @computed_field
    @property
    def tier2_probability_display(self) -> str | None:
        if self.tier2_probability is None:
            return None
        return format_probability(self.tier2_probability)

    @computed_field
    @property
    def can_add_labs(self) -> bool:
        """True when a lab follow-up is allowed: flagged at Tier 1 and no labs yet."""
        return self.tier1_flagged and self.tier2_probability is None


class ScreeningDetail(ScreeningSummary):
    # model_version / model_validated are real field names here, not pydantic internals.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    inputs: dict
    lab_inputs: dict | None
    factors: dict[str, list[FactorOut]]
    report_text: str
    model_version: str
    tier2_model_version: str | None
    model_validated: bool

    @computed_field
    @property
    def next_step(self) -> str:
        return recommendation_message(Recommendation(self.recommendation), self.model_validated)

    @computed_field
    @property
    def disclaimer(self) -> str:
        return DISCLAIMER

    @computed_field
    @property
    def prototype_notice(self) -> str | None:
        return None if self.model_validated else PROTOTYPE_NOTICE


class ScreeningList(BaseModel):
    items: list[ScreeningSummary]
    total: int
    limit: int
    offset: int
