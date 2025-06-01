# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import abc
from collections.abc import Iterable
from typing import Any, Callable, Optional, cast

import aqt
from aqt import mw


def get_default_config() -> dict:
    assert mw
    default_config = mw.addonManager.addonConfigDefaults(mw.addonManager.addonFromModule(__name__))
    assert default_config
    return default_config


def get_config() -> dict:
    assert mw
    config = mw.addonManager.getConfig(__name__)
    assert config
    return config


def write_config(config: dict) -> None:
    assert mw
    return mw.addonManager.writeConfig(__name__, config)


def set_config_action(fn: Callable) -> None:
    assert mw
    return mw.addonManager.setConfigAction(__name__, fn)


def set_config_update_action(fn: Callable) -> None:
    assert mw
    return mw.addonManager.setConfigUpdatedAction(__name__, fn)


class MgrPropMixIn:
    @property
    def mgr(self) -> aqt.addons.AddonManager:
        """Anki's ConfigEditor requires this property."""
        assert mw
        return mw.addonManager


class AddonConfigABC(abc.ABC):
    @property
    @abc.abstractmethod
    def config(self) -> dict:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def default_config(self) -> dict:
        raise NotImplementedError()

    def __getitem__(self, key: str):
        if key in self.default_config:
            return self.config.get(key, self.default_config[key])
        else:
            raise KeyError(f"Key '{key}' is not defined in the default config.")

    def __setitem__(self, key, value) -> None:
        try:
            self[key]
        except KeyError:
            raise
        else:
            self.config[key] = value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterable[str]:
        return self.default_config.keys()

    def bool_keys(self) -> Iterable[str]:
        """Returns an iterable of boolean (toggleable) parameters in the config."""
        return (key for key, value in self.default_config.items() if isinstance(value, bool))

    def items(self) -> Iterable[tuple[str, Any]]:
        for key in self.keys():
            yield key, self[key]

    def toggleables(self) -> Iterable[tuple[str, bool]]:
        """Return all toggleable keys and values in the config."""
        for key in self.bool_keys():
            yield key, self[key]

    def update(self, another: dict[str, Any], clear_old: bool = False) -> None:
        self._raise_if_redundant_keys(another)
        if clear_old:
            self.config.clear()
        self.config.update(another)

    def _raise_if_redundant_keys(self, new_config: dict):
        if redundant_keys := [key for key in new_config if key not in self.default_config]:
            raise RuntimeError(
                "Passed a new config with keys that aren't present in the default config: %s."
                % ", ".join(redundant_keys)
            )


class AddonConfigManager(AddonConfigABC):
    """
    Dict-like proxy class for managing addon's config.
    Normally this class is initialized once and is used as a global variable.
    """

    _default_config: dict
    _config: dict

    def __init__(self, default: bool = False) -> None:
        self._set_underlying_dicts()
        if default:
            self._config = self._default_config

        assert isinstance(self.config, dict)
        assert isinstance(self.default_config, dict)

    def _set_underlying_dicts(self) -> None:
        self._default_config = get_default_config()
        self._config = get_config()

    @property
    def is_default(self) -> bool:
        return self.default_config is self.config

    @property
    def config(self) -> dict:
        return self._config

    @property
    def default_config(self) -> dict:
        return self._default_config

    def update_from_addon_manager(self, new_conf: dict) -> None:
        """
        This method may be passed to mw.addonManager.setConfigUpdatedAction
        to update our copy of the config dictionary after the user finishes editing it.
        """
        try:
            # Config has been already written to disk by aqt.addons.ConfigEditor
            self.update(new_conf, clear_old=True)
        except RuntimeError as ex:
            from aqt.utils import showCritical

            showCritical(str(ex), parent=mw, help=cast(str, None))
            # Restore previous config.
            self.write_config()

    def dict_copy(self) -> dict:
        """Get a deep copy of the config dictionary."""
        import copy

        if self.is_default:
            raise RuntimeError("Can't copy default config.")
        return copy.deepcopy(self.config)

    def write_config(self):
        if self.is_default:
            raise RuntimeError("Can't write default config.")
        return write_config(self.config)


class ConfigSubViewBase(AddonConfigABC):
    """
    Class for viewing into nested dictionaries.
    """

    _view_key: str
    _manager: AddonConfigABC

    def __init__(self, manager: AddonConfigABC, view_key: Optional[str] = None) -> None:
        self._view_key = view_key or self._view_key
        if not self._view_key:
            raise ValueError("view key must be set.")
        self._manager = manager
        assert isinstance(self.config, dict)
        assert isinstance(self.default_config, dict)

    @property
    def config(self) -> dict:
        return self._manager.config[self._view_key]

    @property
    def default_config(self) -> dict:
        return self._manager.default_config[self._view_key]

    def write_config(self) -> None:
        raise RuntimeError("Can't call this function from a sub-view.")
