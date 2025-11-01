from __future__ import annotations

from typing import Optional

try:
    # Type hints only; importing lazily for environments without Qt
    from PySide6.QtWidgets import QWidget, QPlainTextEdit
    from PySide6.QtPrintSupport import QPrintDialog
except Exception:  # pragma: no cover - allow import without Qt
    QWidget = object  # type: ignore
    QPlainTextEdit = object  # type: ignore
    QPrintDialog = object  # type: ignore


class PrintingService:
    """Wraps Qt printing so UI code stays thin and testable."""

    def print_plain_text(self, editor: Optional[QPlainTextEdit], parent: Optional[QWidget] = None) -> bool:
        """Open a print dialog and print the given plain text editor.

        Returns True if a print job was accepted and attempted; False if canceled
        or editor is None.
        """
        if editor is None:
            return False
        try:
            dlg = QPrintDialog(parent)
            if hasattr(dlg, "exec_") and dlg.exec_():
                # QPlainTextEdit provides print_(QPrinter)
                editor.print_(dlg.printer())
                return True
            return False
        except Exception:
            # Swallow printing errors; caller can show a status message if needed
            return False
