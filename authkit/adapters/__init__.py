"""Official AuthKit storage adapters.

SQLAlchemy is an optional extra and must be imported from
``authkit.adapters.sqlalchemy`` so the core package stays ORM-free.
"""

from authkit.adapters.memory import MemoryBackend

__all__ = ["MemoryBackend"]
