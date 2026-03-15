import asyncio
from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner


class _RunnerWithoutFormalResolver:
    _load_agent_spec_for_step = staticmethod(lambda *_args, **_kwargs: None)
    _parse_structured_output_if_possible = staticmethod(lambda *_args, **_kwargs: None)
    _extract_ssot_contract_payload = staticmethod(lambda *_args, **_kwargs: None)
    _materialize_workspace_formal_ssot_markdown = staticmethod(lambda **_kwargs: {"status": "ok"})


def test_materialize_ssot_outputs_falls_back_when_runner_lacks_formal_output_helper():
    runner = _RunnerWithoutFormalResolver()
    step = SimpleNamespace(outputs=[])

    result = asyncio.run(
        LLMRunner._materialize_ssot_outputs(
            runner,
            ctx=None,
            step=step,
            workflow_id="wf_task_demo",
            generated_text="ignored",
        )
    )

    assert result == {"status": "ok"}
