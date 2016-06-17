
import abc

from six import add_metaclass
from pkg_resources import iter_entry_points, load_entry_point, DistributionNotFound

from alerta.app import app

LOG = app.logger


class RejectException(Exception):
    """The alert was rejected because the format did not meet the required policy."""


@add_metaclass(abc.ABCMeta)
class PluginBase(object):

    def __init__(self, name=None):
        self.name = name or self.__module__

    @abc.abstractmethod
    def pre_receive(self, alert):
        """Pre-process an alert based on alert properties or reject it by raising RejectException."""
        return alert

    @abc.abstractmethod
    def post_receive(self, alert):
        """Send an alert to another service or notify users."""
        return None

    @abc.abstractmethod
    def status_change(self, alert, status, text):
        """Trigger integrations based on status changes."""
        return None


class Plugins(object):

    def __init__(self):

        self.plugins = {}
        self.rules = None

        self.register()

    def register(self):

        for ep in iter_entry_points('alerta.plugins'):
            LOG.debug("Server plug-in '%s' found.", ep.name)
            try:
                if ep.name in app.config['PLUGINS']:
                    plugin = ep.load()
                    if plugin:
                        self.plugins[ep.name] = plugin()
                        LOG.info("Server plug-in '%s' enabled.", ep.name)
                else:
                    LOG.debug("Server plug-in '%s' not enabled in 'PLUGINS'.", ep.name)
            except Exception as e:
                LOG.error("Server plug-in '%s' could not be loaded: %s", ep.name, e)

        try:
            self.rules = load_entry_point('alerta-routing', 'alerta.routing', 'rules')
        except (DistributionNotFound, ImportError):
            LOG.info('Failed to load any plugin routing rules. All plugins will be evaluated.')

    def routing(self, alert):

        if self.rules and self.plugins:
            return self.rules(alert, self.plugins)
        else:
            return self.plugins.values()
