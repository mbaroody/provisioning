from typing import Optional


class PathLikeError(Exception):
    """All Exceptions defined in this addon is a subclass of this class"""

    def __init__(self, code: Optional[int] = None, msg: Optional[str] = None):
        super().__init__()
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        class_name = self.__class__.__name__
        errmsg = class_name
        if self.code is not None:
            errmsg += (f"<{self.code}>")
        if self.msg:
            errmsg += (f": {self.msg}")
        return errmsg


class MalformedURLError(PathLikeError):
    """The URL doesn't pass regex search. """
    pass


class RootNotFoundError(PathLikeError):
    """The URL looks fine, but doesn't point to a valid location."""
    pass


class IsAFileError(PathLikeError):
    """Expected a directory, but is a file instead. """
    pass


class RateLimitError(PathLikeError):
    """Rate Limit Exceeded. """
    pass


class ServerError(PathLikeError):
    """Nothing wrong with the request, but with the server."""
    pass


class RequestError(PathLikeError):
    """Other various errors that happened during request."""
    pass
