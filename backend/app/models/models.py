"""SQLAlchemy ORM-Modelle."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base
from app.models.enums import Kategorie, NotificationStatus, Zahlungsintervall


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Insurance(Base):
    __tablename__ = "insurances"
    __table_args__ = (Index("ix_insurances_end_date", "end_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kategorie: Mapped[Kategorie] = mapped_column(SAEnum(Kategorie), nullable=False)
    versicherer: Mapped[str] = mapped_column(String(100), nullable=False)
    vertragsnummer: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    praemie_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    zahlungsintervall: Mapped[Zahlungsintervall] = mapped_column(
        SAEnum(Zahlungsintervall), default=Zahlungsintervall.JAEHRLICH, nullable=False
    )
    # Kündigungsfrist als zwei wiederkehrende Kalenderdaten (Tag+Monat, ohne Jahr):
    # "kündbar jeweils bis" und "Vertrag endet dann zum" — beide optional
    kuendigung_bis_tag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kuendigung_bis_monat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kuendigung_zum_tag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kuendigung_zum_monat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    documents: Mapped[list[Document]] = relationship(back_populates="insurance", cascade="all, delete-orphan")
    recommendation: Mapped[Recommendation | None] = relationship(
        back_populates="insurance", uselist=False, cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_insurance_id", "insurance_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insurance_id: Mapped[int | None] = mapped_column(ForeignKey("insurances.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    insurance: Mapped[Insurance | None] = relationship(back_populates="documents")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_warranty_end", "warranty_end"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kategorie: Mapped[str] = mapped_column(String(50), nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_insurance_id: Mapped[int | None] = mapped_column(ForeignKey("insurances.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_product_id", "product_id"),
        Index("ix_invoices_retain_until", "retain_until"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    retain_until: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    product: Mapped[Product] = relationship("Product")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_lookup", "ref_type", "ref_id", "days_before"),
        Index("ix_notifications_due", "status", "trigger_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "insurance" | "product"
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    days_before: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_date: Mapped[date] = mapped_column(Date, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Recommendation(Base):
    """Gespeicherte KI-Empfehlung je Versicherung (eine pro Vertrag, jährlich aufgefrischt)."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insurance_id: Mapped[int] = mapped_column(
        ForeignKey("insurances.id"), nullable=False, unique=True, index=True
    )
    handlungsbedarf: Mapped[str] = mapped_column(String(20), nullable=False)
    hinweis: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    insurance: Mapped[Insurance] = relationship(back_populates="recommendation")
