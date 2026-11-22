"""Per-user preferences and their settings dialog."""

from dataclasses import dataclass

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QSlider,
    QVBoxLayout,
)

from .appearance import DEFAULT_FINISH, FINISHES
from .character import MechanicalPuppet


@dataclass(frozen=True)
class Preferences:
    finish: str = DEFAULT_FINISH
    effects: bool = True
    sound: bool = False
    birdseye: bool = False
    size: int = 100
    curled_sleep: bool = False

    @classmethod
    def load(cls, store: QSettings) -> "Preferences":
        finish = store.value("appearance/finish", DEFAULT_FINISH, type=str)
        return cls(
            finish if finish in FINISHES else DEFAULT_FINISH,
            store.value("feedback/effects", True, type=bool),
            store.value("feedback/sound", False, type=bool),
            store.value("appearance/birdseye", False, type=bool),
            min(150, max(70, store.value("appearance/size", 100, type=int))),
            store.value("appearance/curled_sleep", False, type=bool),
        )

    def save(self, store: QSettings) -> bool:
        store.setValue("appearance/finish", self.finish)
        store.setValue("feedback/effects", self.effects)
        store.setValue("feedback/sound", self.sound)
        store.setValue("appearance/birdseye", self.birdseye)
        store.setValue("appearance/size", self.size)
        store.setValue("appearance/curled_sleep", self.curled_sleep)
        store.sync()
        return store.status() == QSettings.Status.NoError


class SettingsDialog(QDialog):
    def __init__(self, preferences: Preferences, store: QSettings, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Arachnid Settings")
        self.setMinimumWidth(380)
        self._store = store
        self.preferences = preferences
        self.setStyleSheet("""
            QDialog { background: #17212b; }
            QLabel, QCheckBox { color: #edf3f7; }
            QComboBox, QPushButton {
                color: #edf3f7; background: #263849; border: 1px solid #465c70;
                border-radius: 5px; padding: 6px 12px;
            }
            QComboBox:hover, QPushButton:hover { background: #32495d; }
            QComboBox:focus, QPushButton:focus { border: 1px solid #8ce3d5; }
            QComboBox QAbstractItemView {
                color: #edf3f7; background: #263849; selection-background-color: #3c566c;
            }
            QPushButton:default { color: #11262b; background: #9af0dd; border-color: #9af0dd; }
            QPushButton:default:hover { background: #c7f9ed; }
            QLabel#settingsError { color: #ffbb9b; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        preview = QGraphicsView(self)
        preview.setFixedHeight(152)
        preview.setFrameShape(QFrame.Shape.NoFrame)
        preview.setBackgroundBrush(QBrush(QColor("#202e3b")))
        preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        preview.setRenderHint(QPainter.RenderHint.Antialiasing)
        preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        scene = QGraphicsScene(0, 0, MechanicalPuppet.WIDTH, MechanicalPuppet.HEIGHT, preview)
        preview.setScene(scene)
        puppet = MechanicalPuppet(preferences.finish)
        puppet.set_birdseye(preferences.birdseye)
        scene.addItem(puppet)
        layout.addWidget(preview)

        self._finish = QComboBox(self)
        for key, palette in FINISHES.items():
            self._finish.addItem(palette.label, key)
        self._finish.setCurrentIndex(self._finish.findData(preferences.finish))
        self._finish.currentIndexChanged.connect(lambda _: puppet.set_finish(self._finish.currentData()))
        form = QFormLayout()
        label = QLabel("&Finish", self)
        label.setBuddy(self._finish)
        form.addRow(label, self._finish)
        self._size = QSlider(Qt.Orientation.Horizontal, self)
        self._size.setRange(70, 150)
        self._size.setValue(preferences.size)
        size_label = QLabel("&Size", self)
        size_label.setBuddy(self._size)
        size_value = QLabel(self)
        form.addRow(size_label, self._size)
        form.addRow("", size_value)

        def preview_size(value: int) -> None:
            preview.resetTransform()
            preview.scale(value / 125, value / 125)
            preview.centerOn(puppet)
            size_value.setText(f"{value}%")

        self._size.valueChanged.connect(preview_size)
        preview_size(preferences.size)
        layout.addLayout(form)

        self._effects = QCheckBox("Click &light pulse", self)
        self._effects.setChecked(preferences.effects)
        self._sound = QCheckBox("Click &sound", self)
        self._sound.setChecked(preferences.sound)
        layout.addWidget(self._effects)
        layout.addWidget(self._sound)
        self._birdseye = QCheckBox("&Bird’s-eye view", self)
        self._birdseye.setToolTip("Roam in every direction across the current screen’s work area.")
        self._birdseye.setChecked(preferences.birdseye)
        self._birdseye.toggled.connect(puppet.set_birdseye)
        layout.addWidget(self._birdseye)

        self._curled_sleep = QCheckBox("&Curl up while sleeping", self)
        self._curled_sleep.setChecked(preferences.curled_sleep)
        layout.addWidget(self._curled_sleep)

        self._error = QLabel(self)
        self._error.setObjectName("settingsError")
        self._error.setWordWrap(True)
        self._error.hide()
        layout.addWidget(self._error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        preferences = Preferences(
            self._finish.currentData(), self._effects.isChecked(), self._sound.isChecked(),
            self._birdseye.isChecked(),
            self._size.value(),
            self._curled_sleep.isChecked(),
        )
        if not preferences.save(self._store):
            self._error.setText("Windows could not save your Arachnid preferences.")
            self._error.show()
            return
        self.preferences = preferences
        super().accept()
