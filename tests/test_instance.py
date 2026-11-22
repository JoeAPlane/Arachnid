from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from arachnid.instance import Instance


def test_second_launch_notifies_owner_and_quit_releases_profile(tmp_path):
    app = QApplication.instance() or QApplication([])
    profile = str(tmp_path / "isolated.ini")
    owner = Instance(profile, app)
    other = Instance(profile, app)
    try:
        assert owner.start()
        notified = QSignalSpy(owner.reopen)
        assert not other.start()
        QCoreApplication.processEvents()
        assert notified.count() == 1
        owner.close()
        assert other.start()
    finally:
        owner.close()
        other.close()
