"""Protocol integrity and incomplete-run handling for an independent experiment."""
import json

import pytest

from itemizer.bootstrap.data import ContractError
from itemizer.contracts import NoteResult
from itemizer.independent import freeze_inputs, require_complete, require_authorization
from itemizer import independent


def test_frozen_protocol_can_repeat_but_cannot_silently_change(tmp_path):
    path = tmp_path / "protocol.json"
    payload = {"benchmark_sha256": "original", "model": "fixed-model"}
    freeze_inputs(path, payload)
    before = path.read_bytes()
    freeze_inputs(path, payload)
    assert path.read_bytes() == before
    with pytest.raises(ContractError, match="changed"):
        freeze_inputs(path, {**payload, "benchmark_sha256": "replacement"})
    assert json.loads(path.read_text()) == payload


def test_missing_or_unanswered_predictions_cannot_be_scored():
    with pytest.raises(ContractError, match="incomplete"):
        require_complete({}, {"a"})
    failed = NoteResult(fingerprint="a", note_id="n_a", status="review",
                        review_reason="provider_unavailable", model="fake")
    with pytest.raises(ContractError, match="incomplete"):
        require_complete({"a": failed}, {"a"})


def test_model_uncertainty_is_a_valid_abstention_not_an_outage():
    result = NoteResult(fingerprint="a", note_id="n_a", status="review",
                        review_reason="model_unsure", model="fake")
    require_complete({"a": result}, {"a"})


def test_external_authorization_is_scoped_to_the_dataset(tmp_path):
    path = tmp_path / "authorization.json"
    with pytest.raises(ContractError, match="authorization"):
        require_authorization(path, "dataset-a")
    path.write_text(json.dumps({"external_use": "user_confirmed_written_approval", "dataset_sha256": "dataset-b"}))
    with pytest.raises(ContractError, match="authorization"):
        require_authorization(path, "dataset-a")
    path.write_text(json.dumps({"external_use": "user_confirmed_written_approval", "dataset_sha256": "dataset-a"}))
    require_authorization(path, "dataset-a")


def test_benchmark_weights_come_from_reference_rows():
    weights = independent.benchmark_weights({"multi_note": "multi", "single_note": "single"},
                                            {"multi_note": 3, "single_note": 1})
    assert weights == {"large": 0.0, "multi": 0.75, "single": 0.25}


def test_cli_does_not_print_private_validation_input(monkeypatch, capsys):
    from itemizer.bootstrap.data import NoteLabel

    def malformed_label():
        NoteLabel.model_validate({"evidence_text": "PRIVATE_NOTE_MUST_NOT_PRINT"})

    monkeypatch.setattr(independent, "main", malformed_label)
    assert independent.run_cli() == 2
    output = capsys.readouterr()
    assert "PRIVATE_NOTE_MUST_NOT_PRINT" not in output.out + output.err
    assert "ValidationError" in output.out
