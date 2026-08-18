import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  CloudCog,
  Gauge,
  Network,
  Play,
  ShieldCheck,
  Sparkles,
  TimerReset,
  TrendingDown,
  Zap,
} from "lucide-react";
import { formatPathCount } from "./format";

type Mode = "local" | "azure";
type Scenario = "lehman" | "yen-surge" | "rate-spike" | "custom";
type JobStatus = "queued" | "scaling" | "running" | "verifying" | "completed" | "failed";

interface RuntimeConfig {
  default_execution_mode: Mode;
  azure_batch_configured: boolean;
  azure_batch_pool_id: string;
  missing_azure_settings: string[];
}

interface Recommendation {
  name: string;
  predicted_loss_billion_yen: number;
  verified_loss_billion_yen: number;
  error_percent: number;
  hedge_cost_billion_yen: number;
}

interface SimulationJob {
  id: string;
  execution_mode: Mode;
  iteration: number;
  parent_job_id: string | null;
  status: JobStatus;
  progress: number;
  active_nodes: number;
  completed_paths: number;
  total_paths: number;
  target_nodes: number;
  volatility_scale: number;
  hedge_ratio_percent: number;
  error: string | null;
  result: null | {
    baseline_loss_billion_yen: number;
    value_at_risk_billion_yen: number;
    expected_shortfall_billion_yen: number;
    elapsed_seconds: number;
    estimated_legacy_seconds: number;
    estimated_cost_yen: number;
    evaluations_per_second: number;
    recommendations: Recommendation[];
    loss_contributors: Record<string, number>;
  };
}

interface AiSimulationCandidate {
  source_job_id: string;
  scenario: Scenario;
  paths: number;
  target_nodes: number;
  volatility_scale: number;
  hedge_ratio_percent: number;
  predicted_loss_billion_yen: number;
  selected_strategy: string;
  reasoning: string;
}

const scenarios: { id: Scenario; label: string; detail: string; loss: string }[] = [
  { id: "lehman", label: "複合市場ショック", detail: "株式 -12% / 金利 +150bp", loss: "-124億円" },
  { id: "yen-surge", label: "急激な円高", detail: "USD/JPY -14% / 相関上昇", loss: "-89億円" },
  { id: "rate-spike", label: "金利急騰", detail: "イールドカーブ +180bp", loss: "-97億円" },
];

const statusLabels: Record<JobStatus, string> = {
  queued: "キュー投入",
  scaling: "HPCノード増強中",
  running: "Monte Carlo実行中",
  verifying: "AI提案を厳密検証中",
  completed: "分析完了",
  failed: "実行失敗",
};

