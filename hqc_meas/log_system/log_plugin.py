# -*- coding: utf-8 -*-
#==============================================================================
# module : pref_plugin.py
# author : Matthieu Dartiailh
# license : MIT license
#==============================================================================
import os
import logging
import atexit
from atom.api import Unicode, Dict, List, Tuple

from hqc_meas.utils.has_pref_plugin import HasPrefPlugin
from .tools import PanelModel, GuiHandler, DayRotatingTimeHandler


MODULE_PATH = os.path.dirname(__file__)


class LogPlugin(HasPrefPlugin):
    """ Plugin managing the application logging.

    """
    #--- Public API -----------------------------------------------------------

    # List of installed handlers.
    handler_ids = List(Unicode())

    # List of installed filters.
    filter_ids = List(Unicode())

    def start_logging(self):
        """ Start the log system.

        """
        log_dir = os.path.join(MODULE_PATH, 'logs')
        # Create log dir if it does not exist.
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)

        # Add day rotating handler to the root logger.
        handler = DayRotatingTimeHandler(os.path.join(log_dir, 'hqc_log.log'))
        self.add_handler(u'standard', handler)

        # XXXX add auto redirection

        # Clean up upon application exit.
        atexit.register(logging.shutdown)

    def add_handler(self, id, handler=None, logger='', mode=None):
        """ Add a handler to the specified logger.

        Parameters
        ----------
        id : unicode
            Id of the new handler. This id should be unique.

        handler : logging.Handler, optional
            Handler to add.

        logger : str, optional
            Name of the logger to which the handler should be added. By default
            the handler is added to the root logger.

        mode : {'ui', }, optional
            Conveninence to add a simple logger. If this argument is specified,
            handler will be ignored and the command will return useful
            references (the model to which can be connected a ui for the 'ui'
            mode).

        Returns
        -------
        refs :
            None save if a mode was selected, in this case see the mode
            description.

        """
        refs = []
        id = unicode(id)
        if mode:
            if mode == 'ui':
                model = PanelModel()
                handler = GuiHandler(model=model)
                refs.append(model)

        name = logger
        logger = logging.getLogger(logger)

        logger.addHandler(handler)

        self._handlers[id] = (handler, name)

        if refs:
            return refs

    def remove_handler(self, id):
        """ Remove the specified handler.

        Parameters
        ----------
        id : unicode
            Id of the handler to remove.

        """
        handlers = self._handlers
        id = unicode(id)
        if id in handlers:
            handler, logger_name = handlers.pop(id)
            logger = logging.getLogger(logger_name)
            logger.removeHandler(handler)
            for filter_id, infos in self._filters.values():
                if infos[1] == id:
                    del self._filters[filter_id]

    def add_filter(self, id, filter, handler_id):
        """ Add a filter to the specified handler.

        Parameters
        ----------
        id : unicode
            Id of the filter to add.

        filter : object
            Filter to add to the specified handler (object implemeting a filter
            method).

        handler_id : unicode
            Id of the handler to which this filter should be added

        """
        handlers = self._handlers
        id = unicode(id)
        if handler_id in handlers:
            handler = handlers[handler_id]
            handler.addFilter(filter)
            self._filters[id] = (filter, handler_id)

        else:
            logger = logging.getLogger(__name__)
            logger.warn('Handler {} does not exist')

    def remove_filter(self, id):
        """ Remove the specified filter.

        Parameters
        ----------
        id : unicode
            Id of the filter to remove.

        """
        filters = self._filters
        id = unicode(id)
        if id in filters:
            filter, handler_id = filters.pop(id)
            handler = self._handlers[handler_id]
            handler.removeFilter(filter)

    def set_formatter(self, handler_id, formatter):
        """ Set the formatter of the specified handler.

        Parameters
        ----------
        handler_id : unicode
            Id of the handler whose formatter shoudl be set.

        formatter : Formatter
            Formatter for the handler.

        """
        handlers = self._handlers
        handler_id = unicode(handler_id)
        if handler_id in handlers:
            handler = handlers[handler_id]
            handler.setFormatter(filter)

        else:
            logger = logging.getLogger(__name__)
            logger.warn('Handler {} does not exist')

    #---- Private API ---------------------------------------------------------

    # Mapping between handler ids and handler, logger name pairs.
    _handlers = Dict(Unicode(), Tuple())

    # Mapping between filter_id and filter, handler_id pairs.
    _filters = Dict(Unicode(), Tuple())
