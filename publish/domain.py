import os
import sys
import logging
import traceback

import publish.abstract

log = logging.getLogger('publish.domain')


class Context(publish.abstract.Context):
    """Store selected instances from currently active scene"""

    @property
    def errors(self):
        errors = list()
        for instance in self:
            errors.extend(instance.errors)
        return errors

    @property
    def has_errors(self):
        for error in self.errors:
            return True
        return False


class Instance(publish.abstract.Instance):
    """An individually publishable component within scene

    Examples include rigs, models.

    .. note:: This class isn't meant for use directly.
        See :func:context() below.

    Attributes:
        path (str): Absolute path to instance (i.e. objectSet in this case)
        config (dict): Full configuration, as recorded onto objectSet.

    """


def current_host():
    """Return currently active host

    When running Publish from within a host, this function determines
    which host is running and returns the equivalent keyword.

    Example:
        >> # Running within Autodesk Maya
        >> host()
        'maya'
        >> # Running within Sidefx Houdini
        >> current_host()
        'houdini'

    """

    if 'maya' in os.path.basename(sys.executable):
        # Maya is distinguished by looking at the currently running
        # executable of the Python interpreter. It will be something
        # like: "maya.exe" or "mayapy.exe"; without suffix for
        # posix platforms.
        return 'maya'

    else:
        raise ValueError("Could not determine host")


def select(context=None):
    """Parse currently active scene and return Context

    The context includes which nodes to extract along
    with their configuration.

    Returns:
        Context: Fully qualified context object.

    """

    plugins = publish.plugin.discover(type='selectors')

    context = context if not context is None else Context()

    for PluginClass in plugins:
        plugin = PluginClass(context)

        if not current_host() in plugin.hosts:
            continue

        try:
            log.info("Selecting with {plugin}".format(
                plugin=PluginClass.__name__))
            plugin.process()

        except Exception:
            log.error(traceback.format_exc())
            log.error('An exception occured during the '
                      'execution of plugin: {0}'.format(PluginClass))

    return context


def process(process, context):
    """Perform process step `process` upon context `context`

    Arguments:
        process (str): Type of process to apply
        context (Context): Context upon which to appy process

    Example:
        >>> ctx = Context()
        >>> process('validators', ctx)
        Context([])

    """

    assert isinstance(context, Context)

    plugins = publish.plugin.discover(type=process)

    for instance in context:
        family = instance.config.get('family')

        log.info("Processing {inst} ({family})".format(
            inst=instance, family=family))

        # Run tests for pre-defined host and family
        for PluginClass in plugins:
            plugin = PluginClass(context)

            if not current_host() in plugin.hosts:
                continue

            if not family in plugin.families:
                continue

            try:
                log.info("{process} {instance} with {plugin}".format(
                    process=process,
                    instance=instance,
                    plugin=PluginClass.__name__))
                plugin.process()
            except Exception as exc:
                log.error(traceback.format_exc())
                log.error('An exception occured during the '
                          'execution of plugin: {0}'.format(PluginClass))
                exc.parent = instance
                exc.traceback = traceback.format_exc()
                instance.errors.append(exc)

    return context
