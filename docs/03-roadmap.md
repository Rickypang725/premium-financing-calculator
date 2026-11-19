# 03 — 路線圖與驗收標準（Roadmap & Acceptance）

&gt; 執行原則：一個里程碑做完、驗收過了，再進下一個。每個 milestone 結束時 `git tag m&lt;N&gt;-complete`。
&gt; 平台相關內容已按 ADR-8 修訂（2026-11-19）：GCP Cloud Run → AWS ECS Fargate。

## M0 — 計算引擎 ✅（2026-11 完成）

**任務**：實作 `src/pfpro/engine.py`，使 `pytest tests/ -v` 全綠。

內容：
- `solve_irr(cashflows) -&gt; float | None`：年化 IRR 求解；無正負號變化回傳 `None`。
- `effective_rate(hibor_1m, h_spread, prime_rate, p_spread) -&gt; float`：`min(H+h_spread, P−p_spread)`。
- `project(params, table) -&gt; list[Row]`：逐年投影（利息、退保價值、總回報、淨利潤、IRR、現金流），公式見 `02-functional-spec.md` §2。
- `stress_matrix(params, table, rates, ratios, stress_year) -&gt; matrix`：規則見 §4。

**驗收標準**：
1. `pytest` 全綠（含 golden vectors 全部驗證點）。
2. 引擎無第三方依賴（`pip install -e .` 後僅標準函式庫）。
3. 每個函數有 docstring 與型別標註。

## M1 — REST API ✅（2026-11 完成）

**任務**：FastAPI 包裝引擎；`POST /projection`、`POST /stress`、`GET /healthz`；Pydantic 驗證（範圍檢查 + 利益表逐年結構）；回應附免責文案欄位。

**驗收**：
1. `uvicorn` 本地起服，`curl` 三個 endpoint 行為正確（錯誤輸入回 422）。
2. 新增 API 層測試（TestClient），引擎測試不回退。
3. OpenAPI 文件可開（`/docs`）。

## M2a — 容器化（Dockerfile）

**任務**：根目錄 `Dockerfile`：multi-stage build（builder 階段裝依賴，runtime 階段 `python:3.12-slim`）、**非 root 用戶**運行 uvicorn、只暴露 8080。`.dockerignore` 一併建立。

**驗收**：
1. `docker build -t pfpro:m2a .` 成功。
2. `docker run -p 8080:8080` 後 `curl -sf localhost:8080/healthz` 回 200。
3. 容器內執行用戶非 root（`docker exec &lt;cid&gt; id -u` ≠ 0）。
4. 不改動 `src/`、`tests/` 任何檔案；本里程碑無 Terraform。

**建議 commit 順序**：`feat: add multi-stage Dockerfile with non-root runtime` → `chore: add .dockerignore`。

## M2b — AWS 部署（ECS Fargate；依賴 Repo 1 (cloud-lab) M1 完成）

**任務**：`infra/terraform/`：以 **data source 依 tag 查詢** cloud-lab 的 VPC / private subnets / ALB security group（不建任何網路層資源）；定義 ECR 映像檔來源、ECS task definition（Fargate，0.25 vCPU / 0.5 GB 起步）、ECS service 掛載 ALB target group、應用專用 security group（ALB → tasks 精準放行）。

**驗收**：
1. `terraform plan` 輸出存檔，且**不含任何 vpc/subnet/igw 類資源**（發現缺前置資源 → 回報，不補建）。
2. `terraform apply` 真實部署成功（由 Ricky 在本機執行）。
3. `curl &lt;ALB DNS&gt;/healthz` 回 200；`POST /projection` 回傳數字與 golden vectors 一致（跨網路端到端驗證）。
4. 無密鑰進 repo；無長期 Access Key（本機用 SSO/臨時憑證）。

**建議 commit 順序**：`feat: add aws provider + data sources for cloud-lab vpc` → `feat: add ecs task definition and fargate service` → `feat: wire service to cloud-lab ALB target group`。

## M3 — GitHub Actions（OIDC）

**任務**：`.github/workflows/ci.yml`：
- PR：pytest → docker build → tfsec（Terraform 掃描）→ trivy（映像檔漏洞）。
- push main：pytest 綠 → push 映像檔到 ECR → 更新 ECS service。
- AWS 認證用 GitHub OIDC → IAM role；deploy job 初期以 `workflow_dispatch` 手動觸發，Ricky 建好 IAM role 後改為自動。

**驗收**：
1. PR 上 CI 綠燈（pytest + build + tfsec + trivy）。
2. `workflow_dispatch` 手動觸發可完成 ECR push。
3. README 補「IAM role 與 OIDC 設定」章節。

## M4 — React 前端

**任務**：`web/`（Vite + React + TS）：參數表單、KPI 卡（首付/槓桿/貸款額）、年度明細表、壓力矩陣色階表。只呼叫 API，不內嵌計算。

**驗收**：
1. 輸入基準參數，畫面數字與 golden vectors 一致（含 IRR 為「—」的情況）。
2. `npm run build` 成功；API base URL 以環境變數注入。

## M5 — 多雲對比（stretch；不在關鍵路徑）

把 M2a 的同一映像檔部署到 GCP Cloud Run，產出「Fargate vs Cloud Run」對照表（擴縮容模型、計費、網路模型）。屆時再決定是否開 GCP 帳號。

## M6 — AI 分析（stretch；只開 issue 不排期）

AWS Bedrock 讀引擎 JSON 輸出、生成風險提示報告。以「LLM 工作負載工程實踐」立項（prompt 管理、成本控管、輸出驗證），非「AI 功能」。

## 交付後 Ricky 要補做的事（非 agent 範圍）

- Repo 1 (cloud-lab) M1 完成（M2b 的前置依賴）。
- IAM：開 OIDC provider + GitHub Actions 專用 role（M3 需要）。
- README 加截圖、repo description、topics（`aws` `ecs-fargate` `terraform` `fastapi` `premium-financing`）。
- 部署後把 URL 更新到 CV 與求職信。

## 風險與對策

| 風險 | 對策 |
|---|---|
| IRR 求解器在邊界現金流不收斂 | golden tests 已含 null 情況；求解器加迭代上限與越界檢查 |
| Agent 在 infra 代碼「直覺補完」網路資源 | KICKOFF 明寫「只建應用層資源，缺前置就回報」；PR 檢查 plan 有無預期外資源 |
| ap-east-1 成本失控 | task 規格壓到 0.25 vCPU；閒時 `terraform destroy`（Repo 1 已有全毀重建紀錄） |
| 前端與引擎邏輯漂移 | 前端禁止內嵌計算（ADR-6），唯一事實來源在後端 |
| 範圍膨脹（PDF/Gemini/i18n） | 本檔 M0–M4 之外一律開 issue 不實作；M5/M6 只開 issue |
| 雙 repo 互相阻塞 | M2a 與 Repo 1 M1 無依賴，先行 |