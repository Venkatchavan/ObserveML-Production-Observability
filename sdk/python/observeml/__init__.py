"""ObserveML Python SDK — v0.1.0

Observer Principle: track() captures metadata ONLY.
No prompt or response content is ever transmitted.
"""
import sys
import types

from .tracker import ObserveML, configure, track, prompt_hash

__all__ = ["ObserveML", "configure", "track", "prompt_hash"]
__version__ = "0.1.0"


class _Module(types.ModuleType):
    """Module subclass that proxies _default to observeml.tracker._default.

    Tests access ``observeml._default`` (read) and set it to None (write).
    Both operations are forwarded to tracker._default so that the module-level
    configure() / track() remain consistent with the package attribute.
    """

    @property
    def _default(self):
        from observeml import tracker  # late import avoids circular
        return tracker._default

    @_default.setter
    def _default(self, value):
        from observeml import tracker
        tracker._default = value


# Replace this module in sys.modules with the custom subclass so that
# ``observeml._default`` behaves as a live, two-way proxy.
_mod = _Module(__name__)
_mod.__dict__.update(
    {k: v for k, v in globals().items() if k not in ("_Module", "_mod")}
)
sys.modules[__name__] = _mod
