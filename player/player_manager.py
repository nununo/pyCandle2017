#!/usr/bin/env python
# vim: ts=4:sw=4:et

import os
import random

from twisted.internet import defer
from twisted import logger

from .dbus_manager import OMXPlayerDBusManager
from .player import OMXPlayer
from .misc import sleep


class PlayerManager(object):

    def __init__(self, reactor, settings):

        self.log = logger.Logger(namespace='player-manager')

        self.reactor = reactor
        self.settings = settings
        self.dbus_mgr = OMXPlayerDBusManager(reactor)

        self.files = {}
        self.base_player = None
        self.current_level = 0
        self.current_player = None

        self._update_ld_lib_path()
        self._find_files()

        self.done = defer.Deferred()


    def _update_ld_lib_path(self):

        extra_ld_lib_path = self.settings['environment']['ld_library_path']
        if extra_ld_lib_path:
            ld_lib_path = os.environ.get('LD_LIBRARY_PATH', '')
            if ld_lib_path:
                new_ld_lib_path = '%s:%s' % (extra_ld_lib_path, ld_lib_path)
            else:
                new_ld_lib_path = extra_ld_lib_path
            os.environ['LD_LIBRARY_PATH'] = new_ld_lib_path
            self.log.debug('LD_LIBRARY_PATH set to {v!r}', v=new_ld_lib_path)


    def _find_files(self):

        for level, level_info in self.settings['levels'].items():
            level_folder = level_info['folder']
            self.files[int(level)] = [
                os.path.join(level_folder, name)
                for name in os.listdir(level_folder)
            ]
        self.log.info('files found: {d!r}', d=self.files)


    def generate_player_name(self, filename):

        return 'com.nunogodinho.vela2017-%s' % (
            os.path.splitext(os.path.basename(filename))[0],
        )


    def _get_file_for_level(self, level):

        return random.sample(self.files[level], 1)[0]


    @property
    def executable(self):

        result = self.settings['environment']['omxplayer_bin']
        self.log.info('executable is {e!r}', e=result)
        return result


    @defer.inlineCallbacks
    def start(self):

        yield self.dbus_mgr.connect_to_dbus()
        self.base_player = OMXPlayer(
            self._get_file_for_level(0),
            self,
            layer=0,
            loop=True,
        )
        yield self.base_player.spawn()


    @defer.inlineCallbacks
    def level(self, n):

        if n < self.current_level:
            return

        new_player = OMXPlayer(
            self._get_file_for_level(n),
            self,
            layer=n,
            fadein=self.settings['levels'][str(n)]['fadein'],
            fadeout=self.settings['levels'][str(n)]['fadeout'],
        )
        yield new_player.spawn(end_callable=lambda exit_code: self._player_ended(n))
        if self.current_player:
            yield self.current_player.stop()
        self.current_level = n
        self.current_player = new_player


    def _player_ended(self, level):

        self.log.info('player level={l!r} ended', l=level)
        self.current_level = 0
        self.current_player = None


    @defer.inlineCallbacks
    def stop(self):

        if self.current_player:
            self.log.info('stopping player level={l!r}', l=self.current_level)
            yield self.current_player.stop()
        self.log.info('stopping base player')
        yield self.base_player.stop()

        self.done.callback(None)
