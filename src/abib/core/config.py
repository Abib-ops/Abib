# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any


def get_default_settings() -> dict[str, Any]:
    """Return a fresh copy of Abib's default settings dictionary.
    This centralises defaults so other components (e.g. Settings dialog reset)
    can align with the same values used by SettingsService.
    """
    return {
        "theme": "Light",
        # Default to not showing the splash screen
        # (older machines benefit from faster startup).
        # This is a boolean.
        "show_splash": False,
        "unified_font_size": False,
        "devotional_font_size": 12,
        "bible_font_size": 12,
        # Font size for the 'Other Works' reader window
        "reader_font_size": 12,
        # Whether scripture popups in the reader should automatically scroll the view
        # if the popup otherwise obscures the reference itself.
        "reader_auto_scroll_popups": True,
        "main_window": {
            "x": 25,
            "y": 41,
            "width": 555,
            "height": 599
        },
        "devotional_window": {
            "x": 160,
            "y": 50,
            "width": 350,
            "height": 599
        },
        "reader_window": {
            "x": 100,
            "y": 100,
            "width": 736,
            "height": 599,
        },
        "about_window": {
            "x": 100,
            "y": 100,
            "width": 480,
            "height": 500
        },
        "find_window": {
            "x": 100,
            "y": 100,
            "width": 640,
            "height": 334
        },
        "settings_window": {
            "x": 100,
            "y": 100,
            "width": 400,
            "height": 500
        },
        "reader_find_window": {
            "x": 100,
            "y": 100,
            "width": 500,
            "height": 100
        },
        "last_bible_position": 0,
        # Width (in pixels) of the dockable Search Results panel.
        "search_results_width": 400,
        "gill_hover_delay_ms": 120,
        "gill_hide_delay_ms": 160,
        "gill_show_popups": True,
        # Map of the 'Other Works' file stems to string booleans "true"/"false" indicating
        # whether they should be shown in the reader window combo box.
        # This map is generated and kept in sync at the application startup based on
        # the contents of the "Other Works" folder.
        # Defaults are "false".
        "show_work":{},
        "_comment": "This is a comment. It will be ignored by the program...",
        "last_other_work": "Pilgrims-Progress",
        "last_read_positions": {
            "Pilgrims-Progress": [624, 50, 70, 736, 599],
            "Institutes": [0, 50, 70, 736, 599],
            "Naves Topical Bible": [0, 50, 70, 736, 599],
            # Reserved for future commentary integrations (e.g. John Gill)
            "Catechisms John Owen": [0, 50, 70, 736, 599],
            "Commentary on Galatians Luther": [0, 50, 70, 736, 599],
            "Election A. W. Pink": [0, 50, 70, 1232, 599],
            "Election C. D. Cole": [0, 50, 70, 736, 599],
            "Pneumatologia": [0, 50, 70, 736, 599],
            "Puritan Catechism": [0, 50, 70, 736, 599],
            "Sermons on Proverbs": [0, 50, 70, 736, 599],
            "Small Catechism Luther": [0, 50, 70, 736, 599],
            "Systematic Theology - Vol. I": [0, 50, 70, 736, 599],
            "Systematic Theology - Vol. II": [0, 50, 70, 736, 599],
            "Systematic Theology - Vol. III": [0, 50, 70, 736, 599],
            "The Holy War": [0, 50, 70, 736, 599],
        }
    }
