"""Small per-pixel-alpha window and its mouse controls."""

from __future__ import annotations

from ctypes import wintypes
from math import atan2, copysign, cos, degrees, hypot, radians, sin
from pathlib import Path
from random import choice
from time import perf_counter
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSettings, QTimer, Qt
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QPainter, QScreen
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
    QSystemTrayIcon,
)

from .behavior import Activity, Behavior
from .character import MechanicalPuppet
from .feedback import play_click
from .movement import advance, clamp_origin, weighted_offset
from .navigation import Edge, WindowRoute
from .settings import Preferences, SettingsDialog

if TYPE_CHECKING:
    from .windows import ForegroundWindow

_WM_CANCELMODE = 0x001F
_WM_CAPTURECHANGED = 0x0215


class Overlay(QGraphicsView):
    WIDTH = MechanicalPuppet.WIDTH
    HEIGHT = MechanicalPuppet.HEIGHT
    FRAME_MS = 16

    def __init__(self, speed: float, paused: bool, store: QSettings | None = None,
                 *, startup: bool = False) -> None:
        super().__init__()
        self._press: QPoint | None = None
        self._startup_pending = startup
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Arachnid")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setMouseTracking(True)
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)

        scene = QGraphicsScene(0, 0, self.WIDTH, self.HEIGHT, self)
        self.setScene(scene)
        self._store = store if store is not None else QSettings("ARACHNID", "Desktop Companion")
        self._preferences = Preferences.load(self._store)
        self._resize_pet()
        self._settings_dialog: SettingsDialog | None = None
        self._puppet = MechanicalPuppet(self._preferences.finish)
        self._puppet.set_birdseye(self._preferences.birdseye)
        self._puppet.set_curled_sleep(self._preferences.curled_sleep)
        self._puppet.intro_finished.connect(self._sync_timers)
        scene.addItem(self._puppet)
        self._hovered = False
        self._update_appearance()

        self._velocity = speed
        self._heading = radians(-32)
        self._speed_scale = 0.0
        self._behavior = Behavior()
        self._foreground: ForegroundWindow | None = None
        self._route: WindowRoute | None = None
        self.fullscreen_suppressed = False
        self._user_hidden = False
        self._paused = paused
        self._drag_offset = QPoint()
        self._dragging = False
        self._drag_cursor: QPoint | None = None
        self._drag_position = QPointF()
        self._last_drag_tick = 0.0

        self._menu = QMenu(self)
        self._pause_action = self._menu.addAction("Resume" if paused else "Pause")
        self._pause_action.triggered.connect(self._toggle_pause)
        self._rest_action = self._menu.addAction("Rest", self._toggle_rest)
        self._settings_action = self._menu.addAction("Settings…", self._open_settings)
        self._quit_action = self._menu.addAction("Quit Arachnid", self._quit)
        self._quitting = False
        self._menu.aboutToShow.connect(self._suspend_for_menu)
        self._menu.aboutToHide.connect(self._resume_after_menu)
        self._menu_open = False
        self._tray: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None

        self._last_tick = perf_counter()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._step)
        self._last_decision = self._last_tick
        self._behavior_timer = QTimer(self)
        self._behavior_timer.setInterval(125)
        self._behavior_timer.timeout.connect(self._advance_behavior)
        self._drag_timer = QTimer(self)
        self._drag_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._drag_timer.setInterval(self.FRAME_MS)
        self._drag_timer.timeout.connect(self._drag_step)
        self._capture_lost = QTimer(self)
        self._capture_lost.setSingleShot(True)
        self._capture_lost.timeout.connect(self._end_press)
        self._screen_update = QTimer(self)
        self._screen_update.setSingleShot(True)
        self._screen_update.timeout.connect(self._keep_visible)

        app = QGuiApplication.instance()
        for screen in app.screens():
            self._watch_screen(screen)
        app.screenAdded.connect(self._watch_screen)
        app.screenRemoved.connect(self._screen_changed)
        app.primaryScreenChanged.connect(self._screen_changed)

        self._x = float(self.x())
        self._y = float(self.y())
        screen = app.primaryScreen()
        if screen is not None:
            start = screen.availableGeometry().center() - QPoint(self.width() // 2, self.height() // 2)
            self._place(start, screen)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._startup_pending:
            self._startup_pending = False
            self._puppet.start_intro()
        self._sync_timers()

    def hideEvent(self, event) -> None:
        self._end_press()
        self._puppet.finish_animations()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        if (self._tray is not None and self._tray.isVisible()
                and self._tray.isSystemTrayAvailable() and not self._quitting
                and not QApplication.instance().isSavingSession()):
            event.ignore()
            if self._settings_dialog is not None:
                self._settings_dialog.reject()
            self._set_user_hidden(True)
            return
        if self._tray is not None:
            self._tray_menu.close()
            self._tray.hide()
        if self._settings_dialog is not None:
            self._settings_dialog.reject()
        self._timer.stop()
        self._drag_timer.stop()
        self._behavior_timer.stop()
        super().closeEvent(event)
        QApplication.quit()

    def _quit(self) -> None:
        self._quitting = True
        self.close()

    def install_tray(self) -> None:
        icon = QIcon(str(Path(__file__).with_name("assets") / "arachnid.ico"))
        self._tray_menu = QMenu(self)
        self._visibility_action = self._tray_menu.addAction("Hide Arachnid", self._toggle_visibility)
        self._menu.insertAction(self._quit_action, self._visibility_action)
        self._tray_menu.addAction(self._pause_action)
        self._tray_menu.addAction(self._rest_action)
        self._tray_menu.addAction(self._settings_action)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(self._quit_action)
        self._tray_menu.aboutToShow.connect(self._suspend_for_menu)
        self._tray_menu.aboutToHide.connect(self._resume_after_menu)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Arachnid")
        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _toggle_visibility(self) -> None:
        self._set_user_hidden(not self._user_hidden)

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.reopen()

    def reopen(self) -> None:
        self._set_user_hidden(False)

    def _set_user_hidden(self, hidden: bool) -> None:
        self._user_hidden = hidden
        if self._user_hidden:
            self.hide()
        elif not self.fullscreen_suppressed:
            self._keep_visible()
            self.show()
        self._visibility_action.setText("Show Arachnid" if self._user_hidden else "Hide Arachnid")

    def _watch_screen(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(self._screen_changed)
        screen.geometryChanged.connect(self._screen_changed)
        screen.logicalDotsPerInchChanged.connect(self._screen_changed)
        self._screen_changed()

    def _screen_changed(self) -> None:
        # Let Qt finish processing the display change before querying screens.
        self._screen_update.start(0)

    def _current_screen(self) -> QScreen | None:
        center = self.frameGeometry().center()
        screen = QGuiApplication.screenAt(center)
        if screen is not None:
            return screen

        primary = QGuiApplication.primaryScreen()

        def proximity(candidate: QScreen) -> tuple[int, bool]:
            area = candidate.availableGeometry()
            x = clamp_origin(center.x(), area.x(), area.width(), 1)
            y = clamp_origin(center.y(), area.y(), area.height(), 1)
            return ((center.x() - x)**2 + (center.y() - y)**2, candidate != primary)

        return min(QGuiApplication.screens(), key=proximity, default=primary)

    def _place(self, position: QPoint, screen: QScreen) -> None:
        area = screen.availableGeometry()
        x = clamp_origin(position.x(), area.x(), area.width(), self.width())
        y = clamp_origin(position.y(), area.y(), area.height(), self.height())
        self.move(x, y)
        self._x = float(x)
        self._y = float(y)

    def _keep_visible(self) -> None:
        grab_point = self._drag_cursor if self._dragging else self._press
        if grab_point is not None and QGuiApplication.screenAt(grab_point) is None:
            self._end_press()
        screen = self._current_screen()
        if screen is not None:
            self._place(self.pos(), screen)
            if self._dragging:
                self._drag_position = QPointF(self.pos())
        self._follow_window()
        self._sync_timers()

    def set_foreground(self, window: ForegroundWindow | None) -> None:
        previous = self._foreground
        self._foreground = window
        suppressed = window is not None and window.fullscreen
        was_suppressed = self.fullscreen_suppressed
        self.fullscreen_suppressed = suppressed
        if self._route is not None:
            if window is None or previous is None or window.key != previous.key:
                self._leave_window()
            else:
                self._follow_window()

        if suppressed and not was_suppressed:
            self._menu.close()
            if self._tray_menu is not None:
                self._tray_menu.close()
            self._settings_action.setEnabled(False)
            if self._settings_dialog is not None:
                self._settings_dialog.reject()
            self.hide()
        elif was_suppressed and not suppressed:
            self._settings_action.setEnabled(True)
            if not self._user_hidden:
                self._keep_visible()
                self.show()

    def _surface(self, screen: QScreen) -> QRectF | None:
        window = self._foreground
        if window is None or not window.navigable:
            return None
        bounds, monitor = window.bounds, window.monitor
        geometry = screen.geometry()
        if (geometry.x(), geometry.y()) != (monitor.left, monitor.top):
            return None
        if (bounds.left < monitor.left or bounds.right > monitor.right
                or bounds.top < monitor.top or bounds.bottom > monitor.bottom):
            return None

        # On Windows, Qt scales dimensions and offsets from each monitor origin.
        scale = screen.devicePixelRatio()
        # A display change can leave a native snapshot from the previous topology.
        tolerance = max(2, scale)
        if (abs(geometry.width() * scale - (monitor.right - monitor.left)) > tolerance
                or abs(geometry.height() * scale - (monitor.bottom - monitor.top)) > tolerance):
            return None
        return QRectF(
            geometry.x() + (bounds.left - monitor.left) / scale,
            geometry.y() + (bounds.top - monitor.top) / scale,
            (bounds.right - bounds.left) / scale,
            (bounds.bottom - bounds.top) / scale,
        )

    def _allowed_centers(self, screen: QScreen) -> QRectF:
        return QRectF(screen.availableGeometry()).adjusted(
            self.width() / 2, self.height() / 2, -self.width() / 2, -self.height() / 2
        )

    def _try_window(self, travel: float = 0) -> bool:
        if self._preferences.birdseye:
            return False
        screen = self._current_screen()
        if screen is None:
            return False
        surface = self._surface(screen)
        if surface is None:
            return False
        center = QPointF(self._x + self.width() / 2, self.y() + self.height() / 2)
        facing = 1 if self._velocity > 0 else -1
        self._route = WindowRoute.near(surface, self._allowed_centers(screen), center, facing, travel, scale=self.width() / self.WIDTH)
        if self._route is None:
            return False
        self._puppet.stand(immediate=True)
        self._place_on_window(screen)
        return True

    def _follow_window(self) -> None:
        if self._route is None:
            return
        screen = self._current_screen()
        if screen is None:
            self._leave_window()
            return
        surface = self._surface(screen)
        if surface is None or not self._route.follow(surface, self._allowed_centers(screen)):
            self._leave_window()
        else:
            self._place_on_window(screen)

    def _place_on_window(self, screen: QScreen, distance: float = 0) -> None:
        pose = self._route.pose()
        position = pose.center - QPointF(self.width() / 2, self.height() / 2)
        self._place(position.toPoint(), screen)
        self._puppet.walk(distance, pose.facing, pose.angle)

    def _leave_window(self) -> None:
        if self._route is None:
            return
        self._route = None
        self._puppet.stand(immediate=True)
        self._puppet.walk(0, 1 if self._velocity > 0 else -1)

    def _sync_timers(self) -> None:
        active = self.isVisible() and QGuiApplication.primaryScreen() is not None and not (
            self.fullscreen_suppressed or self._paused or self._press is not None or self._menu_open
            or self._settings_dialog is not None or self._behavior.activity is Activity.SLEEPING
            or self._puppet.entering
        )
        if active and not self._behavior_timer.isActive():
            self._last_decision = perf_counter()
            self._behavior_timer.start()
        elif not active:
            self._behavior_timer.stop()

        walking = active and self._behavior.activity is Activity.WANDERING
        if walking and not self._timer.isActive():
            self._last_tick = perf_counter()
            self._speed_scale = 0.0
            self._timer.start()
        elif not walking:
            self._timer.stop()
            self._puppet.stand(immediate=self._press is not None or not self.isVisible())

    def _advance_behavior(self) -> None:
        now = perf_counter()
        elapsed = min(now - self._last_decision, 0.25)
        self._last_decision = now

        offset = QPoint()
        distance = None
        if self._behavior.activity in (Activity.WANDERING, Activity.OBSERVING):
            offset = QCursor.pos() - self.frameGeometry().center()
            distance = hypot(offset.x(), offset.y())

        if self._behavior.update(elapsed, distance):
            if self._preferences.birdseye:
                self._heading += choice((-1, 1)) * radians(70)
            elif self._route is None:
                self._velocity = -self._velocity
            else:
                self._route.reverse()

        gaze = (0, 0)
        if self._behavior.activity is Activity.OBSERVING and distance is not None:
            scale = 3 / max(distance, 20)
            gaze = (round(offset.x() * scale), round(offset.y() * scale))
        self._show_activity(gaze)
        self._sync_timers()

    def _step(self) -> None:
        now = perf_counter()
        # Discard long pauses caused by a suspended or busy desktop.
        elapsed = min(now - self._last_tick, 0.05)
        self._last_tick = now
        screen = self._current_screen()
        if screen is None:
            self._sync_timers()
            return
        climbing = self._route is not None and self._route.edge in (Edge.SIDE, Edge.CORNER)
        target_scale = 0.72 if climbing else 1.0
        change = elapsed / 0.18
        previous_scale = self._speed_scale
        self._speed_scale += min(change, max(-change, target_scale - self._speed_scale))
        moving_time = elapsed * (previous_scale + self._speed_scale) / 2
        distance = abs(self._velocity) * moving_time
        if self._preferences.birdseye:
            self._step_overhead(screen, moving_time, elapsed)
            return
        if self._route is not None:
            self._route.advance(distance)
            self._place_on_window(screen, distance)
            return
        if distance and self._try_window(distance):
            return

        area = screen.availableGeometry()
        right = area.x() + max(0, area.width() - self.width())
        self._x, self._velocity = advance(
            self._x, self._velocity, moving_time, area.x(), right
        )
        if right > area.x():
            direction = 1 if self._velocity > 0 else -1
            self._puppet.walk(distance, direction)
        else:
            self._puppet.stand()
        x = round(self._x)
        y = clamp_origin(self.y(), area.y(), area.height(), self.height())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)
        self._y = float(y)

    def _step_overhead(self, screen: QScreen, moving_time: float, elapsed: float) -> None:
        area = screen.availableGeometry()
        right = area.x() + max(0, area.width() - self.width())
        bottom = area.y() + max(0, area.height() - self.height())
        # Shorten the stride while the body pivots toward its new heading.
        alignment = cos(self._heading - radians(self._puppet.angle))
        speed = abs(self._velocity) * (0.25 + 0.75 * max(0.0, alignment))
        vx, vy = speed * cos(self._heading), speed * sin(self._heading)
        if right == area.x():
            vx, vy = 0.0, copysign(speed, vy) if bottom > area.y() else 0.0
        elif bottom == area.y():
            vx, vy = copysign(speed, vx), 0.0
        self._x, vx = advance(self._x, vx, moving_time, area.x(), right)
        self._y, vy = advance(self._y, vy, moving_time, area.y(), bottom)
        x, y = round(self._x), round(self._y)
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)
        distance = hypot(vx, vy) * moving_time
        if distance:
            self._heading = atan2(vy, vx)
            delta = (degrees(self._heading) - self._puppet.angle + 180) % 360 - 180
            limit = elapsed * 420
            turn = delta * min(1.0, 9 * elapsed)
            angle = self._puppet.angle + min(limit, max(-limit, turn))
            self._puppet.walk(distance, 1, angle)
        else:
            self._puppet.stand()

    def _update_appearance(self) -> None:
        self._puppet.set_appearance(self._hovered)

    def _end_press(self) -> None:
        self._capture_lost.stop()
        self._drag_timer.stop()
        self._drag_cursor = None
        self._press = None
        self._dragging = False
        self._puppet.set_held(False)
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        self._sync_timers()

    def viewportEvent(self, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.Enter:
            self._hovered = True
            self._update_appearance()
        elif kind == QEvent.Type.Leave:
            self._hovered = False
            self._update_appearance()
        elif kind == QEvent.Type.UngrabMouse and self._press is not None:
            self._end_press()
        return super().viewportEvent(event)

    def nativeEvent(self, event_type, message):
        if self._press is not None and event_type == b"windows_generic_MSG":
            kind = wintypes.MSG.from_address(int(message)).message
            if kind in (_WM_CANCELMODE, _WM_CAPTURECHANGED):
                # Windows also drops capture on regular release. Give Qt time
                # to deliver that release and stop this fallback timer.
                self._capture_lost.start(30)
        return super().nativeEvent(event_type, message)

    def mousePressEvent(self, event) -> None:
        self._puppet.skip_intro()
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._drag_offset = event.position().toPoint()
            self._sync_timers()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressEvent(event)
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press is None:
            super().mouseMoveEvent(event)
            return
        if not event.buttons() & Qt.MouseButton.LeftButton:
            self._end_press()
            return

        cursor = event.globalPosition().toPoint()
        distance = (cursor - self._press).manhattanLength()
        if not self._dragging and distance >= QApplication.startDragDistance():
            self._dragging = True
            self._leave_window()
            self._drag_position = QPointF(self.pos())
            self._last_drag_tick = perf_counter()
            self._puppet.set_held(True)
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        if self._dragging:
            self._drag_cursor = cursor
            self._drag_step()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._press is not None:
            if self._dragging:
                self._drag_cursor = event.globalPosition().toPoint()
                self._drag_step(drop=True)
                self._try_window()
            elif self._behavior.activity is not Activity.SLEEPING:
                self._puppet.pet()
                if self._preferences.effects:
                    self._puppet.flash()
                if self._preferences.sound:
                    play_click()
                if not self._paused:
                    self._behavior.react_to_click()
                    self._show_activity()
            self._end_press()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _drag_step(self, *, drop: bool = False) -> None:
        cursor = self._drag_cursor
        screen = (QGuiApplication.screenAt(cursor) or self._current_screen()) if cursor is not None else None
        if screen is None:
            self._drag_timer.stop()
            return
        area = screen.availableGeometry()
        origin = cursor - self._drag_offset
        target = QPointF(clamp_origin(origin.x(), area.x(), area.width(), self.width()),
                         clamp_origin(origin.y(), area.y(), area.height(), self.height()))
        now = perf_counter()
        gap = self._drag_position - target
        dx, dy = (0.0, 0.0) if drop else weighted_offset(
            gap.x(), gap.y(), min(now - self._last_drag_tick, 0.05)
        )
        if not drop:
            self._puppet.set_drag_lag(dx)
        self._last_drag_tick = now
        self._drag_position = target + QPointF(dx, dy)
        rounded = self._drag_position.toPoint()
        self._place(rounded, screen)
        if self.pos() != rounded:
            self._drag_position = QPointF(self.pos())
        if not dx and not dy:
            self._drag_timer.stop()
        elif not self._drag_timer.isActive():
            self._drag_timer.start()

    def contextMenuEvent(self, event) -> None:
        self._menu.popup(event.globalPos())
        event.accept()

    def _suspend_for_menu(self) -> None:
        self._menu_open = True
        self._sync_timers()

    def _resume_after_menu(self) -> None:
        self._menu_open = False
        self._sync_timers()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_action.setText("Resume" if self._paused else "Pause")
        self._sync_timers()

    def _show_activity(self, gaze: tuple[int, int] = (0, 0)) -> None:
        activity = self._behavior.activity
        self._rest_action.setText("Wake Up" if activity.resting else "Rest")
        self._puppet.set_activity(activity, gaze)
        if not self.isVisible():
            self._puppet.finish_animations()

    def _toggle_rest(self) -> None:
        if self._behavior.activity.resting:
            self._behavior.wake()
        else:
            self._behavior.sleep()
        self._show_activity()
        self._sync_timers()

    def _open_settings(self) -> None:
        if self._settings_dialog is not None or self.fullscreen_suppressed:
            return
        dialog = SettingsDialog(self._preferences, self._store, self)
        self._settings_dialog = dialog
        dialog.finished.connect(self._finish_settings)
        self._sync_timers()
        dialog.open()

    def _resize_pet(self) -> None:
        scale = self._preferences.size / 100
        self.resetTransform()
        self.scale(scale, scale)
        self.setFixedSize(round(self.WIDTH * scale), round(self.HEIGHT * scale))

    def _finish_settings(self, result: int) -> None:
        dialog = self._settings_dialog
        self._settings_dialog = None
        if result == QDialog.DialogCode.Accepted:
            if self._preferences.birdseye != dialog.preferences.birdseye:
                self._leave_window()
                self._puppet.set_birdseye(dialog.preferences.birdseye)
                self._x, self._y = float(self.x()), float(self.y())
            size_changed = self._preferences.size != dialog.preferences.size
            self._preferences = dialog.preferences
            if size_changed:
                center = self.frameGeometry().center()
                self._leave_window()
                self._resize_pet()
                self.move(center - QPoint((self.width() - 1) // 2, (self.height() - 1) // 2))
                self._x, self._y = float(self.x()), float(self.y())
                self._keep_visible()
            self._puppet.set_finish(self._preferences.finish)
            self._puppet.set_curled_sleep(self._preferences.curled_sleep)
        dialog.deleteLater()
        self._sync_timers()
