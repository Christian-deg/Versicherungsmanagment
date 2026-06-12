"""Gemeinsame Enums (verwendet von Modellen, Schemas und Agenten)."""
from __future__ import annotations

from enum import Enum


class Kategorie(str, Enum):
    KFZ = "KFZ"
    HAFTPFLICHT = "Haftpflicht"
    HAUSRAT = "Hausrat"
    GEBAEUDE = "Gebäude"
    KRANKEN = "Kranken"
    ZAHNZUSATZ = "Zahnzusatz"
    UNFALL = "Unfall"
    RECHTSSCHUTZ = "Rechtsschutz"
    LEBEN = "Leben"
    REISE = "Reise"
    TIER = "Tier"
    GERAETE = "Geräteversicherung"
    SONSTIGE = "Sonstige"


class Zahlungsintervall(str, Enum):
    MONATLICH = "monatlich"
    VIERTELJAEHRLICH = "vierteljährlich"
    HALBJAEHRLICH = "halbjährlich"
    JAEHRLICH = "jährlich"
    EINMALIG = "einmalig"
    UNBEKANNT = "unbekannt"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Handlungsbedarf(str, Enum):
    KEINER = "keiner"
    PRUEFEN = "pruefen"
    HANDELN = "handeln"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# Mapping: Tage vor Ablauf → Pushover-Priorität
NOTIFICATION_TRIGGERS_DAYS = (90, 30, 7)
PRIORITY_HIGH_DAYS = 7  # ≤7 Tage → priority=1

# Anzahl Zahlungen pro Jahr je Intervall (praemie_eur ist der Betrag je Zahlung)
INTERVALS_PER_YEAR: dict[Zahlungsintervall, int] = {
    Zahlungsintervall.MONATLICH: 12,
    Zahlungsintervall.VIERTELJAEHRLICH: 4,
    Zahlungsintervall.HALBJAEHRLICH: 2,
    Zahlungsintervall.JAEHRLICH: 1,
    Zahlungsintervall.EINMALIG: 0,
    Zahlungsintervall.UNBEKANNT: 1,
}
