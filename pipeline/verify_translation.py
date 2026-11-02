"""Independently compare the English translation with its original Git blobs."""
from pathlib import Path
import ast
import csv
import hashlib
import io
import itertools
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class TextFree(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(ast.Constant(value="<text>"), node)
        return node


def run():
    record = json.loads((ROOT / "resources/translation-provenance.json").read_text(encoding="utf-8"))
    commit = record["original_commit"]

    def original(name):
        return subprocess.check_output(["git", "show", commit + ":" + name], cwd=ROOT)

    def digest(data):
        return hashlib.sha256(data).hexdigest()

    for name, source in record["scientific_sources"].items():
        before = original("pipeline/" + name)
        after = (ROOT / "pipeline" / name).read_bytes()
        assert digest(before) == source["original_sha256"], name
        assert digest(after) == source["translated_sha256"], name
        trees = [ast.dump(TextFree().visit(ast.parse(data.decode("utf-8-sig"))),
                          include_attributes=False) for data in [before, after]]
        assert trees[0] == trees[1], name
        assert digest(trees[0].encode()) == source["nontext_ast_sha256"], name

    cells = 0
    for entry in record["numeric_csvs"]:
        name = entry["file"]
        before, after = original(name), (ROOT / name).read_bytes()
        assert digest(before) == entry["original_sha256"], name
        assert digest(after) == entry["translated_sha256"], name
        readers = [csv.reader(io.StringIO(data.decode("utf-8-sig"))) for data in [before, after]]
        count = 0
        for old_row, new_row in itertools.zip_longest(*readers):
            assert old_row is not None and new_row is not None and len(old_row) == len(new_row), name
            for old, new in zip(old_row, new_row):
                try:
                    float(old)
                except ValueError:
                    continue
                assert old == new, (name, old, new)
                count += 1
        assert count == entry["numeric_cells_unchanged"], name
        cells += count

    for name in record["raw_input_files_unchanged"]:
        assert original(name) == (ROOT / name).read_bytes(), name
    assert cells == record["csv_numeric_values_checked"]
    result = dict(passed=True, scientific_sources=len(record["scientific_sources"]),
                  raw_inputs=len(record["raw_input_files_unchanged"]), numeric_csv_cells=cells)
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    run()
