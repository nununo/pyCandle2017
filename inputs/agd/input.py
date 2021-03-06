# ----------------------------------------------------------------------------
# vim: ts=4:sw=4:et
# ----------------------------------------------------------------------------
# inputs/agd/input.py
# ----------------------------------------------------------------------------

"""
Aggregated derivative input processor.
"""


from collections import deque

from twisted.internet import defer
from twisted import logger

from inputs import input_base



_log = logger.Logger(namespace='inputs.agd')




class AggregatedDerivative(input_base.InputBase):

    """
    Aggregated derivative input processor.

    Keeps track of the last `buffer_size` readings sourced from `source` and
    calculates an aggregated derivative which is compared to the given
    `thresholds` and, in turn, calls `change_play_level` on the `wiring`.
    """

    def __init__(self, reactor, wiring, buffer_size, thresholds, source):

        super(AggregatedDerivative, self).__init__(reactor, wiring)

        self._thresholds = thresholds
        self._source_type = source

        self._readings = deque(maxlen=buffer_size)
        self._last_play_level = 0

        # Handle the output produced by the selected input `source`.
        wiring[source].wire(self._handle_new_reading)

        # Handle requests to get/set AGD thresholds.
        wiring.request_agd_thresholds.wire(self._notify_agd_thresholds)
        wiring.set_agd_threshold.wire(self._set_threshold)


    @defer.inlineCallbacks
    def start(self):

        _log.info('started')
        yield defer.succeed(None)


    @defer.inlineCallbacks
    def stop(self):

        _log.info('stopped')
        yield defer.succeed(None)


    def _notify_agd_thresholds(self):

        for level, value in enumerate(self._thresholds, start=1):
            self._wiring.notify_agd_threshold(level, value)


    def _set_threshold(self, level, value):

        try:
            self._thresholds[level-1] = value
        except IndexError:
            _log.warn('invalid threshold level: {l!r}', l=level)
        else:
            _log.info('threshold level {l!r} set to {v!r}', l=level, v=value)
            self._wiring.notify_agd_threshold(level, value)



    def _handle_new_reading(self, reading):

        # Track reading and calculate the aggregated derivative.
        self._readings.append(reading)
        agd = self._aggregated_derivative()

        _log.info('reading={r!r}, agd={a!r}', r=reading, a=agd)
        _log.debug('readings={r!r}', r=self._readings)

        # Output both the raw reading as well as the aggregated derivative.
        self._wiring.agd_output(raw=reading, agd=agd)

        # Find if the aggregated derivative is over any of the thresholds and
        # request a level change, if that is the case.
        play_level = 0
        for level, threshold in enumerate(self._thresholds, start=1):
            if agd >= threshold:
                play_level = level
        if play_level != self._last_play_level:
            self._last_play_level = play_level
            comment = 'agd-%s == %r' % (self._source_type, agd)
            self._wiring.change_play_level(play_level, comment)


    @staticmethod
    def _pairs_from(iterable):

        """
        Generates (i0, i1), (i1, i2), (i2, i3), ... tuples from `iterable`.
        """

        i = iter(iterable)
        try:
            one = next(i)
            while True:
                other = next(i)
                yield one, other
                one = other
        except StopIteration:
            pass


    def _aggregated_derivative(self):

        """
        Calculates the aggregated derivative over `buffer_size` readings:
        - Aggregates consecutive reading deltas as long as they are >= 0.
        - If any consecutive runing delta is negative, sets the aggregation to 0.
        """

        result = 0
        for one, next_one in self._pairs_from(self._readings):
            derivative = next_one - one
            if derivative >= 0:
                result += derivative
            else:
                result = 0
        return result


# ----------------------------------------------------------------------------
# inputs/agd/input.py
# ----------------------------------------------------------------------------
