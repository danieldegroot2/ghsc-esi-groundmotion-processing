import pytest
import numpy as np
from obspy import UTCDateTime

from gmprocess.waveform_processing import windows


def test_windows_cut(fdsn_ci38457511_CLC):
    streams, event = fdsn_ci38457511_CLC

    st = windows.signal_split(streams, event=event)
    st = windows.signal_end(
        st,
        event_time=UTCDateTime(event.time),
        event_lon=event.longitude,
        event_lat=event.latitude,
        event_mag=event.magnitude,
        method="magnitude",
    )
    windows.cut(st)
    assert st.passed is True
    assert st[0].stats.endtime == "2019-07-06T03:22:55.998300Z"
    st_fail = st.copy()
    windows.cut(st_fail, sec_before_split=-10000)
    assert st_fail.passed is False


def test_windows_no_split_time(fdsn_ci38457511_CLC):
    streams, _ = fdsn_ci38457511_CLC

    windows.window_checks(streams)
    assert (
        streams[0].get_parameter("failure")["reason"]
        == "Cannot check window because no split time available."
    )


@pytest.mark.parametrize(
    "method, target",
    [
        pytest.param("noise_duration", "Failed noise window duration check."),
        pytest.param("signal_duration", "Failed signal window duration check."),
    ],
)
def test_windows_durations(method, target, fdsn_ci38457511_CLC):
    streams, event = fdsn_ci38457511_CLC

    streams = windows.signal_split(streams, event=event)
    streams = windows.signal_end(
        streams,
        event_time=UTCDateTime(event.time),
        event_lon=event.longitude,
        event_lat=event.latitude,
        event_mag=event.magnitude,
        method="magnitude",
    )

    if method == "noise_duration":
        windows.window_checks(streams, min_noise_duration=100)
    elif method == "signal_duration":
        windows.window_checks(streams, min_signal_duration=1000)

    assert streams[0].get_parameter("failure")["reason"] == target


@pytest.mark.parametrize(
    "method, target",
    [
        ("none", [390.0, 390.0, 390.0]),
        ("magnitude", [212.9617, 212.9617, 212.9617]),
        ("velocity", [149.9617, 149.9617, 149.9617]),
        ("model", [88.008733, 88.008733, 88.008733]),
    ],
)
def test_signal_end_methods(method, target, fdsn_ci38457511_CLC):
    streams, event = fdsn_ci38457511_CLC

    streams = windows.signal_split(streams, event=event)

    # Methods = None, magnitude, velocity, and model
    streams = windows.signal_end(
        streams,
        event_time=UTCDateTime(event.time),
        event_lon=event.longitude,
        event_lat=event.latitude,
        event_mag=event.magnitude,
        method=method,
    )
    durations = []
    for tr in streams:
        durations.append(
            tr.get_parameter("signal_end")["end_time"] - UTCDateTime(tr.stats.starttime)
        )
    np.testing.assert_allclose(durations, target)


def test_signal_split2(load_data_us1000778i):
    streams, event = load_data_us1000778i
    streams = streams.copy()

    stream = streams[0]
    windows.signal_split(stream, event)

    cmpdict = {
        "split_time": UTCDateTime(2016, 11, 13, 11, 3, 0, 0),
        "method": "p_arrival",
        "picker_type": "travel_time",
    }

    pdict = stream[0].get_parameter("signal_split")
    for key, value in cmpdict.items():
        v1 = pdict[key]
        # because I can't figure out how to get utcdattime __eq__
        # operator to behave as expected with the currently installed
        # version of obspy, we're going to pedantically compare two
        # of these objects...
        if isinstance(value, UTCDateTime):
            # value.__precision = 4
            # v1.__precision = 4
            assert value.year == v1.year
            assert value.month == v1.month
            assert value.day == v1.day
            assert value.hour == v1.hour
            assert value.minute == v1.minute
            assert value.second == v1.second
        else:
            assert v1 == value
