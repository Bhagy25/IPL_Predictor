"""The modelling-table fingerprint does not depend on the checkout's line endings."""
import hashlib
import json
from pathlib import Path

from cricketlens.hashing import file_sha256, table_sha256
from cricketlens.model_benchmark import TASKS

ROOT = Path(__file__).resolve().parents[1]


def test_crlf_and_lf_copies_of_a_table_have_the_same_fingerprint(tmp_path):
    lf, crlf = tmp_path / "lf.csv", tmp_path / "crlf.csv"
    lf.write_bytes(b"a,b\n1,2\n3,4\n")
    crlf.write_bytes(b"a,b\r\n1,2\r\n3,4\r\n")
    assert table_sha256(lf) == table_sha256(crlf) == hashlib.sha256(b"a,b\n1,2\n3,4\n").hexdigest()
    # Binary files are hashed byte for byte
    assert file_sha256(lf) != file_sha256(crlf)


def test_recorded_fingerprints_equal_the_committed_lf_tables():
    selection = json.loads((ROOT / "reports" / "model_benchmark" / "selection.json").read_text(encoding="utf-8"))
    for task in TASKS:
        path = ROOT / "data" / "processed" / task.path
        lf = path.read_bytes().replace(b"\r\n", b"\n")
        assert selection["tasks"][task.name]["input_sha256"] == hashlib.sha256(lf).hexdigest() == table_sha256(path)
