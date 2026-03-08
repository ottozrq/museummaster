"""Central module used by components to retrieve env config and secret items.

Setup and query config items in environment:

    >>> # set some env variable with Museum namespace
    >>> os.environ["MUSEUM_PSQL_SERVER"] = "localhost:1234"

    >>> import museum.config
    >>> config.env.getstr("psql_server")
    'localhost:1234'
    >>> config.env.getstr("no_exist")
    museum.config.ConfigValueNotFound: 'no_exist' not found

Setup and query secrets in environment and/or secrets manager:

    >>> # set some env variable with MUSEUM_SECRET namespace
    >>> # OR some code to store "secret" in secretsmanager,
    >>> # with key "<NAMESPACE>-<KEY>"
    >>> os.environ["MUSEUM_SECRET_PASSWORD"] = "secret"

    >>> import museum.config
    >>> config.secrets.getstr("password")
    'secret'
    >>> config.secrets.getstr("no_exist")
    MUSEUM.config.ConfigValueNotFound: 'no_exist' not found

"""

import os

import getconf

# import utils.aws.secrets_manager


class ConfigValueNotFound(ValueError):
    pass


class _ConfigGetterNoDefaults(getconf.BaseConfigGetter):
    """Override default getconf getter to raise on missing key."""

    def _no_default(self, method, key):
        """Forbid default value and raise if none found."""
        value = method(key, default=None)
        if value is None:
            if isinstance(self, _EnvGetter):
                msg = "Please declare MUSEUM_{key_upper} " "in environment.".format(
                    key_upper=key.upper().replace(".", "_"),
                )
            else:
                msg = (
                    "Please declare MUSEUM_SECRET_{key_upper} "
                    "in environment, or setup {namespace}-{key} "
                    "in SecretsManager.".format(
                        key_upper=key.upper().replace(".", "_"),
                        namespace=os.environ.get("NAMESPACE", "<NAMESPACE>"),
                        key=key,
                    )
                )
            raise ConfigValueNotFound(msg)
        return value

    def get(self, key):
        return self._no_default(super().get, key)

    def getstr(self, key) -> str:
        return self._no_default(super().getstr, key)

    def getlist(self, key, sep=","):
        return self._no_default(super().getlist, key)

    def getbool(self, key):
        return self._no_default(super().getbool, key)

    def getint(self, key):
        return self._no_default(super().getint, key)

    def getfloat(self, key):
        return self._no_default(super().getfloat, key)

    def gettimedelta(self, key):
        return self._no_default(super().gettimedelta, key)


class _EnvGetter(_ConfigGetterNoDefaults):
    """Setup env as GetConf from environ only."""

    def __init__(self):
        super().__init__(
            getconf.finders.NamespacedEnvFinder("MUSEUM"),
        )


class _SecretGetter(_ConfigGetterNoDefaults):
    """Setup secrets as GetConf from environ and secrets manager."""

    def __init__(self):
        super().__init__(
            getconf.finders.NamespacedEnvFinder("museum_secret"),
            # utils.aws.secrets_manager.SecretFinder(),
        )


env = _EnvGetter()
secrets = _SecretGetter()
