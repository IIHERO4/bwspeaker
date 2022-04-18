#  Copyright (c) 2022 IIHERO4, TRAP, Seventy
#
import json
import logging
import os
from typing import Callable, Union, Dict

__all__ = [
    "PrefixedFilter",
    "RETURN_IM",
    "get_logger_prefixed",
    "LinkedJSON",
    "ConfigFile",
    "RelativePathAdapter",
    "MISSING",
]
MISSING = object()


def RETURN_IM(a):
    return a


class PrefixedFilter(logging.Filter):
    """Injects a prefix to the log message, ex: [prefix] [message]"""

    __slots__ = ("prefix",)

    def __init__(self, prefix):
        super().__init__("prefix-filter")
        self.prefix = prefix

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.prefix + " " + record.msg
        return True


def get_logger_prefixed(prefix: str, name: str, override: bool = False):
    """Returns a logger with :class:`.PrefixedFilter` added to it
    if override is True, any existing instance of :class:`.PrefixFilter` is removed
    and overriden by a new instance, else no change will happen if an existing instance is found
    """
    logger = logging.getLogger(name)
    removed = []

    for l_filter in logger.filters:
        if isinstance(l_filter, PrefixedFilter):
            if override:
                removed.append(l_filter)
            else:
                return logger

    for rfilter in removed:
        logger.removeFilter(rfilter)

    logger.addFilter(PrefixedFilter(prefix))

    return logger


class LinkedJSON(dict):
    """A Wrapper around dict that is linked to file.json

    Methods
    ----------

        save()
            Saves self to self.fp

        reload()
            Reloads self from self.fp

    """

    def __init__(self, fp, *args, default=None, **kwargs):
        self.fp = fp
        self.default = default

        super().__init__(*args, **kwargs, **self._load_file())

    def _load_file(self) -> dict:
        if self.default is not None and not os.path.exists(self.fp):
            logging.warning(f"{self.fp} not found, Filling Default Value")
            with open(self.fp, mode="x", encoding="utf-8") as json_file:
                json_file.write(
                    self.default
                    if isinstance(self.default, str)
                    else json.dumps(self.default)
                )

            return (
                self.default
                if isinstance(self.default, dict)
                else json.loads(self.default)
            )

        with open(self.fp, mode="r", encoding="utf-8") as json_file:
            return json.load(json_file)

    def save(self) -> None:
        with open(self.fp, mode="w", encoding="utf-8") as json_file:
            json.dump(self, json_file, indent=4)

    def reload(self) -> None:
        d = self._load_file()
        self.clear()
        self.update(**d)

    def copy(self) -> "LinkedJSON":
        return self.__class__(self.fp, default=self.default, **self)


"""
    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | str               |
    +---------------+-------------------+
    | number (int)  | int               |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+
"""
JSON_SERIALIZABLE = Union[dict, list, str, int, float, None, bool]


class ConfigFile(LinkedJSON):
    """A Wrapper around json

    access a config attribute by dotted syntax.
    if the config attribute it will return a specified default or None.
    Inspired by Spigot API

    .. Example:
        hydra.server is the same as config["hydra"]["server"]
        This function assumes hydra.server.meta is nested dicts,
        which will look something like this
            "hydra": {
                "server": {
                    "meta": Whatever JSON object this is,
                }
            }

    """

    def __init__(self, fp: str):
        super(ConfigFile, self).__init__(fp, default={})
        self._defaults: Dict[str, JSON_SERIALIZABLE] = {}

    def add_default(self, path: str, value: JSON_SERIALIZABLE, create: bool = False):
        """Adds a default value for the specified path

        Ex: hydra.server is the same as config["hydra"]["server"]
        This function assumes hydra.server.meta is nested dicts,
        which will look something like this
            "hydra": {
                "server": {
                    "meta": Whatever JSON object this is,
                }
            }

        :param value:
            the value to which is returned as a default
        :param path:
            path to the element in a nested structure.
        :param create:
            if set to `True`, the function will create missing parents from path
            Otherwise it will only store path to its default
        :return:
            value that's passed in Or actual value if found
        """
        if not create:
            self._defaults[path] = value
            return
        self.create_path(path, lambda: value)

    def get_key(self, path: str) -> JSON_SERIALIZABLE:
        """gets the value of specified path


        :param path:
            path of the element in dotted notation
        :return:
            JSON deserialized object
        :raises KeyError:
            if path or parent is not found
        """
        current_obj = self  # root
        for attr in path.split("."):
            current_obj = current_obj[attr]
        return current_obj

    def get_or_default(
        self, path: str, default: JSON_SERIALIZABLE = MISSING  # type: ignore
    ) -> JSON_SERIALIZABLE:  # type: ignore
        """Gets the value of the path or its default

        :param default:
            if passed in, the function will create the path and return default by calling :meth:`.add_default`
        :param path:
            path to the element in a nested structure
        :return:
            JSON deserialized object
            `MISSING` if default or value is not found
        """
        try:
            return self.get_key(path)
        except KeyError:
            if default is not MISSING:
                self.add_default(path, default, create=True)
                return default
            return self._defaults.get(path, MISSING)  # type: ignore

    def create_path(
        self, path: str, head_class: Union[Callable[..., object], type] = dict
    ):
        """Creates a nested structure to ensure path creation

        :param path:
            path to the element that :param head_class: will be located at
        :param head_class:
            the class which will be located at path
            or a callable returns a JSON serializable element
        :return:
            path that's passed into it
        :raises:
            TypeError: if a parent is not a dict object
        """
        if not path:
            return path
        attrs = path.split(".")
        current = self
        current_path = ""

        for attr in attrs[:-1]:
            if current_path:
                current_path += "." + attr
            else:
                current_path += attr

            try:
                current = current[attr]
                if not isinstance(current, dict):
                    raise TypeError(f"cant nest a path with {current.__class__} Type")
            except KeyError:
                d = {}  # type: ignore
                current[attr] = d  # type: ignore
                current = d  # type: ignore

        current[attrs[-1]] = head_class()
        return path

    def as_relative(self, path: str):
        return RelativePathAdapter(self, path)


class RelativePathAdapter:
    """Relative path adapter

    An adapter for :class:`ConfigFile` which makes it cleaner for accessing the same parent multiple times.
    Only has: `add_default`, `get_key`, `get_or_default`, `create_path`

    .. Example:
        rpa = RelativePathAdapter(my_config, "hydra.server")
        rpa.get_key("meta")  # is the same as `my_config.get_key("hydra.server.meta")`

    """

    def __init__(self, original: "ConfigFile", path: str):
        self.parent_path = path
        self.original = original

    def add_default(self, path: str, value: JSON_SERIALIZABLE, create: bool = False):
        return self.original.add_default(
            self.parent_path + "." + path, value, create=create
        )

    def get_key(self, path: str):
        return self.original.get_key(self.parent_path + "." + path)

    def get_or_default(
        self, path: str, default: JSON_SERIALIZABLE = MISSING  # type: ignore
    ) -> JSON_SERIALIZABLE:  # type: ignore
        return self.original.get_or_default(self.parent_path + "." + path, default)

    def create_path(
        self, path: str, head_class: Union[Callable[..., object], type] = dict
    ):
        return self.original.create_path(self.parent_path + "." + path, head_class)

    @staticmethod
    def as_relative(path: str):
        raise TypeError("Can not nest RelativePathAdapters")
