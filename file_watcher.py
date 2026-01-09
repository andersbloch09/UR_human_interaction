import time
import paramiko
import hashlib
from typing import Optional, Generator, Tuple


class SSHFileWatcher:
    def __init__(
        self,
        hostname: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
        poll_interval: float = 1.0,
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.poll_interval = poll_interval

        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None

        self._connect()

    # ------------------ CONNECTION ------------------

    def _connect(self):
        self.close()

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh_client.connect(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
            key_filename=self.key_filename,
            allow_agent=True,
            look_for_keys=True,
            timeout=10,
        )

        self.sftp_client = self.ssh_client.open_sftp()

    def close(self):
        try:
            if self.sftp_client:
                self.sftp_client.close()
        finally:
            self.sftp_client = None

        try:
            if self.ssh_client:
                self.ssh_client.close()
        finally:
            self.ssh_client = None

    # ------------------ FILE OPS ------------------

    def _file_hash(self, remote_path: str) -> Optional[str]:
        try:
            with self.sftp_client.open(remote_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except FileNotFoundError:
            return None

    def _read_file(self, remote_path: str) -> str:
        # Always return TEXT, never bytes
        with self.sftp_client.open(remote_path, "rb") as f:
            return f.read().decode("utf-8")

    # ------------------ WATCHER ------------------

    def watch_file(
        self, remote_path: str
    ) -> Generator[Tuple[str, str], None, None]:
        last_hash = None

        while True:
            try:
                current_hash = self._file_hash(remote_path)

                if current_hash and current_hash != last_hash:
                    last_hash = current_hash
                    content = self._read_file(remote_path)
                    yield remote_path, content

                time.sleep(self.poll_interval)

            except (paramiko.SSHException, OSError):
                print("SSH connection lost — reconnecting...")
                time.sleep(2)
                self._connect()

            except Exception as e:
                print(f"Watcher error: {e}")
                time.sleep(self.poll_interval)
