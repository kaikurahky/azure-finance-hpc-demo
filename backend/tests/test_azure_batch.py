import unittest
from unittest.mock import MagicMock, patch

from backend.src.azure_batch import AzureBatchSimulationService
from backend.src.config import Settings
from backend.src.models import SimulationRequest


class AzureBatchSimulationServiceTests(unittest.TestCase):
    def test_routes_jobs_to_the_selected_pool(self) -> None:
        settings = Settings(
            execution_mode="azure",
            azure_batch_account_url="https://example.japaneast.batch.azure.com",
            azure_batch_autoscale_pool_id="autoscale-pool",
            azure_batch_always_on_pool_id="always-on-pool",
        )
        service = AzureBatchSimulationService(settings)
        client = MagicMock()

        with patch.object(service, "_client", return_value=client):
            for pool_mode, expected_pool_id in (
                ("autoscale", "autoscale-pool"),
                ("always-on", "always-on-pool"),
            ):
                with self.subTest(pool_mode=pool_mode):
                    job = service.create(
                        SimulationRequest(
                            pool_mode=pool_mode,
                            paths=100_000,
                            target_nodes=1,
                        )
                    )

                    batch_job = client.job.add.call_args.args[0]
                    self.assertEqual(batch_job.pool_info.pool_id, expected_pool_id)
                    self.assertEqual(job.pool_mode, pool_mode)
                    self.assertIn(f'"poolId": "{expected_pool_id}"', job.error or "")

    def test_all_iterations_wait_before_running_batch_tasks(self) -> None:
        settings = Settings(
            execution_mode="azure",
            azure_batch_account_url="https://example.japaneast.batch.azure.com",
            azure_batch_autoscale_pool_id="autoscale-pool",
            azure_batch_always_on_pool_id="always-on-pool",
            batch_task_delay_seconds=180,
        )
        service = AzureBatchSimulationService(settings)
        client = MagicMock()

        with patch.object(service, "_client", return_value=client):
            for iteration in (1, 2):
                with self.subTest(iteration=iteration):
                    service.create(
                        SimulationRequest(
                            paths=100_000,
                            target_nodes=1,
                            iteration=iteration,
                        )
                    )

                    tasks = client.task.add_collection.call_args.args[1]
                    self.assertEqual(len(tasks), 1)
                    self.assertIn('sleep 180 && python3 -c', tasks[0].command_line)


if __name__ == "__main__":
    unittest.main()
