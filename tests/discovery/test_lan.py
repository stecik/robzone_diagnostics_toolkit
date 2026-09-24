from robzone_diag.discovery import lan

# Sanitized samples: addresses are documentation/private ranges, MACs are fake.
WINDOWS_CZ = """
Rozhraní: 192.168.1.5 --- 0x5
  Internetová adresa    Fyzická adresa        Typ
  192.168.1.1           d8-21-da-00-00-01     dynamický
  192.168.1.7           a8-80-55-00-00-02     dynamický
  192.168.1.255         ff-ff-ff-ff-ff-ff     statický
  224.0.0.22            01-00-5e-00-00-16     statický
"""

MACOS = """
? (192.168.1.1) at d8:21:da:0:0:1 on en0 ifscope [ethernet]
? (192.168.1.7) at a8:80:55:0:0:2 on en0 ifscope [ethernet]
? (192.168.1.9) at (incomplete) on en0 ifscope [ethernet]
"""

LINUX_PROC = """IP address       HW type     Flags       HW address            Mask     Device
192.168.1.1      0x1         0x2         d8:21:da:00:00:01     *        wlan0
192.168.1.7      0x1         0x2         a8:80:55:00:00:02     *        wlan0
"""

EXPECTED = [
    lan.Neighbour("192.168.1.1", "d8:21:da:00:00:01"),
    lan.Neighbour("192.168.1.7", "a8:80:55:00:00:02"),
]


def test_parses_windows_arp_in_any_locale():
    assert lan.parse_neighbour_table(WINDOWS_CZ) == EXPECTED


def test_parses_macos_arp_with_short_octets():
    assert lan.parse_neighbour_table(MACOS) == EXPECTED


def test_parses_linux_proc_net_arp():
    assert lan.parse_neighbour_table(LINUX_PROC) == EXPECTED


def test_locally_administered_mac():
    assert lan.is_locally_administered("da:a1:19:00:00:01")
    assert not lan.is_locally_administered("a8:80:55:00:00:02")


def test_private_address_check():
    assert lan.is_private_address("192.168.1.7")
    assert lan.is_private_address("10.0.0.1")
    assert not lan.is_private_address("8.8.8.8")
    assert not lan.is_private_address("127.0.0.1")
    assert not lan.is_private_address("not-an-ip")
