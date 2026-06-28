from __future__ import annotations

import pytest

import main


def test_runtime_preview_output_without_runtime_preview_is_parser_error(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main.main(["--runtime-preview-output", "runtime-preview-full.json", "Działasz?"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--runtime-preview-output wymaga --runtime-preview albo --dev-preview" in err
