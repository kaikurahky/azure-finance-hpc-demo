import unittest
from datetime import UTC, datetime

from backend.src.ai_candidate import infer_next_candidate
from backend.src.models import JobStatus, ShockScenario, SimulationJob
from backend.src.simulation import _adjusted_baseline, _build_result


class AiCandidateTests(unittest.TestCase):
    def test_infers_bounded_candidate_for_second_batch_run(self) -> None:
        now = datetime.now(UTC)
        job = SimulationJob(
            id="first-job",
            scenario=ShockScenario.LEHMAN,
            execution_mode="azure",
            status=JobStatus.COMPLETED,
            progress=100,
            active_nodes=0,
            completed_paths=5_000_000,
            total_paths=5_000_000,
            target_nodes=10,
            iteration=1,
            volatility_scale=1.0,
            hedge_ratio_percent=0.0,
            created_at=now,
            updated_at=now,
            result=_build_result(124.0, 60.0, 5_000_000),
        )

        candidate = infer_next_candidate(job)

        self.assertEqual(candidate.source_job_id, job.id)
        self.assertEqual(candidate.target_nodes, 10)
        self.assertEqual(candidate.volatility_scale, 0.9)
        self.assertEqual(candidate.hedge_ratio_percent, 45.0)
        self.assertLess(
            candidate.predicted_loss_billion_yen,
            job.result.baseline_loss_billion_yen,
        )

    def test_rejects_incomplete_job(self) -> None:
        now = datetime.now(UTC)
        job = SimulationJob(
            id="running-job",
            scenario=ShockScenario.LEHMAN,
            execution_mode="azure",
            status=JobStatus.RUNNING,
            progress=50,
            active_nodes=10,
            completed_paths=2_500_000,
            total_paths=5_000_000,
            target_nodes=10,
            iteration=1,
            volatility_scale=1.0,
            hedge_ratio_percent=0.0,
            created_at=now,
            updated_at=now,
        )

        with self.assertRaises(ValueError):
            infer_next_candidate(job)

    def test_adjusted_baseline_applies_ai_parameters(self) -> None:
        adjusted = _adjusted_baseline(
            baseline=124.0,
            volatility_scale=0.9,
            hedge_ratio_percent=45.0,
        )

        self.assertAlmostEqual(adjusted, 71.424)


if __name__ == "__main__":
    unittest.main()
