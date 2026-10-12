"""Automated regression tests for small-screen layout, responsive sizing, and scrolling."""
import sys
import unittest
from unittest import mock
import tkinter as tk
from tkinter import ttk
from support import AppCase, rs


class LayoutGeometryTests(AppCase):
    def test_window_minsize_and_usable_screen_area(self):
        app = self.make_app()
        minsize = self.root.minsize()
        self.assertEqual(minsize, (640, 400))

        width, height = rs.get_usable_screen_area(self.root)
        self.assertGreaterEqual(width, 640)
        self.assertGreaterEqual(height, 400)

    def test_windows_workarea_fallback(self):
        # Test ctypes SPI_GETWORKAREA logic when on win32
        class MockRect:
            def __init__(self, left, top, right, bottom):
                self.left = left
                self.top = top
                self.right = right
                self.bottom = bottom

        mock_rect = MockRect(0, 0, 1280, 760)
        mock_ctypes = mock.MagicMock()
        mock_ctypes.wintypes.RECT.return_value = mock_rect
        mock_ctypes.windll.user32.SystemParametersInfoW.return_value = 1

        with mock.patch.dict(sys.modules, {'ctypes': mock_ctypes, 'ctypes.wintypes': mock_ctypes.wintypes}):
            with mock.patch('sys.platform', 'win32'):
                area = rs.get_usable_screen_area(self.root)
                self.assertEqual(area, (1280, 760))

    def test_layout_elements_mapped_at_1280x800(self):
        app = self.make_app()
        self.root.geometry('1280x800+0+0')
        self.root.deiconify()
        self.root.update()

        # Key action buttons and indicators must be mapped and visible
        self.assertEqual(app.copy_button.winfo_ismapped(), 1)
        self.assertEqual(app.delete_button.winfo_ismapped(), 1)
        self.assertEqual(app.progress.winfo_ismapped(), 1)
        self.assertEqual(app.terminal_button.winfo_ismapped(), 1)

        # On a 1280x800 target screen, the content fits comfortably without outer scrollbars
        self.assertEqual(app.outer_vscroll.winfo_ismapped(), 0)
        self.assertEqual(app.outer_hscroll.winfo_ismapped(), 0)

    def test_layout_elements_mapped_at_1024x768(self):
        app = self.make_app()
        self.root.geometry('1024x768+0+0')
        self.root.deiconify()
        self.root.update()

        # Bottom action controls remain mapped
        self.assertEqual(app.copy_button.winfo_ismapped(), 1)
        self.assertEqual(app.delete_button.winfo_ismapped(), 1)
        self.assertEqual(app.progress.winfo_ismapped(), 1)

    def test_outer_scrollbars_appear_on_compact_window(self):
        app = self.make_app()
        self.root.geometry('640x400+0+0')
        self.root.deiconify()
        self.root.update()

        # On small 640x400 window, content overflows and scrollbars appear
        self.assertTrue(app.outer_vscroll.winfo_ismapped() == 1 or app.outer_hscroll.winfo_ismapped() == 1)

        # Scrolling canvas works without errors
        app.outer_canvas.yview_scroll(1, 'units')
        app.outer_canvas.xview_scroll(1, 'units')
        app.outer_canvas.yview_moveto(0.0)
        app.outer_canvas.xview_moveto(0.0)


class ThumbnailGridReflowTests(AppCase):
    def test_calculate_columns(self):
        app = self.make_app()
        # Fallback for unmapped or zero-width canvas
        self.assertEqual(app.calculate_columns(0), 4)
        self.assertEqual(app.calculate_columns(1), 4)
        # 1 column minimum
        self.assertEqual(app.calculate_columns(100), 1)
        # 2 columns at ~340px
        self.assertEqual(app.calculate_columns(340), 2)
        # 4 columns at ~670px
        self.assertEqual(app.calculate_columns(670), 4)
        # 5 columns at ~850px
        self.assertEqual(app.calculate_columns(850), 5)
        # Clamped to max 12 columns
        self.assertEqual(app.calculate_columns(3000), 12)

    def test_reflow_grid_repositions_cards(self):
        from pathlib import Path
        app = self.make_app()
        # Create dummy cards and paths
        paths = [Path(f'game{i}.zip') for i in range(10)]
        app.filtered = paths
        app.page = 0
        cards = {}
        for i, p in enumerate(paths):
            card = ttk.Frame(app.grid)
            card.grid(row=i // 4, column=i % 4)
            cards[p] = (card, None, None)
        app.cards = cards

        # Reflow to 3 columns
        app.current_cols = 3
        app.reflow_grid()
        for i, p in enumerate(paths):
            card = cards[p][0]
            info = card.grid_info()
            self.assertEqual(int(info['column']), i % 3)
            self.assertEqual(int(info['row']), i // 3)

        # Reflow to 6 columns
        app.current_cols = 6
        app.reflow_grid()
        for i, p in enumerate(paths):
            card = cards[p][0]
            info = card.grid_info()
            self.assertEqual(int(info['column']), i % 6)
            self.assertEqual(int(info['row']), i // 6)


class MouseWheelIsolationTests(AppCase):
    def test_inner_wheel_returns_break(self):
        app = self.make_app()
        event = mock.MagicMock()
        event.delta = -120
        event.num = '??'
        result = app.wheel(event)
        self.assertEqual(result, 'break')

    def test_outer_wheel_ignores_events_from_inner_scrollables(self):
        app = self.make_app()
        # Mock outer canvas yview_scroll
        app.outer_canvas.yview_scroll = mock.MagicMock()

        event = mock.MagicMock()
        event.delta = -120
        event.num = '??'

        # Event from inside local canvas
        event.widget = app.canvas
        app.outer_wheel(event)
        app.outer_canvas.yview_scroll.assert_not_called()

        # Event from inside treeview
        event.widget = app.tree
        app.outer_wheel(event)
        app.outer_canvas.yview_scroll.assert_not_called()

        # Event from inside scrollbars
        event.widget = app.local_scroll
        app.outer_wheel(event)
        app.outer_canvas.yview_scroll.assert_not_called()

        event.widget = app.remote_scroll
        app.outer_wheel(event)
        app.outer_canvas.yview_scroll.assert_not_called()

        # Event from outer container or labels scrolls outer canvas
        event.widget = app.main_frame
        app.outer_wheel(event)
        app.outer_canvas.yview_scroll.assert_called_once_with(1, 'units')


if __name__ == '__main__':
    unittest.main()
