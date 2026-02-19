
import pytest
import json
import os
from dataclasses import asdict
from datetime import datetime
from lee.orchestrator.execution.receipt import ExecutionReceipt, ReceiptVerifier, ReceiptStore, asdict

def test_execution_receipt_integrity():
    """Test signing and verification logic"""
    receipt = ExecutionReceipt(
        run_id="run-1", step_id="step-1", repo_id="repo-1",
        commit_before="abc", commit_after="def",
        inputs_hash="hash1", patch_hash="hash2",
        exit_code=0, timestamp="2023-01-01T00:00:00",
        executor_type="llm"
    )
    
    # 1. Sign
    receipt.sign()
    assert receipt.checksum
    
    # 2. Verify valid
    verifier = ReceiptVerifier()
    assert verifier.verify(receipt)
    
    # 3. Tamper - change data field
    receipt.commit_after = "modified"
    assert not verifier.verify(receipt)
    
    # 4. Tamper - change checksum
    receipt.commit_after = "def" # Restore
    original_checksum = receipt.checksum
    receipt.checksum = "fake_checksum"
    assert not verifier.verify(receipt)

def test_receipt_store_io(tmp_path):
    """Test saving and loading receipts"""
    # runs_root is passed to ReceiptStore
    runs_root = tmp_path
    store = ReceiptStore(str(runs_root))
    
    receipt1 = ExecutionReceipt(
        run_id="run-1", step_id="step-1", repo_id="repo-1",
        commit_before="abc", commit_after="def",
        inputs_hash="hash1", patch_hash="hash2",
        exit_code=0, timestamp="2023-01-01T00:00:00",
        executor_type="llm"
    )
    
    receipt2 = ExecutionReceipt(
        run_id="run-1", step_id="step-2", repo_id="repo-1",
        commit_before="def", commit_after="ghi",
        inputs_hash="hash3", patch_hash="hash4",
        exit_code=0, timestamp="2023-01-01T00:01:00",
        executor_type="llm"
    )
    
    store.save(receipt1)
    store.save(receipt2)
    
    # Check file existence
    receipt_file = runs_root / "run-1" / "receipts.jsonl"
    assert receipt_file.exists()
    
    # Load back
    loaded = store.load_by_run("run-1")
    assert len(loaded) == 2
    assert loaded[0].step_id == "step-1"
    assert loaded[1].step_id == "step-2"
    
    # Verify loaded receipt is valid
    verifier = ReceiptVerifier()
    assert verifier.verify(loaded[0])
    assert verifier.verify(loaded[1])
