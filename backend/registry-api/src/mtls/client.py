"""mTLS client utilities for Python services.

Reference: FR-010 (mTLS enforcement), research.md (certificate reload)
"""
import ssl
import time
from pathlib import Path
from threading import Lock, Thread
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class TLSConfig:
    """mTLS configuration."""

    def __init__(
        self,
        cert_file: str,
        key_file: str,
        ca_file: str,
        enable_auto_reload: bool = True,
        reload_interval: int = 300,  # 5 minutes
    ):
        """Initialize TLS configuration.

        Args:
            cert_file: Path to client certificate
            key_file: Path to client private key
            ca_file: Path to CA certificate
            enable_auto_reload: Enable automatic certificate reloading
            reload_interval: Reload check interval in seconds
        """
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.enable_auto_reload = enable_auto_reload
        self.reload_interval = reload_interval


class MTLSClient:
    """mTLS client with automatic certificate reloading."""

    def __init__(self, config: TLSConfig):
        """Initialize mTLS client.

        Args:
            config: TLS configuration
        """
        self.config = config
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._lock = Lock()
        self._observer: Optional[Observer] = None
        self._stop_flag = False

        # Load initial SSL context
        self._load_ssl_context()

        # Start auto-reload if enabled
        if config.enable_auto_reload:
            self._start_auto_reload()

    def get_ssl_context(self) -> ssl.SSLContext:
        """Get current SSL context (thread-safe).

        Returns:
            ssl.SSLContext: Current SSL context
        """
        with self._lock:
            return self._ssl_context

    def _load_ssl_context(self) -> None:
        """Load certificates and create SSL context."""
        try:
            # Create SSL context
            context = ssl.create_default_context(
                purpose=ssl.Purpose.SERVER_AUTH,
                cafile=self.config.ca_file,
            )

            # Load client certificate and key
            context.load_cert_chain(
                certfile=self.config.cert_file,
                keyfile=self.config.key_file,
            )

            # Enforce TLS 1.3
            context.minimum_version = ssl.TLSVersion.TLSv1_3

            # Require client certificates
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True

            # Update SSL context (thread-safe)
            with self._lock:
                self._ssl_context = context

            print("✓ SSL context loaded successfully")

        except Exception as e:
            print(f"✗ Failed to load SSL context: {e}")
            raise

    def _start_auto_reload(self) -> None:
        """Start watching certificate files for changes."""
        event_handler = CertificateFileHandler(self._on_certificate_changed)
        self._observer = Observer()

        # Watch certificate directory
        cert_dir = Path(self.config.cert_file).parent
        self._observer.schedule(event_handler, str(cert_dir), recursive=False)
        self._observer.start()

        # Start periodic reload thread
        reload_thread = Thread(target=self._periodic_reload, daemon=True)
        reload_thread.start()

        print(f"✓ Certificate auto-reload enabled (interval: {self.config.reload_interval}s)")

    def _on_certificate_changed(self, file_path: str) -> None:
        """Handle certificate file change event.

        Args:
            file_path: Path to changed file
        """
        # Check if the changed file is one of our certificate files
        if file_path in [self.config.cert_file, self.config.key_file, self.config.ca_file]:
            print(f"Certificate file changed: {file_path}, reloading...")
            try:
                self._load_ssl_context()
                print("✓ SSL context reloaded successfully")
            except Exception as e:
                print(f"✗ Failed to reload SSL context: {e}")

    def _periodic_reload(self) -> None:
        """Periodically reload certificates (backup mechanism)."""
        while not self._stop_flag:
            time.sleep(self.config.reload_interval)
            if not self._stop_flag:
                try:
                    self._load_ssl_context()
                except Exception as e:
                    print(f"✗ Periodic reload failed: {e}")

    def validate_certificate(self) -> None:
        """Validate certificate is not expired.

        Raises:
            ValueError: If certificate is invalid or expired
        """
        import OpenSSL.crypto as crypto

        with self._lock:
            # Load certificate
            with open(self.config.cert_file, "rb") as f:
                cert_data = f.read()

            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)

            # Check expiration
            not_after = cert.get_notAfter().decode("ascii")
            expiry = time.strptime(not_after, "%Y%m%d%H%M%SZ")
            expiry_timestamp = time.mktime(expiry)
            now = time.time()

            if now > expiry_timestamp:
                raise ValueError(f"Certificate expired on {time.ctime(expiry_timestamp)}")

            # Warn if expiring within 7 days
            seven_days = 7 * 24 * 60 * 60
            if (expiry_timestamp - now) < seven_days:
                days_left = int((expiry_timestamp - now) / (24 * 60 * 60))
                print(f"⚠️  WARNING: Certificate expires in {days_left} days! Please renew.")

    def close(self) -> None:
        """Stop auto-reload and cleanup resources."""
        self._stop_flag = True
        if self._observer:
            self._observer.stop()
            self._observer.join()


class CertificateFileHandler(FileSystemEventHandler):
    """File system event handler for certificate changes."""

    def __init__(self, callback):
        """Initialize handler.

        Args:
            callback: Function to call when certificate file changes
        """
        self.callback = callback

    def on_modified(self, event):
        """Handle file modification event."""
        if not event.is_directory:
            self.callback(event.src_path)

    def on_created(self, event):
        """Handle file creation event."""
        if not event.is_directory:
            self.callback(event.src_path)


# Convenience function for FastAPI/HTTPX
def create_httpx_client(config: TLSConfig):
    """Create HTTPX client with mTLS configuration.

    Args:
        config: TLS configuration

    Returns:
        httpx.AsyncClient: Configured HTTPX client
    """
    import httpx

    mtls_client = MTLSClient(config)
    ssl_context = mtls_client.get_ssl_context()

    return httpx.AsyncClient(verify=ssl_context)
