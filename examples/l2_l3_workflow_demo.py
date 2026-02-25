"""
L2/L3 Workflow System - End-to-End Demo

This script demonstrates the complete L2/L3 workflow system with:
1. L2 template with 5 phases
2. L3 template with 6 steps
3. Complexity-based routing (S/M/L)
4. PMA task splitting
5. Phase dependency resolution
6. Progress tracking
"""

import asyncio
from pathlib import Path
from datetime import datetime

from lee.orchestrator.storage.models import Complexity, Point, WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.pm_agent.split_cache import SplitCache
from lee.orchestrator.core.workflow_generator import (
    WorkflowGenerator,
    L2InstanceConfig,
    L3InstanceConfig,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def demo_template_system():
    """Demo: Template parsing and L2/L3 instance generation."""
    print_section("1. Template System Demo")

    from lee.orchestrator.execution.template_manager import TemplateManager

    # Path to templates
    project_root = Path("/Users/zengle/git/ai/lee")
    template_dir = project_root / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates"

    tm = TemplateManager(template_dir=str(template_dir))

    # Load L2 template
    print("\n🔹 Loading L2 Template...")
    l2_template = tm.get_template("template.dev.feature_l2")
    if l2_template:
        print(f"   ✓ L2 Template: {l2_template.name}")
        print(f"   ✓ Phases: {len(l2_template.steps)}")
        for step in l2_template.steps:
            print(f"     - {step.id}: {step.config.get('default_complexity')}")
    else:
        # Try loading from content
        l2_path = template_dir / "feature-l2-template.yaml"
        if l2_path.exists():
            l2_template = tm.load_template_from_content(l2_path.read_text(), "template.dev.feature_l2")
            print(f"   ✓ L2 Template: {l2_template.name}")

    # Load L3 template
    print("\n🔹 Loading L3 Template...")
    l3_path = template_dir / "task-l3-template.yaml"
    if l3_path.exists():
        l3_template = tm.load_template_from_content(l3_path.read_text(), "template.dev.task_l3")
        print(f"   ✓ L3 Template: {l3_template.name}")
        print(f"   ✓ Steps: {len(l3_template.steps)}")
        for step in l3_template.steps:
            print(f"     - {step.id}: {step.kind}")


async def demo_l2_instance_generation():
    """Demo: Generate L2 instance from template."""
    print_section("2. L2 Instance Generation")

    project_root = Path("/Users/zengle/git/ai/lee")
    template_base = project_root / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates"
    instance_base = project_root / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "instances"

    generator = WorkflowGenerator(template_path=str(template_base / "feature-l2-template.yaml"))

    config = L2InstanceConfig(
        id="instance.demo.user_profile_v1",
        name="User Profile Feature",
        project="Demo App",
        module="user_profile",
        module_version="v1",
        prd_path="specs/user-profile.md",
        repos=[
            {"id": "fe-repo", "type": "frontend", "url": "github.com/app/fe", "branch": "main"},
            {"id": "be-repo", "type": "backend", "url": "github.com/app/be", "branch": "main"},
        ],
        phase_complexities={
            "plan": "S",
            "api_align": "M",
            "frontend_dev": "L",  # Will trigger PMA split
            "backend_dev": "L",  # Will trigger PMA split
            "integration": "S",
        }
    )

    result = generator.generate_l2_instance(config, str(instance_base / "l2/demo-user-profile.yaml"))
    print(f"\n✓ L2 Instance Generated: {result.generated_workflow['id']}")
    print(f"  ✓ Name: {result.generated_workflow['name']}")
    print(f"  ✓ Phases: {len(result.generated_workflow['phases'])}")

    for phase in result.generated_workflow['phases']:
        complexity = phase['complexity']
        print(f"    - {phase['id']}: complexity={complexity}")


async def demo_complexity_levels():
    """Demo: Complexity enum and Point dataclass."""
    print_section("3. Complexity & Point Models")

    print("\n🔹 Complexity Levels:")
    for comp in [Complexity.S, Complexity.M, Complexity.L]:
        strategy = {
            Complexity.S: "Direct execution",
            Complexity.M: "Single L3",
            Complexity.L: "PMA split → Multiple L3s"
        }
        print(f"  - {comp.value}: {strategy[comp]}")

    print("\n🔹 Point Dataclass:")
    point = Point(
        id="frontend_dev-p1",
        title="Build User Profile Page",
        desc="Implement user profile UI with avatar and bio",
        layer="ui",
        estimated_complexity=Complexity.M,
        files_hint=["src/pages/UserProfile.vue", "src/components/Avatar.vue"],
        depends_on=[]
    )
    print(f"  - ID: {point.id}")
    print(f"  - Title: {point.title}")
    print(f"  - Layer: {point.layer}")
    print(f"  - Complexity: {point.estimated_complexity.value}")
    print(f"  - Files: {point.files_hint}")


async def demo_phase_dependencies():
    """Demo: Phase dependency resolution."""
    print_section("4. Phase Dependency Resolution")

    from unittest.mock import Mock
    from lee.orchestrator.storage.models import WorkflowInstance

    orch = Orchestrator(store=Mock(), project_root=str(Path.cwd()))

    # Create L2 instance with phase dependencies
    data = {
        "kind": "l2_workflow_instance",
        "phases": [
            {"id": "plan", "status": "completed", "complexity": "S", "depends_on": []},
            {"id": "api_align", "status": "pending", "complexity": "M", "depends_on": ["plan"]},
            {"id": "frontend_dev", "status": "pending", "complexity": "L", "depends_on": ["api_align"]},
            {"id": "backend_dev", "status": "pending", "complexity": "L", "depends_on": ["api_align"]},
            {"id": "integration", "status": "pending", "complexity": "S", "depends_on": ["frontend_dev", "backend_dev"]},
        ]
    }

    instance = WorkflowInstance(
        id="l2-demo",
        level=WorkflowLevel.DEPARTMENT,
        template_id="template.dev.feature_l2",
        status=WorkflowStatus.RUNNING,
        data=data,
    )

    print("\n🔹 Phase Execution Order:")
    print("  Execution flow based on dependencies:")

    phases_copy = data["phases"].copy()
    completed = []

    while len(completed) < len(data["phases"]):
        next_phase = orch._get_next_pending_phase(instance)
        if next_phase:
            completed.append(next_phase["id"])
            print(f"  {len(completed)}. {next_phase['id']} (complexity={next_phase['complexity']})")
            # Update status
            for p in data["phases"]:
                if p["id"] == next_phase["id"]:
                    p["status"] = "completed"
            instance.data["phases"] = data["phases"]
        else:
            break

    print("\n🔹 Parallel Execution Opportunity:")
    ready = orch._get_ready_phases(instance)
    # Reset state for demo
    for p in data["phases"]:
        if p["id"] in ["frontend_dev", "backend_dev"]:
            p["status"] = "pending"
    instance.data["phases"] = data["phases"]

    ready = orch._get_ready_phases(instance)
    ready_ids = [p["id"] for p in ready]
    print(f"  Phases that can run in parallel after api_align: {ready_ids}")


async def demo_point_grouping():
    """Demo: Point grouping for parallel L3 execution."""
    print_section("5. Point Grouping for Parallel Execution")

    from unittest.mock import Mock

    orch = Orchestrator(store=Mock(), project_root=str(Path.cwd()))

    # Create points with dependencies
    points = [
        Point(id="p1", title="Foundation", desc="Base setup", layer="ui", estimated_complexity=Complexity.M, depends_on=[]),
        Point(id="p2", title="Component A", desc="Feature A", layer="ui", estimated_complexity=Complexity.M, depends_on=["p1"]),
        Point(id="p3", title="Component B", desc="Feature B", layer="ui", estimated_complexity=Complexity.M, depends_on=["p1"]),
        Point(id="p4", title="Integration", desc="Combine A and B", layer="ui", estimated_complexity=Complexity.S, depends_on=["p2", "p3"]),
    ]

    groups = orch._group_points_by_dependency(points)

    print("\n🔹 Execution Groups (topological order):")
    for i, group in enumerate(groups, 1):
        group_ids = [p.id for p in group]
        print(f"  Group {i}: {group_ids} (can run in parallel)")


async def demo_split_cache():
    """Demo: PMA split result caching."""
    print_section("6. PMA Split Result Caching")

    import tempfile
    cache_dir = tempfile.mkdtemp()

    cache = SplitCache(cache_dir=cache_dir)

    # Create sample points
    points = [
        Point(id="phase1-p1", title="Point 1", desc="Description 1", layer="ui", estimated_complexity=Complexity.M),
        Point(id="phase1-p2", title="Point 2", desc="Description 2", layer="ui", estimated_complexity=Complexity.M),
    ]

    # Store in cache
    cache.set(
        phase_id="phase1",
        phase_description="Implement UI",
        prd_content="Build user interface...",
        repo_context={"type": "frontend", "language": "vue"},
        points=points,
        metadata={"confidence": 0.9, "original_estimate": "8h", "split_estimate": "6h"}
    )

    # Retrieve from cache
    cached = cache.get("phase1", "Implement UI", "Build user interface...", {"type": "frontend", "language": "vue"})

    print("\n🔹 Cache Operations:")
    print(f"  ✓ Stored {len(points)} points in cache")
    print(f"  ✓ Retrieved {len(cached)} points from cache")
    print(f"  ✓ Cache hit: same points returned")

    stats = cache.get_stats()
    print(f"\n🔹 Cache Statistics:")
    print(f"  - Total entries: {stats['total_entries']}")
    print(f"  - Total size: {stats['total_size_bytes']} bytes")

    # Cleanup
    import shutil
    shutil.rmtree(cache_dir, ignore_errors=True)


async def demo_quality_validation():
    """Demo: Split quality validation."""
    print_section("7. Split Quality Validation")

    from lee.orchestrator.execution.pm_agent.task_splitter import SimpleTaskSplitter

    splitter = SimpleTaskSplitter(llm_executor=None)

    # Good split
    good_points = [
        Point(id="p1", title="Design Layout", desc="Create detailed UI mockups", layer="ui", estimated_complexity=Complexity.M),
        Point(id="p2", title="Build Components", desc="Implement Vue components", layer="ui", estimated_complexity=Complexity.M),
        Point(id="p3", title="Wire State", desc="Add Pinia state management", layer="state", estimated_complexity=Complexity.M),
    ]

    result = splitter._validate_split_quality(good_points)
    print(f"\n🔹 Good Split Quality:")
    print(f"  - Valid: {result['is_valid']}")
    print(f"  - Score: {result['score']}/100")
    print(f"  - Errors: {len(result['errors'])}")
    print(f"  - Warnings: {len(result['warnings'])}")

    # Poor split
    poor_points = [
        Point(id="x", title="X", desc="X", layer="invalid", estimated_complexity=Complexity.L),
    ]

    result = splitter._validate_split_quality(poor_points)
    print(f"\n🔹 Poor Split Quality:")
    print(f"  - Valid: {result['is_valid']}")
    print(f"  - Score: {result['score']}/100")
    print(f"  - Errors: {result['errors']}")


async def demo_progress_tracking():
    """Demo: L2 progress tracking."""
    print_section("8. L2 Progress Tracking")

    from unittest.mock import Mock, AsyncMock
    from lee.orchestrator.storage.models import WorkflowInstance

    mock_store = Mock()
    mock_store.get_workflow = AsyncMock()

    data = {
        "kind": "l2_workflow_instance",
        "phases": [
            {"id": "plan", "status": "completed", "complexity": "S", "l3_instance_ids": []},
            {"id": "api_align", "status": "completed", "complexity": "M", "l3_instance_ids": ["l3-1"]},
            {"id": "frontend_dev", "status": "running", "complexity": "L", "l3_instance_ids": ["l3-2", "l3-3"]},
            {"id": "backend_dev", "status": "pending", "complexity": "L", "l3_instance_ids": []},
            {"id": "integration", "status": "pending", "complexity": "S", "l3_instance_ids": []},
        ]
    }

    instance = WorkflowInstance(
        id="l2-progress",
        level=WorkflowLevel.DEPARTMENT,
        template_id="template.dev.feature_l2",
        status=WorkflowStatus.RUNNING,
        data=data,
    )
    mock_store.get_workflow.return_value = instance

    orch = Orchestrator(store=mock_store, project_root=str(Path.cwd()))
    progress = await orch.get_l2_progress("l2-progress")

    print(f"\n🔹 L2 Workflow Progress:")
    print(f"  - Overall: {progress['progress_percent']}% complete")
    print(f"  - Phases: {progress['phases']['completed']}/{progress['phases']['total']} completed")
    print(f"  - L3s: {progress['l3_instances']['completed']}/{progress['l3_instances']['total']} completed")

    print(f"\n🔹 Phase Details:")
    for p in progress['phase_details']:
        status_icon = {"completed": "✓", "running": "▶", "pending": "○"}.get(p['status'], "?")
        print(f"  {status_icon} {p['id']}: complexity={p['complexity']}, l3s={p['l3_count']}")


async def main():
    """Run all demos."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║     L2/L3 Workflow System - End-to-End Demo              ║")
    print("╚════════════════════════════════════════════════════════════╝")

    await demo_template_system()
    await demo_l2_instance_generation()
    await demo_complexity_levels()
    await demo_phase_dependencies()
    await demo_point_grouping()
    await demo_split_cache()
    await demo_quality_validation()
    await demo_progress_tracking()

    print_section("Demo Complete")
    print("\n✅ All demos completed successfully!")
    print("\nNext Steps:")
    print("  1. Run actual L2 workflow with orchestrator.run_until_blocked()")
    print("  2. Integrate with real LLM for PMA splitting")
    print("  3. Add actual L3 execution with agent runners")
    print()


if __name__ == "__main__":
    asyncio.run(main())
