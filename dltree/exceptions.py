class DLTError(Exception):
    exit_code = 10


class ConfigError(DLTError):
    exit_code = 2


class NotFoundError(DLTError):
    exit_code = 3


class ExternalDependencyError(DLTError):
    exit_code = 4


class DiskSpaceError(DLTError):
    exit_code = 5


class DatabaseError(DLTError):
    exit_code = 10


class ImportExecutionError(DLTError):
    exit_code = 10


class DownloadExecutionError(DLTError):
    exit_code = 10
