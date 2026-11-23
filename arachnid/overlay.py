"""Small per-pixel-alpha window and its mouse controls."""

from __future__ import annotations

from ctypes import wintypes
from dataclasses import dataclass
from math import atan2, copysign, cos, degrees, hypot, pi, radians, sin
from pathlib import Path
from random import choice
from time import perf_counter
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSettings, QTimer, Qt, QVariantAnimation
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
from .desktop_edges import (
    ATTACH_TIME, DesktopEdge, DesktopPose, DesktopRoute, DesktopTrack, SurfaceContact, smooth,
)
from .feedback import play_click
from .movement import advance, angle_delta, clamp_origin, ramp_speed, weighted_offset
from .navigation import Edge, WindowRoute
from .settings import Preferences, SettingsDialog
from .throwing import CursorHistory, MAX_RELEASE_SPEED, ThrowBounds, ThrowMotion

if TYPE_CHECKING:
    from .windows import ForegroundWindow

_WM_CANCELMODE = 0x001F
_WM_CAPTURECHANGED = 0x0215


@dataclass
class _EdgeTransfer:
    start: DesktopPose
    end: DesktopPose
    attaching: bool
    time: float = 0.0


class Overlay(QGraphicsView):
    WIDTH = MechanicalPuppet.WIDTH
    HEIGHT = MechanicalPuppet.HEIGHT
    FRAME_MS = 16
    WINDOW_MOUNT_TIME = 0.18

    def __init__(self, speed: float, paused: bool, store: QSettings | None = None,
                 *, startup: bool = False, desktop_preview: bool = False) -> None:
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
        self._braking = False
        self._behavior = Behavior()
        self._foreground: ForegroundWindow | None = None
        self._route: WindowRoute | None = None
        self._window_mount_offset = QPointF()
        self._window_mount_angle = 0.0
        self._window_mount_progress = 1.0
        self._window_mount = QVariantAnimation(self)
        self._window_mount.setDuration(round(self.WINDOW_MOUNT_TIME * 1000))
        self._window_mount.setStartValue(0.0)
        self._window_mount.setEndValue(1.0)
        self._window_mount.valueChanged.connect(self._set_window_mount)
        self._desktop_route: DesktopRoute | None = None
        self._desktop_transfer: _EdgeTransfer | None = None
        self._desktop_screen: QScreen | None = None
        self._desktop_geometry = None
        self._desktop_cooldown = 14.0
        self._desktop_reverse_pending = False
        self.fullscreen_suppressed = False
        self._user_hidden = False
        self._paused = paused
        self._drag_offset = QPoint()
        self._dragging = False
        self._drag_cursor: QPoint | None = None
        self._drag_position = QPointF()
        self._last_drag_tick = 0.0
        self._drag_floor_extension = 0
        self._cursor_history = CursorHistory()
        self._throw: ThrowMotion | None = None

        self._menu = QMenu(self)
        self._pause_action = self._menu.addAction("Resume" if paused else "Pause")
        self._pause_action.triggered.connect(self._toggle_pause)
        self._rest_action = self._menu.addAction("Rest", self._toggle_rest)
        if desktop_preview:
            edges = self._menu.addMenu("Desktop Edge Preview")
            edges.addAction("Climb Left Edge", lambda: self._preview_edge(-1))
            edges.addAction("Climb Right Edge", lambda: self._preview_edge(1))
            edges.addAction("Preview Upper Corner", lambda: self._preview_edge(-1, near_top=True))
            edges.addAction("Reverse Direction", self._reverse_desktop)
            edges.addAction("Detach", self._detach_desktop)
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
        self._cancel_throw()
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

    def _place(self, position: QPoint, screen: QScreen, *, floor_extension: int = 0) -> None:
        area = screen.availableGeometry()
        x = clamp_origin(position.x(), area.x(), area.width(), self.width())
        y = clamp_origin(position.y(), area.y(), area.height(), self.height() - floor_extension)
        self.move(x, y)
        self._x = float(x)
        self._y = float(y)

    def _keep_visible(self) -> None:
        grab_point = self._drag_cursor if self._dragging else self._press
        if grab_point is not None and QGuiApplication.screenAt(grab_point) is None:
            self._end_press()
        screen = self._current_screen()
        if self._throw is not None:
            bounds = self._throw_bounds(screen) if screen is not None else None
            if bounds is not None:
                self._throw.resize(bounds)
                self._move_throw()
                self._sync_timers()
                return
            self._cancel_throw()
        if self._desktop_route is not None:
            if self._desktop_matches(screen):
                self._sync_timers()
                return
            self._discard_desktop(screen)
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
        if self._throw is not None or self._preferences.birdseye or self._desktop_route is not None:
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
        pose = self._route.pose()
        self._window_mount_offset = self._center() - pose.center
        self._window_mount_angle = angle_delta(pose.angle, self._puppet.angle)
        self._window_mount_progress = 0.0
        self._place_on_window(screen)
        self._window_mount.start()
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

    def _set_window_mount(self, progress: float) -> None:
        self._window_mount_progress = progress
        if self._route is not None and self.isVisible() and self._press is None:
            screen = self._current_screen()
            if screen is not None:
                self._place_on_window(screen)

    def _place_on_window(self, screen: QScreen, distance: float = 0, elapsed: float = 0.0) -> None:
        pose = self._route.pose()
        center, angle = pose.center, pose.angle
        if self._window_mount_progress < 1:
            remaining = 1 - smooth(self._window_mount_progress)
            center += self._window_mount_offset * remaining
            angle += self._window_mount_angle * remaining
        position = center - QPointF(self.width() / 2, self.height() / 2)
        self._place(position.toPoint(), screen)
        self._puppet.walk(distance / self.transform().m11(), pose.facing, angle, elapsed=elapsed)

    def _leave_window(self) -> None:
        if self._route is None:
            return
        self._route = None
        self._window_mount.stop()
        self._window_mount_progress = 1.0
        self._puppet.stand()
        self._puppet.level_after_release()
        self._puppet.walk(0, 1 if self._velocity > 0 else -1)

    @staticmethod
    def _screen_key(screen: QScreen):
        return screen.geometry(), screen.availableGeometry(), screen.devicePixelRatio()

    def _desktop_matches(self, screen: QScreen | None) -> bool:
        return (screen is not None and screen is self._desktop_screen
                and self._desktop_geometry == self._screen_key(screen))

    def _desktop_track(self, screen: QScreen, side: int) -> DesktopTrack | None:
        if (self._route is not None or self._desktop_route is not None
                or self._preferences.birdseye or not self._allowed_centers(screen).isValid()):
            return None
        if (self._press is not None or self._settings_dialog is not None
                or self.fullscreen_suppressed or self._behavior.activity is Activity.SLEEPING):
            return None
        return DesktopTrack.from_screen(QRectF(screen.geometry()), QRectF(screen.availableGeometry()),
                                        side, self.transform().m11())

    def _attach_desktop(self, track: DesktopTrack, screen: QScreen) -> None:
        center = self._center()
        self._desktop_route = DesktopRoute(track, track.attach_at(center))
        self._desktop_screen = screen
        self._desktop_geometry = self._screen_key(screen)
        self._desktop_cooldown = 26.0
        target = self._desktop_route.pose()
        start = DesktopPose(center, 0, target.facing, DesktopEdge.SIDE)
        self._desktop_transfer = _EdgeTransfer(start, target, attaching=True)

    def _center(self) -> QPointF:
        return QPointF(self.x() + self.width() / 2, self.y() + self.height() / 2)

    def _preview_edge(self, side: int, *, near_top: bool = False) -> None:
        screen = self._current_screen()
        if screen is None or self._throw is not None or self._puppet.entering or not self.isVisible():
            return
        track = self._desktop_track(screen, side)
        if track is None:
            return
        area = screen.availableGeometry()
        x = area.x() if side < 0 else area.x() + area.width() - self.width()
        y = min(track.bottom, track.high + 44) if near_top else track.bottom
        self._place(QPoint(x, round(y - self.height() / 2)), screen)
        self._attach_desktop(track, screen)
        # The explicit preview overrides an idle decision, but honors Pause.
        self._behavior.wake()
        self._show_activity()
        self._sync_timers()

    def _reverse_desktop(self) -> None:
        if self._desktop_route is not None and self._desktop_transfer is None:
            self._desktop_reverse_pending = True

    def _detach_desktop(self) -> None:
        if self._desktop_route is None or self._desktop_transfer is not None:
            return
        self._start_desktop_detach()

    def _start_desktop_detach(self) -> None:
        self._desktop_reverse_pending = False
        route = self._desktop_route
        start = route.pose()
        area = route.track.area
        center = QPointF(start.center)
        allowed = area.adjusted(self.width() / 2, self.height() / 2,
                                -self.width() / 2, -self.height() / 2)
        center.setX(max(allowed.left(), min(center.x(), allowed.right())))
        center.setY(max(allowed.top(), min(center.y(), allowed.bottom())))
        angle = round(start.angle / 360) * 360
        end = DesktopPose(center, angle, start.facing, start.edge)
        self._desktop_transfer = _EdgeTransfer(start, end, attaching=False)

    def _discard_desktop(self, screen: QScreen | None = None, *, facing: int | None = None,
                         grabbed: bool = False) -> None:
        self._desktop_route = None
        self._desktop_transfer = None
        self._desktop_screen = None
        self._desktop_geometry = None
        self._desktop_reverse_pending = False
        self._puppet.set_desktop_contact(None)
        if screen is not None:
            previous = self.pos()
            self._place(previous, screen)
            if grabbed:
                offset = QPointF(previous - self.pos()) / self.transform().m11()
                self._puppet.level_after_release(offset)
        if facing is None:
            facing = 1 if self._velocity > 0 else -1
        self._velocity = copysign(abs(self._velocity), facing)
        self._puppet.stand(immediate=True)
        self._puppet.walk(0, facing)

    def _paint_desktop_pose(self, pose: DesktopPose, distance: float, strength: float,
                            elapsed: float) -> None:
        # The window has transparent padding. Only the artwork approaches the wall.
        position = (pose.center - QPointF(self.width() / 2, self.height() / 2)).toPoint()
        if position != self.pos():
            self.move(position)
        self._x, self._y = float(position.x()), float(position.y())
        scale = self.transform().m11()
        area = self._desktop_route.track.area
        center = self._center()
        self._puppet.set_desktop_contact(SurfaceContact.from_area(area, center, scale, strength))
        self._puppet.walk(distance / scale, pose.facing, pose.angle, elapsed=elapsed)

    def _step_desktop(self, screen: QScreen, distance: float, elapsed: float) -> None:
        # Geometry/DPI changes invalidate via _keep_visible; only check screen identity here.
        if screen is not self._desktop_screen:
            self._discard_desktop(screen)
            return
        transfer = self._desktop_transfer
        route = self._desktop_route
        if transfer is None:
            route.advance(distance)
            self._paint_desktop_pose(route.pose(), distance, 1.0, elapsed)
            if route.finished:
                self._start_desktop_detach()
            return
        transfer.time += elapsed
        progress = smooth(transfer.time / ATTACH_TIME)
        start, end = transfer.start, transfer.end
        # On release, gain clearance before turning the tail toward the wall.
        angle_progress = progress if transfer.attaching else smooth((progress - 0.12) / 0.88)
        position_progress = progress if transfer.attaching else smooth(progress * 1.60)
        angle = start.angle + (end.angle - start.angle) * angle_progress
        center = start.center + (end.center - start.center) * position_progress
        strength = progress if transfer.attaching else 1 - progress
        pose = DesktopPose(center, angle, end.facing, end.edge)
        self._paint_desktop_pose(pose, distance * (0.6 + 0.4 * progress), strength, elapsed)
        if progress == 1:
            self._desktop_transfer = None
            if not transfer.attaching:
                # Leave the boundary facing into the screen, regardless of its side.
                facing = 1 if end.center.x() < route.track.area.center().x() else -1
                self._discard_desktop(screen, facing=facing)

    def _sync_timers(self) -> None:
        if self._throw is not None:
            self._behavior_timer.stop()
            if self.isVisible() and not self._menu_open:
                if not self._timer.isActive():
                    self._last_tick = perf_counter()
                    self._timer.start()
            else:
                self._timer.stop()
            return
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
        self._braking = (active and not walking and self._desktop_transfer is None
                         and self._timer.isActive() and self._speed_scale > 0)
        if walking or self._braking:
            if not self._timer.isActive():
                self._last_tick = perf_counter()
                self._timer.start()
        else:
            self._timer.stop()
            self._speed_scale = 0.0
            self._puppet.stand(immediate=self._press is not None or not self.isVisible())
        if walking or not active:
            self._puppet.settle_idle()

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
            elif self._route is not None:
                self._route.reverse()
            elif self._desktop_route is None:
                self._velocity = -self._velocity

        gaze = (0, 0)
        if self._behavior.activity is Activity.OBSERVING and distance is not None:
            scale = 3 / max(distance, 20)
            gaze = (round(offset.x() * scale), round(offset.y() * scale))
        self._show_activity(gaze)
        self._sync_timers()
        if self._behavior.idle_shift_ready(elapsed, stationary=not self._timer.isActive()):
            self._puppet.idle_shift()

    def _step(self) -> None:
        now = perf_counter()
        elapsed = now - self._last_tick
        self._last_tick = now
        if self._throw is not None:
            self._step_throw(elapsed)
            return
        # Discard long pauses caused by a suspended or busy desktop.
        elapsed = min(elapsed, 0.05)
        screen = self._current_screen()
        if screen is None:
            self._sync_timers()
            return
        climbing = self._route is not None and self._route.edge in (Edge.SIDE, Edge.CORNER)
        desktop = self._desktop_route is not None
        if self._braking and not self._speed_scale:
            self._sync_timers()
            return
        if desktop and self._desktop_reverse_pending and self._speed_scale <= 1e-6:
            self._desktop_reverse_pending = False
            self._desktop_route.direction *= -1
            pose = self._desktop_route.pose()
            self._puppet.walk(0, pose.facing, pose.angle)
        idle = self._braking or self._desktop_reverse_pending
        target_scale = 0.0 if idle else (0.72 if climbing or desktop else 1.0)
        if desktop and not idle and self._desktop_transfer is None:
            route = self._desktop_route
            remaining = route.track.length - route.distance if route.direction > 0 else route.distance
            target_scale = 0.34 + 0.38 * smooth(remaining / (28 * self.transform().m11()))
        if not desktop:
            self._desktop_cooldown = max(0.0, self._desktop_cooldown - elapsed)
        # Automatic stops coast only a few logical pixels. Input still stops immediately.
        duration = min(0.115, 13 / max(1, abs(self._velocity))) if self._braking else 0.18
        self._speed_scale, moving_time = ramp_speed(self._speed_scale, target_scale, elapsed, duration)
        distance = abs(self._velocity) * moving_time
        if self._preferences.birdseye:
            self._step_overhead(screen, moving_time, elapsed)
            return
        if self._route is not None:
            self._route.advance(distance)
            self._place_on_window(screen, distance, elapsed)
            return
        if desktop:
            self._step_desktop(screen, distance, elapsed)
            return
        if distance and not self._braking and self._try_window(distance):
            return

        area = screen.availableGeometry()
        right = area.x() + max(0, area.width() - self.width())
        if distance and not self._braking and not self._desktop_cooldown:
            side = 1 if self._velocity > 0 else -1
            wall = right if side > 0 else area.x()
            if 0 <= (wall - self._x) * side <= max(distance, 8):
                track = self._desktop_track(screen, side)
                if track is not None:
                    self._attach_desktop(track, screen)
                    return
        self._x, self._velocity = advance(
            self._x, self._velocity, moving_time, area.x(), right
        )
        if right > area.x():
            direction = 1 if self._velocity > 0 else -1
            self._puppet.walk(distance / self.transform().m11(), direction, elapsed=elapsed)
        else:
            self._puppet.stand()
        x = round(self._x)
        y = clamp_origin(self.y(), area.y(), area.height(), self.height())
        if self._y > y:
            # A throw can settle with the toes at the work-area boundary
            # while the transparent bottom of the overlay extends past it.
            y = clamp_origin(self.y(), area.y(), area.height(), self.height() - self._floor_extension())
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
            delta = angle_delta(self._puppet.angle, degrees(self._heading))
            limit = elapsed * 420
            turn = delta * min(1.0, 9 * elapsed)
            angle = self._puppet.angle + min(limit, max(-limit, turn))
            self._puppet.walk(distance / self.transform().m11(), 1, angle, elapsed=elapsed)
        else:
            self._puppet.stand()

    def _update_appearance(self) -> None:
        self._puppet.set_appearance(self._hovered)

    def _end_press(self) -> None:
        self._cursor_history.clear()
        self._capture_lost.stop()
        self._drag_timer.stop()
        self._drag_cursor = None
        self._press = None
        self._dragging = False
        self._drag_floor_extension = 0
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
            self._cancel_throw()
            self._press = event.globalPosition().toPoint()
            self._cursor_history.clear()
            self._sample_cursor(event)
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

        self._sample_cursor(event)
        cursor = event.globalPosition().toPoint()
        distance = (cursor - self._press).manhattanLength()
        if not self._dragging and distance >= QApplication.startDragDistance():
            self._dragging = True
            self._leave_window()
            if self._desktop_route is not None:
                self._discard_desktop(self._current_screen(), grabbed=True)
            screen = self._current_screen()
            if screen is not None:
                area = screen.availableGeometry()
                if self.y() > area.y() + area.height() - self.height():
                    self._drag_floor_extension = self._floor_extension()
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
                self._sample_cursor(event)
                velocity = (self._cursor_history.release() if self._preferences.throwing
                            and self._behavior.activity is not Activity.SLEEPING else None)
                if velocity is None or not self._start_throw(*velocity):
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

    def _sample_cursor(self, event) -> None:
        if self._preferences.throwing:
            point = event.globalPosition()
            # Qt timestamps preserve the spacing of native events queued
            # during a busy frame. Synthetic events may have no timestamp.
            timestamp = event.timestamp()
            self._cursor_history.add(timestamp / 1000 if timestamp else perf_counter(), point.x(), point.y())

    def _landing_clearance(self) -> float:
        if self._preferences.birdseye:
            return self.height() / 2
        return self._puppet.SIDE_LANDING_CLEARANCE * self.transform().m11()

    def _floor_extension(self) -> int:
        return round(self.height() / 2 - self._landing_clearance())

    def _throw_bounds(self, screen: QScreen) -> ThrowBounds | None:
        area = QRectF(screen.availableGeometry())
        half_width = self.width() / 2
        half_height = self.height() / 2
        if area.width() < self.width() or area.height() < self.height():
            return None
        # Keep the envelope swept by the six legs and tail inside the
        # work area. Only transparent overlay padding can cross a boundary.
        margin = min(half_width, 82 * self.transform().m11())
        return ThrowBounds(area.left() + margin, area.top() + half_height,
                           area.right() - margin, area.bottom() - half_height + self._floor_extension(),
                           area.left() + half_width, area.right() - half_width)

    def _start_throw(self, vx: float, vy: float) -> bool:
        screen = self._current_screen()
        bounds = self._throw_bounds(screen) if screen is not None else None
        if (bounds is None or self.fullscreen_suppressed or not self.isVisible()
                or self._route is not None or self._desktop_route is not None):
            return False
        scale = self.transform().m11()
        pivot = QPointF(self.pos()) + self._puppet.pos() * scale
        angle, tuck, kick = self._puppet.begin_throw_pose()
        self._throw = ThrowMotion(pivot.x(), pivot.y(), vx, vy, bounds, angle, tuck, kick)
        self._throw.contain()
        self._move_throw()
        return True

    def _move_throw(self) -> None:
        flight = self._throw
        self._x = flight.x - self.width() / 2
        self._y = flight.y - self.height() / 2
        position = round(self._x), round(self._y)
        if position != (self.x(), self.y()):
            self.move(*position)

    def _step_throw(self, elapsed: float) -> None:
        flight = self._throw
        finished = flight.advance(elapsed)
        self._move_throw()
        clearance = max(0.0, (flight.bounds.floor - flight.y) / self.transform().m11())
        settle = smooth(flight.age / 0.16)
        ready_to_land = smooth(clearance / 75)
        lean = 13 * flight.vx / MAX_RELEASE_SPEED + 8 * flight.vy / MAX_RELEASE_SPEED
        base_angle = flight.initial_angle if self._preferences.birdseye else 0.0
        angle = base_angle + ((flight.initial_angle - base_angle) * (1 - settle) + lean * settle) * ready_to_land
        tuck = (flight.initial_tuck * (1 - settle) + 0.68 * settle) * ready_to_land
        impact = flight.impact_age
        # Compression peaks first; the last tail segments catch up later.
        compression = 0.0
        if flight.impact and impact < 0.19:
            compression = (2.0 + 6.0 * flight.impact) * sin(pi * impact / 0.19)
        tail = flight.impact * 0.075 * sin(2 * pi * smooth((impact - 0.045) / 0.30))
        self._puppet.set_throw_pose(angle, tuck, compression, tail,
                                    foot_lift=(5 - 19 * settle) * tuck,
                                    leg_kick=flight.initial_kick * (1 - settle) * ready_to_land)
        if finished:
            self._cancel_throw()
            if self._behavior.activity is not Activity.SLEEPING:
                self._behavior.wake()
                self._show_activity()
            self._desktop_cooldown = max(self._desktop_cooldown, 4.0)
            self._sync_timers()

    def _cancel_throw(self) -> None:
        if self._throw is not None:
            self._throw = None
            self._puppet.end_throw_pose()

    def _drag_step(self, *, drop: bool = False) -> None:
        cursor = self._drag_cursor
        screen = (QGuiApplication.screenAt(cursor) or self._current_screen()) if cursor is not None else None
        if screen is None:
            self._drag_timer.stop()
            return
        area = screen.availableGeometry()
        origin = cursor - self._drag_offset
        target = QPointF(clamp_origin(origin.x(), area.x(), area.width(), self.width()),
                         clamp_origin(origin.y(), area.y(), area.height(),
                                      self.height() - self._drag_floor_extension))
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
        self._place(rounded, screen, floor_extension=self._drag_floor_extension)
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
        self._cancel_throw()
        if self._behavior.activity.resting:
            self._behavior.wake()
        else:
            if self._desktop_transfer is not None:
                self._discard_desktop(self._current_screen())
            self._behavior.sleep()
        self._show_activity()
        self._sync_timers()

    def _open_settings(self) -> None:
        if self._settings_dialog is not None or self.fullscreen_suppressed:
            return
        self._cancel_throw()
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
            if self._desktop_route is not None and (
                self._preferences.birdseye != dialog.preferences.birdseye
                or self._preferences.size != dialog.preferences.size
            ):
                self._discard_desktop(self._current_screen())
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
