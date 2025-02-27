import numpy as np

from invutils import get_inventory
from obspy.core.utcdatetime import UTCDateTime

from gmprocess.core.stationtrace import StationTrace


def test_trace():
    data = np.random.rand(1000)
    header = {
        "sampling_rate": 1,
        "npts": len(data),
        "network": "US",
        "location": "11",
        "station": "ABCD",
        "channel": "HN1",
        "starttime": UTCDateTime(2010, 1, 1, 0, 0, 0),
    }
    inventory = get_inventory()
    invtrace = StationTrace(data=data, header=header, inventory=inventory)
    invtrace.set_provenance("detrend", {"detrending_method": "demean"})
    invtrace.set_parameter("failed", True)
    invtrace.set_parameter("corner_frequencies", [1, 2, 3])
    invtrace.set_parameter("metadata", {"name": "Fred"})

    assert invtrace.get_provenance("detrend")[0]["prov_attributes"] == {
        "detrending_method": "demean"
    }
    assert invtrace.get_parameter("failed")
    assert invtrace.get_parameter("corner_frequencies") == [1, 2, 3]
    assert invtrace.get_parameter("metadata") == {"name": "Fred"}

    prov = invtrace.provenance.get_prov_series()
    assert prov.iloc[0] == "demean"