export function App() {
  const [scenario, setScenario] = useState<Scenario>("lehman");
  const [mode, setMode] = useState<Mode>("local");
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [job, setJob] = useState<SimulationJob | null>(null);
  const [firstJob, setFirstJob] = useState<SimulationJob | null>(null);
  const [candidate, setCandidate] = useState<AiSimulationCandidate | null>(null);
  const [candidateAttemptedJobId, setCandidateAttemptedJobId] = useState("");
  const [candidateSubmitting, setCandidateSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<"dashboard" | "architecture">("dashboard");

  useEffect(() => {
    fetch("/api/config")
      .then((response) => response.json())
      .then((data: RuntimeConfig) => {
        setConfig(data);
        setMode(data.default_execution_mode);
      })
      .catch(() => setError("APIに接続できません。FastAPIを起動してください。"));
  }, []);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`/api/simulations/${job.id}`);
      if (response.ok) setJob(await response.json());
    }, job.execution_mode === "azure" ? 5_000 : 500);
    return () => window.clearInterval(timer);
  }, [job]);

  useEffect(() => {
    if (
      !job ||
      job.execution_mode !== "azure" ||
      job.iteration !== 1 ||
      job.status !== "completed" ||
      candidateAttemptedJobId === job.id
    ) {
      return;
    }

    setCandidateAttemptedJobId(job.id);
    fetch(`/api/simulations/${job.id}/next-candidate`, { method: "POST" })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail ?? "AI候補の推論に失敗しました。");
        setCandidate(body);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [candidateAttemptedJobId, job]);

  async function runSimulation() {
    setError("");
    setJob(null);
    setFirstJob(null);
    setCandidate(null);
    setCandidateAttemptedJobId("");
    const response = await fetch("/api/simulations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario, paths: 5_000_000, target_nodes: 10, execution_mode: mode }),
    });
    const body = await response.json();
    if (!response.ok) {
      setError(body.detail ?? "ジョブの投入に失敗しました。");
      return;
    }
    setJob(body);
  }

  async function runAiCandidate() {
    if (!candidate || !job?.result || candidateSubmitting) return;

    setError("");
    const sourceJob = job;
    setCandidateSubmitting(true);
    try {
      const response = await fetch("/api/simulations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario: candidate.scenario,
          paths: candidate.paths,
          target_nodes: candidate.target_nodes,
          execution_mode: "azure",
          iteration: 2,
          parent_job_id: candidate.source_job_id,
          volatility_scale: candidate.volatility_scale,
          hedge_ratio_percent: candidate.hedge_ratio_percent,
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        setError(body.detail ?? "2回目のAzure Batchジョブ投入に失敗しました。");
        return;
      }
      setFirstJob(sourceJob);
      setJob(body);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "2回目のAzure Batchジョブ投入に失敗しました。");
    } finally {
      setCandidateSubmitting(false);
    }
  }

  if (view === "architecture") {
    return <ArchitectureView onBack={() => setView("dashboard")} config={config} />;
  }

  const running = job && !["completed", "failed"].includes(job.status);
  const result = job?.result;

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><TrendingDown size={21} /></div>
          <div><strong>MARKET SHOCK</strong><span>WAR ROOM</span></div>
        </div>
        <div className="header-actions">
          <button className="text-button" onClick={() => setView("architecture")}><Network size={16} />構成を見る</button>
          <span className="live-badge"><i /> LIVE DEMO</span>
          <span className="azure-badge"><CloudCog size={16} /> Microsoft Azure</span>
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">FINANCIAL HPC × AI COMMAND CENTER</p>
          <h1>Azure Risk Simulation Portal</h1>
          <p className="lead">500万シナリオを並列評価。AIが対策を探索し、Azure HPCがその正しさを検証します。</p>
        </div>
        <div className="portfolio-card">
          <span>分析対象ポートフォリオ</span>
          <strong>¥ 2.84<span>兆円</span></strong>
          <div><span>100,000 ポジション</span><span>4 アセットクラス</span></div>
        </div>
      </section>

      <section className="control-grid">
        <div className="panel scenario-panel">
          <PanelTitle number="01" title="市場ショックを選択" icon={<Activity />} />
          <div className="scenario-list">
            {scenarios.map((item) => (
              <button key={item.id} className={scenario === item.id ? "scenario active" : "scenario"} onClick={() => setScenario(item.id)}>
                <div className="radio"><i /></div>
                <div><strong>{item.label}</strong><span>{item.detail}</span></div>
                <b>{item.loss}</b>
              </button>
            ))}
          </div>
        </div>

        <div className="panel launch-panel">
          <PanelTitle number="02" title="計算モード" icon={<CloudCog />} />
          <div className="mode-switch">
            <button className={mode === "local" ? "selected" : ""} onClick={() => setMode("local")}>
              <Gauge /><strong>Local Cluster</strong><span>デモ用・資格情報不要</span>
            </button>
            <button className={mode === "azure" ? "selected" : ""} onClick={() => setMode("azure")}>
              <Zap /><strong>Azure Batch</strong><span>{config?.azure_batch_configured ? "実リソースで実行" : "Azure設定が必要"}</span>
            </button>
          </div>
          <div className="workload">
            <div><span>Monte Carlo</span><b>5,000,000</b></div>
            <div><span>目標ノード</span><b>10</b></div>
            <div><span>従来所要時間</span><b>4h 20m</b></div>
          </div>
          <button className="run-button" disabled={Boolean(running)} onClick={runSimulation}>
            {running ? <><Activity className="spin" /> 分析を実行中...</> : <><Play fill="currentColor" /> 緊急リスク分析を開始 <ChevronRight /></>}
          </button>
          {error && <p className="error">{error}</p>}
        </div>
      </section>

      <section className="panel execution-panel">
        <PanelTitle number="03" title="HPC実行状況" icon={<Zap />} />
        <div className="execution">
          <div className="progress-column">
            <div className="status-line">
              <span className={job ? "pulse" : "idle-dot"} />
              <strong>{job ? statusLabels[job.status] : "実行待機中"}</strong>
              <b>{job?.progress ?? 0}%</b>
            </div>
            <div className="progress-track"><i style={{ width: `${job?.progress ?? 0}%` }} /></div>
            <div className="progress-meta">
              <span>{formatPathCount(job?.completed_paths ?? 0)} / {formatPathCount(job?.total_paths ?? 5_000_000)} paths</span>
              <span>{job?.execution_mode === "azure" ? `Azure Batch 第${job.iteration}回` : "Local Cluster"}</span>
            </div>
          </div>
          <Metric icon={<Network />} label="ACTIVE NODES" value={`${job?.active_nodes ?? 0}`} unit="/ 10" accent />
          <Metric icon={<Gauge />} label="THROUGHPUT" value={result ? `${Math.round(result.evaluations_per_second / 1000)}K` : job ? `${Math.max(12, job.progress * 13)}K` : "0"} unit="eval/s" />
          <Metric icon={<CircleDollarSign />} label="EST. COST" value={`¥${result?.estimated_cost_yen.toLocaleString() ?? Math.round((job?.progress ?? 0) * 12)}`} unit="" />
        </div>
      </section>

      <section className="results-grid">
        <div className="panel risk-panel">
          <PanelTitle number="04" title="リスク評価" icon={<ShieldCheck />} />
          <div className="risk-values">
            <div><span>想定損失</span><strong>-¥{result?.baseline_loss_billion_yen ?? "—"}<small>億</small></strong></div>
            <div><span>99% VaR</span><strong>-¥{result?.value_at_risk_billion_yen ?? "—"}<small>億</small></strong></div>
            <div><span>Expected Shortfall</span><strong>-¥{result?.expected_shortfall_billion_yen ?? "—"}<small>億</small></strong></div>
          </div>
          <div className="contributors">
            <span>損失寄与度</span>
            {Object.entries(result?.loss_contributors ?? { 株式: 42, 金利: 27, 為替: 19, クレジット: 12 }).map(([name, value]) => (
              <div key={name}><label>{name}</label><i><b style={{ width: `${result ? value : 0}%` }} /></i><strong>{result ? value : 0}%</strong></div>
            ))}
          </div>
        </div>

        <div className="panel ai-panel">
          <PanelTitle number="05" title="AIヘッジ提案 × HPC検証" icon={<Bot />} />
          <div className="ai-note"><Sparkles size={16} />サロゲートモデルが候補を探索し、厳密計算で再検証</div>
          <div className="recommendations">
            {(result?.recommendations ?? []).map((rec, index) => (
              <div className="recommendation" key={rec.name}>
                <span className="rank">0{index + 1}</span>
                <div><strong>{rec.name}</strong><span>AI予測 -¥{rec.predicted_loss_billion_yen.toFixed(1)}億</span></div>
                <div className="verified"><CheckCircle2 /><span>HPC検証</span><strong>-¥{rec.verified_loss_billion_yen.toFixed(1)}億</strong></div>
                <small>誤差 {rec.error_percent}%</small>
              </div>
            ))}
            {!result && <div className="empty-state"><Bot /><strong>分析後にAI提案を表示</strong><span>候補生成 → 並列検証 → 最適案を比較</span></div>}
          </div>
          {candidate && (
            <div className="ai-candidate">
              <div className="candidate-heading"><Sparkles /><span>AI NEXT PARAMETER</span><b>READY</b></div>
              <strong>{candidate.selected_strategy}を次の探索点へ</strong>
              <p>{candidate.reasoning}</p>
              <div className="candidate-parameters">
                <span>HEDGE<b>{candidate.hedge_ratio_percent.toFixed(1)}%</b></span>
                <span>VOL SCALE<b>{candidate.volatility_scale.toFixed(2)}</b></span>
                <span>NODES<b>{candidate.target_nodes}</b></span>
                <span>PRED. LOSS<b>-¥{candidate.predicted_loss_billion_yen.toFixed(1)}億</b></span>
              </div>
              {job?.id === candidate.source_job_id && (
                <button className="candidate-button" disabled={candidateSubmitting} onClick={runAiCandidate}>
                  {candidateSubmitting ? <Activity className="spin" /> : <Zap />}
                  {candidateSubmitting ? "2回目のジョブを投入中..." : "AI候補で2回目のAzure Batchを実行"}
                  {!candidateSubmitting && <ChevronRight />}
                </button>
              )}
              {job?.iteration === 2 && !["completed", "failed"].includes(job.status) && (
                <div className="candidate-status"><Activity className="spin" />2回目のHPC厳密検証を実行中</div>
              )}
              {job?.iteration === 2 && job.status === "failed" && (
                <div className="candidate-status error"><Zap />2回目の検証に失敗: {job.error ?? "Batchジョブを確認してください。"}</div>
              )}
              {job?.iteration === 2 && job.status === "completed" && firstJob?.result && result && (
                <div className="candidate-comparison">
                  <CheckCircle2 />
                  <span>2回目の検証完了</span>
                  <strong>
                    VaR -¥{firstJob.result.value_at_risk_billion_yen.toFixed(1)}億
                    <em> → </em>
                    -¥{result.value_at_risk_billion_yen.toFixed(1)}億
                  </strong>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <section className={result ? "impact visible" : "impact"}>
        <div><TimerReset /><span>意思決定時間</span><strong>4時間20分 <em>→</em> {result?.elapsed_seconds}秒</strong></div>
        <div><TrendingDown /><span>推奨策による損失削減</span><strong>最大 <em>¥{result ? (result.baseline_loss_billion_yen - result.recommendations[2].verified_loss_billion_yen).toFixed(1) : 0}億</em></strong></div>
        <div><CircleDollarSign /><span>今回の計算コスト</span><strong><em>¥{result?.estimated_cost_yen.toLocaleString() ?? 0}</em></strong></div>
      </section>

      <footer><span>Azure Batch</span><i /> <span>FastAPI</span><i /> <span>React</span><i /> <span>HPC + AI</span><b>DEMO DATA / NOT FOR TRADING</b></footer>
    </main>
  );
}

function PanelTitle({ number, title, icon }: { number: string; title: string; icon: React.ReactNode }) {
  return <div className="panel-title"><span>{number}</span>{icon}<h2>{title}</h2></div>;
}

function Metric({ icon, label, value, unit, accent = false }: { icon: React.ReactNode; label: string; value: string; unit: string; accent?: boolean }) {
  return <div className={accent ? "metric accent" : "metric"}>{icon}<div><span>{label}</span><strong>{value}<small>{unit}</small></strong></div></div>;
}

function ArchitectureView({ onBack, config }: { onBack: () => void; config: RuntimeConfig | null }) {
  const components = [
    ["React Dashboard", "市場シナリオ・進捗・結果をリアルタイム表示"],
    ["FastAPI Control Plane", "ジョブ投入、状態管理、実行モード切替"],
    ["Azure Batch", "Monte Carloタスクを計算ノードへ並列配置"],
    ["HPC VM Pool", "需要時にスケールし、完了後にゼロへ縮退"],
    ["AI Surrogate", "ヘッジ候補を高速探索しHPCへ検証依頼"],
  ];
  return (
    <main>
      <header className="topbar"><div className="brand"><div className="brand-mark"><Network /></div><div><strong>DEMO ARCHITECTURE</strong><span>AZURE HPC × AI</span></div></div><button className="text-button" onClick={onBack}>← ダッシュボードへ戻る</button></header>
      <section className="architecture-page">
        <p className="eyebrow">REFERENCE FLOW</p><h1>意思決定までを、ひとつの計算パイプラインに。</h1>
        <div className="architecture-flow">
          {components.map(([title, detail], index) => <div className="architecture-node" key={title}><span>0{index + 1}</span><strong>{title}</strong><p>{detail}</p>{index < components.length - 1 && <ChevronRight />}</div>)}
        </div>
        <div className="config-card"><CloudCog /><div><span>現在の実行先</span><strong>{config?.azure_batch_configured ? "Azure Batch接続準備完了" : "Local Cluster"}</strong><p>Pool: {config?.azure_batch_pool_id ?? "finance-hpc-pool"}</p></div><b className={config?.azure_batch_configured ? "ready" : ""}>{config?.azure_batch_configured ? "READY" : "CONFIG REQUIRED"}</b></div>
      </section>
    </main>
  );
}
