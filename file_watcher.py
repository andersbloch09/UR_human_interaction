# file_watcher.py
import time
import paramiko
import hashlib
from typing import Optional, Tuple

class SSHFileWatcher:
    def __init__(self, hostname: str, username: str, password: Optional[str] = None,
                 port: int = 22, key_filename: Optional[str] = None):
        """
        Initialize SSH connection parameters.
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.ssh_client = None
        self.sftp_client = None
        self._connect()

    def _connect(self):
        """
        Establish SSH and SFTP connections.
        """
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
            key_filename=self.key_filename,
            look_for_keys=False,
            allow_agent=False
        )
        self.sftp_client = self.ssh_client.open_sftp()

    def close(self):
        """
        Close SSH and SFTP connections.
        """
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()

    def _get_file_hash(self, remote_path: str) -> str:
        """
        Compute a hash of the remote file content.
        """
        try:
            with self.sftp_client.open(remote_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except FileNotFoundError:
            return ""

    def _read_file(self, remote_path: str) -> str:
        """
        Read and return the content of the remote file.
        """
        with self.sftp_client.open(remote_path, 'r') as f:
            return f.read()

    def watch_file(self, remote_path: str, poll_interval: float = 1.0):
        """
        Generator that yields the file content whenever it changes.
        """
        last_hash = None
        while True:
            try:
                current_hash = self._get_file_hash(remote_path)
                if current_hash != last_hash:
                    last_hash = current_hash
                    content = self._read_file(remote_path)
                    yield remote_path, content
                time.sleep(poll_interval)
            except Exception as e:
                print(f"Error watching file: {e}")
                time.sleep(poll_interval)
