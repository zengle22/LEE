"""测试 flowcore 兼容性重定向"""
import warnings


def test_flowcore_orchestrator_redirect():
    """测试 flowcore.orchestrator 重定向到 lee.orchestrator.execution"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from flowcore.orchestrator import TemplateManager as FlowcoreTM
        from lee.orchestrator.execution import TemplateManager as LeeTM

    assert FlowcoreTM is LeeTM


def test_flowcore_engines_redirect():
    """测试 flowcore.engines 重定向到 lee.orchestrator.execution"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from flowcore.engines import ExecutorFactory as FlowcoreEF
        from lee.orchestrator.execution import ExecutorFactory as LeeEF

    assert FlowcoreEF is LeeEF


def test_flowcore_imports_work():
    """测试 flowcore 导入功能正常（即使显示警告）"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import flowcore
        from flowcore import orchestrator
        from flowcore import engines
        from flowcore import utils

    assert hasattr(flowcore, '__version__')
    assert hasattr(orchestrator, 'TemplateManager')
    assert hasattr(engines, 'ExecutorFactory')
