from __future__ import annotations

import atexit
import hashlib
import logging
import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:   %(funcName)16s:  %(message)s",
)
logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key           TEXT PRIMARY KEY,
    file_path     TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    access_count  INTEGER DEFAULT 1,
    last_accessed REAL NOT NULL
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache(last_accessed);
"""


class ImageCache:
    """Process- and thread-safe LRU image cache backed by SQLite.

    Stores image files on disk and tracks metadata in a SQLite database.
    Eviction is based on least-recently-used (LRU) access time. WAL journal
    mode and busy_timeout allow multiple processes to share the same cache
    directory safely.

    Environment variables:
        AYON_IMG_CACHE_DIR: Parent directory for the AYON_IMG_CACHE folder.
                            Defaults to the system temp directory.
        AYON_IMG_CACHE_SIZE: Override default cache size in MB.
        AYON_IMG_CACHE_CLEAR_ON_STARTUP: Clear all cache files on startup.

    Attributes:
        cache_path (Path): Directory where cached files are stored.
        max_size_in_MB (int): Maximum cache size in megabytes.
        max_size_bytes (int): Maximum cache size in bytes.
    """

    _instance: ImageCache | None = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        cache_path: str | Path | None = None,
        max_size_in_MB: int = 500,
    ) -> ImageCache:
        """Return the singleton cache instance, creating it if needed.

        Args:
            cache_path: Directory path for storing cached files.
            max_size_in_MB: Maximum cache size in megabytes.

        Returns:
            The singleton ImageCache instance.

        Raises:
            ValueError: If max_size_in_MB is not positive.
        """
        if max_size_in_MB <= 0:
            raise ValueError("max_size_in_MB must be positive")

        with cls._lock:
            if cls._instance is None:
                instance = object.__new__(cls)
                instance._initialize(cache_path, max_size_in_MB)
                cls._instance = instance
            return cls._instance

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _get_tmp_dir(self) -> Path:
        tmp = Path(os.environ.get("AYON_IMG_CACHE_DIR", tempfile.gettempdir()))
        tmp = tmp / "AYON_IMG_CACHE"
        tmp.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            os.chmod(tmp, 0o700)
        logger.info(f"AYON image cache: {tmp} ({self.max_size_in_MB} MB)")
        return tmp

    def _initialize(
        self,
        cache_path: str | Path | None,
        max_size_in_MB: int,
    ) -> None:
        """Initialise the cache instance.

        Args:
            cache_path: Directory path for storing cached files.
            max_size_in_MB: Maximum cache size in megabytes.
        """
        raw_size_env = os.environ.get("AYON_IMG_CACHE_SIZE")
        if raw_size_env is not None:
            try:
                parsed_size = int(raw_size_env)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Environment variable AYON_IMG_CACHE_SIZE must be an integer "
                    f"number of megabytes, got {raw_size_env!r}"
                ) from exc
            if parsed_size <= 0:
                raise ValueError(
                    f"Environment variable AYON_IMG_CACHE_SIZE must be a positive "
                    f"integer number of megabytes, got {raw_size_env!r}"
                )
            self.max_size_in_MB = parsed_size
        else:
            try:
                parsed_size = int(max_size_in_MB)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"max_size_in_MB must be an integer number of megabytes, "
                    f"got {max_size_in_MB!r}"
                ) from exc
            if parsed_size <= 0:
                raise ValueError(
                    f"max_size_in_MB must be a positive integer number of "
                    f"megabytes, got {max_size_in_MB!r}"
                )
            self.max_size_in_MB = parsed_size
        self.max_size_bytes = self.max_size_in_MB * 1024 * 1024

        self.cache_path = (
            Path(cache_path) if cache_path else self._get_tmp_dir()
        )
        self.cache_path.mkdir(parents=True, exist_ok=True)

        self._db_path = self.cache_path / "cache_metadata.db"
        self._db = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._db.execute("PRAGMA busy_timeout=10000")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(_CREATE_TABLE_SQL)
        self._db.execute(_CREATE_INDEX_SQL)
        self._db.commit()

        self._access_lock = threading.Lock()

        if "AYON_IMG_CACHE_CLEAR_ON_STARTUP" in os.environ:
            self._clear_all_files()

        self._validate_cache_files()
        self._cleanup_legacy_files()

        atexit.register(self._db.close)

    def _clear_all_files(self) -> None:
        """Delete every file in the cache directory and reset the DB."""
        count = 0
        for entry in os.scandir(self.cache_path):
            if entry.is_file() and entry.name != self._db_path.name:
                try:
                    os.remove(entry.path)
                    count += 1
                except OSError as exc:
                    logger.warning(f"Could not remove {entry.path}: {exc}")
        self._db.execute("DELETE FROM cache")
        self._db.commit()
        logger.info(f"AYON image cache: cleared ({count} files removed)")

    def _cleanup_legacy_files(self) -> None:
        """Remove legacy JSON metadata files left from the previous version."""
        for name in ("cache_metadata.json", "cache_metadata.json.lock"):
            legacy = self.cache_path / name
            if legacy.exists():
                try:
                    legacy.unlink()
                    logger.debug(f"Removed legacy cache file: {legacy}")
                except OSError as exc:
                    logger.warning(
                        f"Could not remove legacy file {legacy}: {exc}"
                    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, file_closure: Callable) -> str:
        """Return the cached file path for *key*, caching it if necessary.

        If *key* is not in the cache (or its file was deleted), *file_closure*
        is called to obtain the source file, which is then copied atomically
        into the cache directory.

        Args:
            key: Unique identifier for the cached file.
            file_closure: Callable returning the path to the source file.
                          Called only on a cache miss.

        Returns:
            Absolute path to the cached file as a string.

        Raises:
            ValueError: If *key* is empty or *file_closure* returns a path
                        that does not exist.
            IOError: If the file cannot be copied into the cache.
        """
        if not key:
            raise ValueError("Cache key cannot be empty")

        with self._access_lock:
            row = self._db.execute(
                "SELECT file_path FROM cache WHERE key = ?", (key,)
            ).fetchone()

            if row is not None:
                cached_path = Path(row[0])
                if cached_path.exists():
                    self._db.execute(
                        "UPDATE cache "
                        "SET access_count = access_count + 1,"
                        "    last_accessed = ? "
                        "WHERE key = ?",
                        (time.time(), key),
                    )
                    self._db.commit()
                    logger.debug(f"Cache hit for key '{key}'")
                    return str(cached_path)

                # File gone — purge the stale row
                logger.debug(
                    f"Cached file missing for key '{key}': {cached_path}"
                )
                self._db.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._db.commit()

            # Cache miss — call the closure inside the lock to prevent
            # duplicate work from concurrent threads.
            logger.debug(f"Cache miss for key '{key}', calling file_closure")
            source_path = Path(file_closure())

            if not source_path.exists():
                raise ValueError(
                    f"Loader returned non-existent file: {source_path}"
                )

            cache_filename = self._generate_cache_filename(key, source_path)
            cached_path = self.cache_path / cache_filename

            self._atomic_copy(source_path, cached_path)

            file_size = cached_path.stat().st_size
            self._db.execute(
                "INSERT OR REPLACE INTO cache "
                "(key, file_path, size_bytes, access_count, last_accessed) "
                "VALUES (?, ?, ?, 1, ?)",
                (key, str(cached_path), file_size, time.time()),
            )
            self._db.commit()

            self._evict_if_needed()

            logger.debug(f"Cached file for key '{key}': {cached_path}")
            return str(cached_path)

    def has(self, key: str) -> bool:
        """Return True if *key* is cached and its file exists on disk.

        Args:
            key: Cache key to check.

        Returns:
            True if the key is present and the file exists, else False.
        """
        with self._access_lock:
            row = self._db.execute(
                "SELECT file_path FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return False
            return Path(row[0]).exists()

    def get_path(self, key: str) -> str | None:
        """Return the cached file path for *key* if it exists, else None.

        Updates access metadata when the entry is found.

        Args:
            key: Cache key to look up.

        Returns:
            Absolute path string to the cached file, or None.
        """
        with self._access_lock:
            row = self._db.execute(
                "SELECT file_path FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            cached_path = Path(row[0])
            if not cached_path.exists():
                return None
            self._db.execute(
                "UPDATE cache "
                "SET access_count = access_count + 1,"
                "    last_accessed = ? "
                "WHERE key = ?",
                (time.time(), key),
            )
            self._db.commit()
            return str(cached_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _atomic_copy(self, src: Path, dst: Path) -> None:
        """Copy *src* to *dst* atomically using a temp file + os.replace().

        The temporary file is created in the same directory as *dst* so that
        ``os.replace`` is an atomic rename on the same filesystem.

        Args:
            src: Source file path.
            dst: Destination file path.

        Raises:
            IOError: If the copy or rename fails.
        """
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.cache_path,
                delete=False,
            ) as tmp_fh:
                tmp_path = tmp_fh.name
                with open(src, "rb") as src_fh:
                    tmp_fh.write(src_fh.read())
            os.replace(tmp_path, dst)
        except IOError as exc:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise IOError(f"Failed to cache file: {exc}") from exc

    def _generate_cache_filename(self, key: str, source_path: Path) -> str:
        """Build a cache filename from a SHA-256 hash of *key*.

        Args:
            key: The cache key.
            source_path: The original file (used only to preserve extension).

        Returns:
            Filename string with the original extension.
        """
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        extension = source_path.suffix
        return f"{key_hash}{extension}"

    def _evict_if_needed(self) -> None:
        """Evict LRU entries until cache size is at 90 % of the limit."""
        current_size = self._get_cache_size()

        if current_size <= self.max_size_bytes:
            return

        target_size = int(self.max_size_bytes * 0.9)
        logger.info(
            f"Cache size ({current_size} bytes) exceeds limit "
            f"({self.max_size_bytes} bytes). Evicting to {target_size} bytes"
        )

        rows = self._db.execute(
            "SELECT key, file_path, size_bytes FROM cache ORDER BY last_accessed ASC"
        ).fetchall()

        keys_to_delete: list[str] = []
        for key, file_path_str, size_bytes in rows:
            if current_size <= target_size:
                break
            file_path = Path(file_path_str)
            try:
                if file_path.exists():
                    file_path.unlink()
                current_size -= size_bytes
                keys_to_delete.append(key)
                logger.debug(f"Evicted cache entry for key '{key}'")
            except OSError as exc:
                logger.warning(f"Failed to delete cache file: {exc}")

        if keys_to_delete:
            placeholders = ",".join("?" * len(keys_to_delete))
            self._db.execute(
                f"DELETE FROM cache WHERE key IN ({placeholders})",
                keys_to_delete,
            )
            self._db.commit()

    def _get_cache_size(self) -> int:
        """Return the total size of all cached entries in bytes.

        Returns:
            Total bytes recorded in the database.
        """
        row = self._db.execute(
            "SELECT COALESCE(SUM(size_bytes), 0) FROM cache"
        ).fetchone()
        return int(row[0])

    def _validate_cache_files(self) -> None:
        """Remove DB entries whose files no longer exist on disk."""
        rows = self._db.execute("SELECT key, file_path FROM cache").fetchall()

        invalid_keys = [key for key, fp in rows if not Path(fp).exists()]

        if not invalid_keys:
            return

        placeholders = ",".join("?" * len(invalid_keys))
        self._db.execute(
            f"DELETE FROM cache WHERE key IN ({placeholders})",
            invalid_keys,
        )
        self._db.commit()
        logger.debug(f"Removed {len(invalid_keys)} invalid cache entries")
