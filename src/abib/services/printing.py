# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Protocol

try:
    # Import minimal Qt types; allow this module to import without Qt
    from PySide6.QtPrintSupport import QPrintDialog
    from PySide6.QtWidgets import QWidget
except ImportError:  # pragma: no cover - allow import without Qt
    QWidget = object  # type: ignore
    QPrintDialog = object  # type: ignore


class EditorPrinter(Protocol):
    """Protocol for editors/widgets that support Qt printing via print_."""

    def print_(self, printer) -> None: ...


class PrintingService:
    """Wraps Qt printing so UI code stays thin and testable."""

    @staticmethod
    def print_plain_text(editor: EditorPrinter | None, parent: QWidget | None = None) -> bool:
        """Open a print dialog and print the given plain text editor.

        Returns True if a print job was accepted and attempted; False if cancelled,
        or editor is None.
        """
        if editor is None:
            return False
        try:
            # Use a local reference with a type hint to satisfy the linter,
            # especially when QWidget is potentially aliased to object
            p: Any = parent
            dlg = QPrintDialog(p)
            # Support both exec() (PySide6) and exec_() (compat)
            accepted = False
            if hasattr(dlg, "exec"):
                accepted = bool(dlg.exec())
            elif hasattr(dlg, "exec_"):
                accepted = bool(dlg.exec_())
            d: Any = dlg
            if accepted:
                editor.print_(d.printer())
                return True
            return False
        except (RuntimeError, AttributeError, TypeError):
            # Swallow printing errors; caller can show a status message if needed
            return False
