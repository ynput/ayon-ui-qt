from __future__ import annotations

import atexit
import hashlib
import json
import logging
import threading
import time
import tempfile
import os
from pathlib import Path
from typing import Callable

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:   %(funcName)16s:  %(message)s",
)
logger = logging.getLogger(__name__)


class ImageCache:
    """Thread-safe LRU cache singleton for storing and retrieving images.

    This cache manages image files on disk with automatic eviction based on
    size limits. It maintains metadata in JSON format and ensures thread-safe
    access through locking mechanisms.

    Attributes:
        cache_path (Path): Directory where cached files are stored.
        max_size_in_MB (int): Maximum cache size in megabytes.
    """

    _instance: ImageCache | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> ImageCache:
        """Prevent direct instantiation. Use get_instance() instead."""
        raise RuntimeError(
            "Use ImageCache.get_instance() to get the singleton instance"
        )

    @classmethod
    def get_instance(
        cls, cache_path: str | Path | None = None, max_size_in_MB: int = 50
    ) -> ImageCache:
        """Get or create the singleton cache instance.

        Args:
            cache_path: Directory path for storing cached files.
            max_size_in_MB: Maximum cache size in megabytes.

        Returns:
            ImageCache: The singleton cache instance.

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
                atexit.register(cls._instance._save_metadata)
            return cls._instance

    def _get_tmp_dir(self) -> Path:
        tmp = Path(tempfile.gettempdir())
        tmp = tmp / "AYON_IMG_CACHE"
        # make tmp writable and readable to the user only
        tmp.mkdir(parents=True, exist_ok=True)
        os.chmod(tmp, 0o700)
        logger.info(f"image cache: {tmp} ({self.max_size_in_MB} MB)")
        return tmp

    def _initialize(
        self, cache_path: str | Path | None, max_size_in_MB: int
    ) -> None:
        """Initialize the cache instance.

        Args:
            cache_path: Directory path for storing cached files.
            max_size_in_MB: Maximum cache size in megabytes.
        """
        self.max_size_in_MB = max_size_in_MB
        self.max_size_bytes = max_size_in_MB * 1024 * 1024
        self.cache_path = (
            Path(cache_path) if cache_path else self._get_tmp_dir()
        )
        self._metadata_file = self.cache_path / "cache_metadata.json"
        self._metadata: dict[str, dict] = {}
        self._access_lock = threading.Lock()

        # Create cache directory if it doesn't exist
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # Load existing metadata and validate files
        self._load_metadata()
        self._validate_cache_files()

    def _load_metadata(self) -> None:
        """Load cache metadata from JSON file.

        If the metadata file doesn't exist, initialize empty metadata.
        """
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r") as f:
                    self._metadata = json.load(f)
                logger.info(
                    f"Loaded cache metadata with {len(self._metadata)} entries"
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to load metadata: {e}. Starting fresh."
                )
                self._metadata = {}
        else:
            self._metadata = {}

    def _validate_cache_files(self) -> None:
        """Remove metadata entries for files that no longer exist.

        This ensures cache integrity on startup.
        """
        invalid_keys = []
        for key, entry in self._metadata.items():
            file_path = Path(entry.get("file_path", ""))
            if not file_path.exists():
                invalid_keys.append(key)
                logger.warning(
                    f"Cache file missing for key '{key}': {file_path}"
                )

        for key in invalid_keys:
            del self._metadata[key]

        if invalid_keys:
            logger.info(f"Removed {len(invalid_keys)} invalid cache entries")

    def get(self, key: str, file_closure: Callable) -> str:
        """Get a cached file or load it using the provided file_closure.

        Args:
            key: Unique identifier for the cached file.
            file_closure: Callable that returns the path to the file to cache.
                          Called only if the key is not in the cache.

        Returns:
            str: Path to the cached file.

        Raises:
            ValueError: If key is empty or file_closure returns invalid path.
            IOError: If file operations fail.
        """
        if not key:
            raise ValueError("Cache key cannot be empty")

        with self._access_lock:
            # Check if key exists in cache
            if key in self._metadata:
                entry = self._metadata[key]
                cached_path = Path(entry["file_path"])

                # Verify file still exists
                if cached_path.exists():
                    # Update access info
                    entry["access_count"] = entry.get("access_count", 0) + 1
                    entry["last_accessed"] = time.time()
                    logger.debug(f"Cache hit for key '{key}'")
                    return str(cached_path)
                else:
                    # File was deleted, remove from cache
                    logger.warning(
                        f"Cached file missing for key '{key}': {cached_path}"
                    )
                    del self._metadata[key]

            # Cache miss: call file_closure to get file
            logger.debug(f"Cache miss for key '{key}', calling file_closure")
            source_path = Path(file_closure())

            if not source_path.exists():
                raise ValueError(
                    f"Loader returned non-existent file: {source_path}"
                )

            # Generate cache filename from key hash
            cache_filename = self._generate_cache_filename(key, source_path)
            cached_path = self.cache_path / cache_filename

            # Move file to cache
            try:
                # Copy file to cache (preserves original)
                with open(source_path, "rb") as src:
                    with open(cached_path, "wb") as dst:
                        dst.write(src.read())
            except IOError as e:
                raise IOError(f"Failed to cache file: {e}") from e

            # Get file size
            file_size = cached_path.stat().st_size

            # Add entry to metadata
            self._metadata[key] = {
                "file_path": str(cached_path),
                "size_bytes": file_size,
                "access_count": 1,
                "last_accessed": time.time(),
            }

            # Check cache size and evict if necessary
            self._evict_if_needed()

            logger.info(f"Cached file for key '{key}': {cached_path}")
            return str(cached_path)

    def _generate_cache_filename(self, key: str, source_path: Path) -> str:
        """Generate a cache filename from the key hash.

        Args:
            key: The cache key.
            source_path: The original file path (to get extension).

        Returns:
            str: The cache filename with preserved extension.
        """
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        extension = source_path.suffix
        return f"{key_hash}{extension}"

    def _evict_if_needed(self) -> None:
        """Evict least recently used files if cache exceeds max size.

        Continues eviction until cache size is at 90% of max_size.
        """
        current_size = self._get_cache_size()

        if current_size > self.max_size_bytes:
            target_size = int(self.max_size_bytes * 0.9)
            logger.info(
                f"Cache size ({current_size} bytes) exceeds limit "
                f"({self.max_size_bytes} bytes). Evicting to {target_size} "
                "bytes"
            )

            # Sort by last_accessed (least recently used first)
            sorted_entries = sorted(
                self._metadata.items(),
                key=lambda x: x[1].get("last_accessed", 0),
            )

            for key, entry in sorted_entries:
                if current_size <= target_size:
                    break

                file_path = Path(entry["file_path"])
                file_size = entry.get("size_bytes", 0)

                try:
                    if file_path.exists():
                        file_path.unlink()
                        current_size -= file_size
                        logger.debug(f"Evicted cache entry for key '{key}'")
                except OSError as e:
                    logger.warning(f"Failed to delete cache file: {e}")

                del self._metadata[key]

    def _get_cache_size(self) -> int:
        """Calculate total cache size in bytes.

        Returns:
            int: Total size of all cached files in bytes.
        """
        total_size = 0
        for entry in self._metadata.values():
            file_path = Path(entry.get("file_path", ""))
            if file_path.exists():
                total_size += file_path.stat().st_size
            else:
                # Update metadata if file is missing
                total_size += entry.get("size_bytes", 0)
        return total_size

    def _save_metadata(self) -> None:
        """Save cache metadata to JSON file."""
        try:
            with open(self._metadata_file, "w") as fw:
                json.dump(self._metadata, fw, indent=4)
            logger.info("Cache metadata saved")
        except IOError as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def __del__(self) -> None:
        """Save metadata when cache is destroyed."""
        try:
            self._save_metadata()
        except Exception:
            pass
