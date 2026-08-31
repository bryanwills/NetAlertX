from server.plugins.plugin_helper import is_mac, normalize_mac, per_item_timeout


def test_is_mac_accepts_wildcard():
    # is_mac checks structure, so it should still return True
    assert is_mac("aa:bb:cc:*") is True
    assert is_mac("AA-BB-CC:*") is True  # mixed case/separator should still be recognized
    assert is_mac("00:11:22:33:44:55") is True
    assert is_mac("00-11-22-33-44-55") is True
    assert is_mac("not-a-mac") is False


def test_normalize_mac_preserves_wildcard():
    # UPDATED: Expected results are now lowercase to match the DB standard
    assert normalize_mac("aa:bb:cc:*") == "aa:bb:cc:*"
    assert normalize_mac("AA-BB-CC-*") == "aa:bb:cc:*"

    # Call once and assert deterministic result
    result = normalize_mac("aabbcc*")
    assert result == "aa:bb:cc:*", f"Expected 'aa:bb:cc:*' but got '{result}'"

    # Ensure full MACs are lowercase too
    assert normalize_mac("AA:BB:CC:DD:EE:FF") == "aa:bb:cc:dd:ee:ff"


def test_normalize_mac_preserves_internet_root():
    # Stays lowercase
    assert normalize_mac("internet") == "internet"
    assert normalize_mac("Internet") == "internet"
    assert normalize_mac("INTERNET") == "internet"


def test_per_item_timeout_unchanged_for_zero_or_one_items():
    # The common case (0 or 1 queued items) must see no behavior change.
    assert per_item_timeout(10, 0) == 10
    assert per_item_timeout(10, 1) == 10


def test_per_item_timeout_divides_budget_across_items():
    assert per_item_timeout(10, 5) == 2
    assert per_item_timeout(9, 2) == 4  # integer division, not rounded


def test_per_item_timeout_never_goes_below_floor():
    # A large queue must not divide the per-item timeout down to 0.
    assert per_item_timeout(10, 100) == 1
    assert per_item_timeout(10, 100, floor=2) == 2