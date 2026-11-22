"""Route repeated launches to the Arachnid instance using the same settings."""

from hashlib import sha256
from pathlib import Path
from time import monotonic, sleep

from PySide6.QtCore import QLockFile, QObject, QStandardPaths, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class Instance(QObject):
    reopen = Signal()

    def __init__(self, profile: str, parent: QObject) -> None:
        super().__init__(parent)
        directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation))
        key = sha256(f"{directory}\n{profile}".casefold().encode()).hexdigest()[:24]
        self._name = f"arachnid-{key}"
        self._lock = QLockFile(str(directory / f"{self._name}.lock"))
        self._lock.setStaleLockTime(0)
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._accept_reopen)

    def start(self) -> bool:
        """Return True for a new instance and False if an existing one was notified."""
        deadline = monotonic() + 2
        while monotonic() < deadline:
            if self._lock.tryLock(0):
                if self._server.listen(self._name):
                    return True
                self._lock.unlock()
                raise RuntimeError(self._server.errorString())
            if self._lock.error() != QLockFile.LockError.LockFailedError:
                raise RuntimeError("Unable to lock the Arachnid settings profile.")
            client = QLocalSocket()
            client.connectToServer(self._name)
            if client.waitForConnected(100):
                client.disconnectFromServer()
                return False
            sleep(0.05)
        raise RuntimeError("The running Arachnid instance did not respond.")

    def _accept_reopen(self) -> None:
        while self._server.hasPendingConnections():
            client = self._server.nextPendingConnection()
            client.close()
            client.deleteLater()
        self.reopen.emit()

    def close(self) -> None:
        self._server.close()
        self._lock.unlock()
