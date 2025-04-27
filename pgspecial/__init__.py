import importlib.metadata

__version__ = importlib.metadata.version("pgspecial")
__all__ = []


def export(defn):
    """Decorator to explicitly mark functions that are exposed in a lib."""
    globals()[defn.__name__] = defn
    __all__.append(defn.__name__)
    return defn


from . import dbcommands, iocommands  # type: ignore[import]
