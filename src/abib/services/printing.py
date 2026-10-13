# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from typing import Any, Protocol

try:
    # Import minimal Qt types; allow this module to import without Qt
    # noinspection PyPackageRequirements
    from PySide6.QtCore import QSizeF

    # noinspection PyPackageRequirements
    from PySide6.QtGui import QFont, QTextDocument

    # noinspection PyPackageRequirements
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter

    # noinspection PyPackageRequirements
    from PySide6.QtWidgets import QWidget
except ImportError:  # pragma: no cover - allow import without Qt
    QWidget = object  # type: ignore
    QPrintDialog = object  # type: ignore
    QPrinter = object  # type: ignore
    QTextDocument = object  # type: ignore
    QFont = object  # type: ignore
    QSizeF = object  # type: ignore


class EditorPrinter(Protocol):
    """Protocol for editors/widgets that support Qt printing via print_."""

    def print_(self, printer) -> None: ...


class PrintingService:
    """Wraps Qt printing so UI code stays thin and testable."""

    @staticmethod
    def print_plain_text(editor: EditorPrinter | None, parent: QWidget | None = None) -> bool:
        """Open a print dialog and print the given editor's document or selection.

        A high-resolution ``QPrinter`` is created and bound to the dialog, so the
        output is rendered at the printer's native resolution (printing at the
        default screen resolution is what corrupts/mis-scales the output). When
        the editor has a selection, the dialog opens with the "Selection" option
        pre-selected so that, by default, only the highlighted text is printed;
        the user can switch to "All" in the dialog to print the whole document.

        Returns True if a print job was accepted and attempted; False if cancelled,
        or editor is None.
        """
        if editor is None:
            return False
        try:
            # Use local references with type hints to satisfy the linter,
            # especially when QWidget is potentially aliased to object
            p: Any = parent
            # QPrinter has a module-level fallback alias to ``object`` (for the
            # no-Qt import path), which makes static checkers think the real
            # ``QPrinter.PrinterMode`` enum is missing; suppress that false positive.
            # noinspection PyUnresolvedReferences
            printer: Any = QPrinter(QPrinter.PrinterMode.HighResolution)
            dlg: Any = QPrintDialog(printer, p)

            # Offer the "Selection" option only when something is selected.
            cursor: Any = None
            has_selection = False
            try:
                get_cursor = getattr(editor, "textCursor", None)
                if callable(get_cursor):
                    # get_cursor is guaranteed callable here (checked above), but
                    # its getattr default of None makes static checkers warn.
                    # noinspection PyCallingNonCallable
                    cursor = get_cursor()
                    has_selection = bool(cursor is not None and cursor.hasSelection())
            except (RuntimeError, AttributeError, TypeError):
                cursor = None
                has_selection = False

            if has_selection:
                try:
                    # QPrintDialog has a module-level fallback alias to ``object``
                    # (for the no-Qt import path), which makes static checkers think
                    # the real ``QPrintDialog.PrintDialogOption`` enum is missing;
                    # suppress that false positive.
                    # noinspection PyUnresolvedReferences
                    dlg.setOption(QPrintDialog.PrintDialogOption.PrintSelection, True)
                except (RuntimeError, AttributeError, TypeError):
                    pass
                try:
                    # Pre-select the "Selection" radio so the highlighted portion
                    # is what prints by default. The dialog reads the printer's
                    # current print range to decide which radio is active; without
                    # this it defaults to "All Pages", so the user has to spot and
                    # tick "Selection" manually. They can still switch to "All" in
                    # the dialog. (``QPrinter.PrintRange`` is flagged as missing by
                    # static checkers because of the no-Qt ``object`` alias.)
                    # noinspection PyUnresolvedReferences
                    printer.setPrintRange(QPrinter.PrintRange.Selection)
                except (RuntimeError, AttributeError, TypeError):
                    pass

            # Support both exec() (PySide6) and exec_() (compat)
            accepted = False
            if hasattr(dlg, "exec"):
                accepted = bool(dlg.exec())
            elif hasattr(dlg, "exec_"):
                accepted = bool(dlg.exec_())
            if not accepted:
                return False

            # If the user explicitly asked for the selection, print only that.
            # Default to the selection whenever one exists, so the feature is
            # discoverable instead of hidden behind the dialog's radio button.
            want_selection = has_selection
            if has_selection:
                try:
                    # QPrintDialog has a module-level fallback alias to ``object``
                    # (for the no-Qt import path), which makes static checkers think
                    # the real ``QPrintDialog.PrintRange`` enum is missing; suppress
                    # that false positive.
                    # noinspection PyUnresolvedReferences
                    want_selection = bool(
                        dlg.printRange() == QPrintDialog.PrintRange.Selection
                    )
                except (RuntimeError, AttributeError, TypeError):
                    want_selection = False

            # Render through a FRESH document instead of ``editor.print_()``.
            # The editor's document carries on-screen styling that must never
            # reach paper: a QSyntaxHighlighter applies search/verse highlight
            # colours (and in dark mode light-on-dark colours), which otherwise
            # print as coloured/near-white, unreadable ("corrupted") output.
            # Using plain text on a default document guarantees clean black
            # glyphs on a white page while keeping the editor's font.
            doc = QTextDocument()

            # Use an explicit, readable print font rather than relying on the
            # on-screen font being resolvable by the print engine. Keep the
            # editor's font (and point size) when it is available.
            try:
                font = QFont("Cascadia Mono")
            except (RuntimeError, TypeError):
                font = None
            try:
                get_doc = getattr(editor, "document", None)
                if callable(get_doc):
                    # get_doc is guaranteed callable here (checked above), but
                    # its getattr default of None makes static checkers warn.
                    # noinspection PyCallingNonCallable
                    src_doc = get_doc()
                    if src_doc is not None:
                        font = QFont(src_doc.defaultFont())
            except (RuntimeError, AttributeError, TypeError):
                pass
            if font is not None:
                doc.setDefaultFont(font)

            if want_selection and cursor is not None:
                text = cursor.selection().toPlainText()
            else:
                text = ""
                get_text = getattr(editor, "toPlainText", None)
                if callable(get_text):
                    # noinspection PyCallingNonCallable
                    text = get_text()
            doc.setPlainText(text)

            # CRITICAL: lay the document out against the real printer page.
            # Without this, a HighResolution printer renders glyphs at its
            # native DPI while the layout is computed against a default,
            # undersized width, so lines run off the page or pile up -- the
            # classic cause of mis-scaled / clipped ("corrupted") output.
            try:
                layout = doc.documentLayout()
                if layout is not None:
                    layout.setPaintDevice(printer)
                # noinspection PyUnresolvedReferences
                page = printer.pageRect(QPrinter.Unit.DevicePixel)
                doc.setPageSize(QSizeF(page.size()))
                doc.setTextWidth(page.width())
            except (RuntimeError, AttributeError, TypeError):
                pass

            doc.print_(printer)
            return True
        except (RuntimeError, AttributeError, TypeError):
            # Swallow printing errors; caller can show a status message if needed
            return False
