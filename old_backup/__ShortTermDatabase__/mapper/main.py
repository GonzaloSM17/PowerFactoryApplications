"""
Build de main
"""

from mapper.pipelines.sh_term_orchestrating import ShTermVectorOrchestrator


if __name__ == "__main__":

    scenarios = [
        "E1", "E2", "E3",
        "E4",
        "E5", "E6", "E7", "E8", "E5B", "E6B"
    ]

    for scenario in scenarios:
        orchestrator = ShTermVectorOrchestrator(scenario)
        orchestrator.execute()
