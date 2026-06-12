"""Test-Konfiguration: isolierte Test-Datenbank in tmp_path."""
from __future__ import annotations

import os
import tempfile

# Test-spezifische Settings vor dem Import setzen
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="vers_test_"))
