@dataclass
class GpsAttack:
    """Attack targeting GPS / navigation.

    Args:
        type: One of ``passthrough``, ``replay``, ``drift``
        lat: Spoofed latitude (for ``replay``).
        lon: Spoofed longitude (for ``replay``).
        alt: Spoofed altitude (for ``replay``).
        rate_lat: Drift rate in deg/s (for ``drift``).
        rate_lon: Drift rate in deg/s (for ``drift``).
    """

    type: str = "passthrough"
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0
    rate_lat: float = 1e-5
    rate_lon: float = 1e-5