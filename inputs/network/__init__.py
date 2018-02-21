# ----------------------------------------------------------------------------
# vim: ts=4:sw=4:et
# ----------------------------------------------------------------------------
# inputs/network/__init__.py
# ----------------------------------------------------------------------------

"""
The TCP network connection input.
"""

from .protocol import ControlFactory


def initialize(reactor, port, interface, event_manager):

    """
    Initializes the TCP input and starts listening for connections.
    """

    factory = ControlFactory(event_manager)
    reactor.listenTCP(port, factory, interface=interface)


# ----------------------------------------------------------------------------
# inputs/network/__init__.py
# ----------------------------------------------------------------------------
