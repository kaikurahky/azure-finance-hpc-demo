# Azure Finance HPC Demo

金融市場ショックを題材に、Azure BatchによるMonte Carlo並列計算とAIサロゲートモデルによるヘッジ探索を可視化するライブデモです。

## 構成

- `frontend/`: React + TypeScript + Vite
- `backend/`: FastAPI、ローカル疑似実行、Azure Batchジョブ制御

## ローカル実行

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

別のターミナルで:

```bash
cd frontend
npm install
npm run dev
```

ブラウザーで `http://localhost:5173` を開きます。既定ではAzure資格情報なしで動作するローカル疑似実行モードです。

## Azure Batchモード

`.env.sample`を参考にBatchアカウント、キー、既存プールIDを設定し、`EXECUTION_MODE=azure`でAPIを起動します。秘密情報はソース管理しないでください。

## ヘルスチェック

- `GET /healthz`
- `GET /readyz`

