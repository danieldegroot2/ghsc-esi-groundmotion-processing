import numpy as np

from gmprocess.waveform_processing.corner_frequencies import (
    get_corner_frequencies,
)


def test_corner_frequencies(setup_corner_freq_test):
    _, event, processed_streams = setup_corner_freq_test
    processed_streams = processed_streams.copy()

    lp = []
    hp = []
    for stream in processed_streams:
        if not stream.passed:
            continue
        stream = get_corner_frequencies(stream, event, method="snr")
        for tr in stream:
            cfdict = tr.get_parameter("corner_frequencies")
            lp.append(cfdict["lowpass"])
            hp.append(cfdict["highpass"])

    np.testing.assert_allclose(
        np.sort(hp),
        [0.024919013207076998, 0.024919013207076998, 0.024919013207076998],
        atol=1e-6,
    )
    np.testing.assert_allclose(np.sort(lp), [100.0, 100.0, 100.0])


def test_corner_frequencies_magnitude(setup_corner_freq_mag_test):
    _, event, processed_streams = setup_corner_freq_mag_test
    processed_streams = processed_streams.copy()

    lp = []
    hp = []
    for stream in processed_streams:
        if not stream.passed:
            continue
        stream = get_corner_frequencies(stream, event, method="magnitude")
        for tr in stream:
            cfdict = tr.get_parameter("corner_frequencies")
            lp.append(cfdict["lowpass"])
            hp.append(cfdict["highpass"])

    np.testing.assert_allclose(hp, [0.3, 0.3, 0.3])
    np.testing.assert_allclose(lp, [35.0, 35.0, 35.0])
