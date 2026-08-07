from PySide6.QtWidgets import QApplication


def get_screen_size() -> tuple[int, int]:
    """Get the primary screen dimensions."""
    try:
        screen = QApplication.primaryScreen()
        if screen:
            size = screen.size()
            w, h = size.width(), size.height()
            if isinstance(w, int) and isinstance(h, int):
                return w, h
    except (RuntimeError, AttributeError):
        pass
    return 1024, 768  # Fallback

def center_on_screen(width: int, height: int) -> tuple[int, int]:
    """Return top-left coordinates to centre a window of (width,height) on the primary screen."""
    from abib import utils
    screen_w, screen_h = utils.get_screen_size()
    w_origin = max(0, int((screen_w - width) / 2))
    h_origin = max(0, int((screen_h - height) / 2))
    return w_origin, h_origin

def fit_to_screen(window_width: int, window_height: int) -> tuple[int, int]:
    """Shrink window size to fit within the current screen with a small margin."""
    from abib import utils
    screen_w, screen_h = utils.get_screen_size()
    if window_height > screen_h:
        window_height = int(screen_h * 0.95)
    if window_width > screen_w:
        window_width = int(screen_w * 0.95)
    return window_width, window_height
