from .models import AiSimulationCandidate, JobStatus, SimulationJob


def infer_next_candidate(job: SimulationJob) -> AiSimulationCandidate:
    if job.status != JobStatus.COMPLETED or job.result is None:
        raise ValueError("完了したシミュレーションだけがAI候補生成の対象です")

    best = min(
        job.result.recommendations,
        key=lambda recommendation: recommendation.verified_loss_billion_yen,
    )
    reduction_ratio = 1 - (
        best.verified_loss_billion_yen / job.result.baseline_loss_billion_yen
    )
    hedge_ratio = round(min(45.0, max(15.0, reduction_ratio * 100)), 1)
    volatility_scale = 0.9 if job.result.expected_shortfall_billion_yen > 100 else 0.95
    predicted_loss = (
        job.result.baseline_loss_billion_yen
        * volatility_scale
        * (1 - hedge_ratio / 100 * 0.8)
    )

    return AiSimulationCandidate(
        source_job_id=job.id,
        scenario=job.scenario,
        paths=job.total_paths,
        target_nodes=10,
        pool_mode=job.pool_mode,
        volatility_scale=volatility_scale,
        hedge_ratio_percent=hedge_ratio,
        predicted_loss_billion_yen=round(predicted_loss, 1),
        selected_strategy=best.name,
        reasoning=(
            f"1回目のExpected Shortfallと「{best.name}」のHPC検証値を基に、"
            f"ヘッジ比率{hedge_ratio:.1f}%、ボラティリティ倍率"
            f"{volatility_scale:.2f}を次の探索点として選択しました。"
        ),
    )
