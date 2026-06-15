"""Test RunContext and RunLog."""
from opc_foundation.run.run_context import RunContext
from opc_foundation.run.run_log import RunLog


def test_run_context_defaults():
    ctx = RunContext(pipeline_name="test")
    assert ctx.run_id.startswith("run_")
    assert ctx.pipeline_name == "test"
    assert ctx.started_at is not None


def test_run_context_custom():
    ctx = RunContext(project_id="proj1", pipeline_name="acq", run_id="run_abc")
    assert ctx.project_id == "proj1"
    assert ctx.run_id == "run_abc"


def test_run_log_start_end():
    log = RunLog("run_test")
    log.start_step("step1")
    entry = log.end_step("step1", status="ok", output_count=5)
    assert entry is not None
    assert entry.status == "ok"
    assert entry.output_count == 5


def test_run_log_persist(tmp_path):
    log = RunLog("run_xyz")
    log.start_step("s1")
    log.end_step("s1", status="ok")
    p = tmp_path / "run_log.jsonl"
    log.write_run_log(p)
    entries = RunLog.load_run_log(p)
    assert len(entries) == 1
    assert entries[0].step_name == "s1"
