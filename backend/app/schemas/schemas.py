"""Pydantic-Schemas für REST-API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import Confidence, Kategorie, NotificationStatus, Zahlungsintervall

# Maximaler Tag je Monat (Februar großzügig mit 29 — Schaltjahr-Eingaben nicht blockieren)
_MAX_TAG_IM_MONAT = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _validate_recurring_date(tag: int | None, monat: int | None, feldname: str) -> None:
    """Validiert ein wiederkehrendes Datum (Tag+Monat ohne Jahr): paarweise und plausibel."""
    if (tag is None) != (monat is None):
        raise ValueError(f"{feldname}: Tag und Monat müssen gemeinsam angegeben werden")
    if tag is not None and monat is not None and tag > _MAX_TAG_IM_MONAT[monat]:
        raise ValueError(f"{feldname}: Tag {tag} existiert nicht im Monat {monat}")


class InsuranceBase(BaseModel):
    name: str = Field(..., max_length=200)
    kategorie: Kategorie
    versicherer: str = Field(..., max_length=100)
    vertragsnummer: str = Field(..., max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    praemie_eur: float | None = Field(None, ge=0, le=100000)
    zahlungsintervall: Zahlungsintervall = Zahlungsintervall.JAEHRLICH
    # Kündigung als zwei wiederkehrende Daten (Tag+Monat ohne Jahr), beide optional:
    # "kündbar jeweils bis" (z.B. 30.09.) und "Vertrag endet dann zum" (z.B. 31.12.)
    kuendigung_bis_tag: int | None = Field(None, ge=1, le=31, description="Tag: jährlich kündbar bis")
    kuendigung_bis_monat: int | None = Field(None, ge=1, le=12, description="Monat: jährlich kündbar bis")
    kuendigung_zum_tag: int | None = Field(None, ge=1, le=31, description="Tag: Vertrag endet dann zum")
    kuendigung_zum_monat: int | None = Field(None, ge=1, le=12, description="Monat: Vertrag endet dann zum")
    notes: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _check_kuendigung_paare(self) -> InsuranceBase:
        _validate_recurring_date(self.kuendigung_bis_tag, self.kuendigung_bis_monat, "kuendigung_bis")
        _validate_recurring_date(self.kuendigung_zum_tag, self.kuendigung_zum_monat, "kuendigung_zum")
        return self


class InsuranceCreate(InsuranceBase):
    pass


class InsuranceConfirmPayload(InsuranceBase):
    """Payload für POST /documents/confirm/{document_id}.

    Enthält alle Versicherungsfelder plus optionale IDs weiterer Dokumente,
    die beim Anlegen der Versicherung direkt mit zugeordnet werden sollen.
    """

    extra_document_ids: list[int] = Field(default_factory=list)


class InsuranceRead(InsuranceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProductBase(BaseModel):
    name: str = Field(..., max_length=200)
    kategorie: str = Field(..., max_length=50)
    purchase_date: date | None = None
    warranty_end: date | None = None
    linked_insurance_id: int | None = None
    notes: str | None = Field(None, max_length=2000)


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    insurance_id: int | None
    original_filename: str
    mime_type: str
    ai_summary: str | None
    uploaded_at: datetime


class ExtractionPreview(BaseModel):
    """Vom DocumentAnalysisAgent extrahierte Daten zur Bestätigung durch den Nutzer."""

    versicherer: str
    kategorie: Kategorie
    vertragsnummer: str
    start_date: date | None
    end_date: date | None
    praemie_eur: float | None
    zahlungsintervall: Zahlungsintervall
    kuendigung_bis_tag: int | None
    kuendigung_bis_monat: int | None
    kuendigung_zum_tag: int | None
    kuendigung_zum_monat: int | None
    konfidenz: Confidence
    hinweise: str
    document_id: int


class RecommendationRead(BaseModel):
    """Gespeicherte KI-Empfehlung inkl. Erstellungsdatum (für 'Stand'-Anzeige)."""

    model_config = ConfigDict(from_attributes=True)

    handlungsbedarf: str
    hinweis: str
    details: str
    created_at: datetime


class ChatMessage(BaseModel):
    """Eine Nachricht aus dem bisherigen Gesprächsverlauf."""

    rolle: Literal["user", "assistant"]
    text: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    frage: str = Field(..., min_length=1, max_length=2000)
    # Bisheriger Verlauf für Folgefragen — das Frontend schickt die letzten Runden mit
    verlauf: list[ChatMessage] = Field(default_factory=list, max_length=30)


class ChatResponse(BaseModel):
    antwort: str
    quellen: list[str] = []
    konfidenz: Confidence


class InvoiceCreate(BaseModel):
    purchase_date: date | None = None
    amount_eur: float | None = Field(None, ge=0, le=1_000_000)
    notes: str | None = Field(None, max_length=2000)


class InvoiceAnalysisPreview(BaseModel):
    """Vom Invoice-Agenten extrahierte Daten zur Bestätigung durch den Nutzer."""

    purchase_date: date | None = None
    amount_eur: float | None = None
    produkt_name: str | None = None
    notes: str | None = None


class DocumentClassification(BaseModel):
    """Ergebnis der automatischen Dokumenttyp-Erkennung beim Upload."""

    typ: str  # "versicherung" | "rechnung" | "unbekannt"
    begruendung: str | None = None


class InvoiceRead(InvoiceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    original_filename: str
    mime_type: str
    retain_until: date
    uploaded_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref_type: str
    ref_id: int
    days_before: int
    trigger_date: date
    message: str
    status: NotificationStatus
    sent_at: datetime | None
