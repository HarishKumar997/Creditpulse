from creditpulse.generate import generate


def test_same_seed_writes_the_same_bytes(tmp_path):
    generate(42, 40, "batch-a", tmp_path / "one")
    generate(42, 40, "batch-a", tmp_path / "two")
    for name in ("customers.csv", "accounts.csv", "loans.csv", "events.csv", "repayments.json"):
        left = (tmp_path / "one" / "landing" / "batch-a" / name).read_bytes()
        right = (tmp_path / "two" / "landing" / "batch-a" / name).read_bytes()
        assert left == right


def test_different_seed_changes_customers(tmp_path):
    generate(1, 30, "batch-a", tmp_path / "one")
    generate(2, 30, "batch-a", tmp_path / "two")
    left = (tmp_path / "one" / "landing" / "batch-a" / "customers.csv").read_bytes()
    right = (tmp_path / "two" / "landing" / "batch-a" / "customers.csv").read_bytes()
    assert left != right
