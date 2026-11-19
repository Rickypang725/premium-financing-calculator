# 01 — 架構決策（Architecture Decisions）

> 每個決策都給出**理由**與**替代方案**，供面試時解釋取捨。決策標記：[採用] / [考慮後否決]。

## ADR-1 計算引擎：獨立 Python 套件，零框架依賴

**[採用]** `src/pfpro/engine.py`：純 Python（僅標準函式庫，不強制 numpy/scipy），不 import FastAPI、不讀環境變數、不做 I/O。

- **理由**：引擎是純函數（輸入參數 + 利益表 → 輸出投影），隔離框架後 golden tests 秒開、無需起伺服器；未來換 API 框架或前端不影響引擎。
- **替代方案**：(a) 直接用 Node/TypeScript 實作——與前端同語言，但數值求解與測試生態不如 Python 直接；(b) 引擎放進 FastAPI route 裡——測試必須起 HTTP，違反「引擎是純函數」的邊界。

## ADR-2 API 框架：FastAPI

**[採用]** P1 階段以 FastAPI 包裝引擎，Pydantic v2 做輸入驗證。

- **理由**：型別即文件（OpenAPI 自動生成，面試 demo 可直接展示 Swagger UI）；Pydantic 驗證擋掉非法輸入（LTV>100、負利率等）；與未來 P5 Gemini 解析（google-genai Python SDK）同生態。
- **替代方案**：(a) Flask——更輕但無內建驗證/文件；(b) Node Express/NestJS——與前端同語言但與 AI SDK 生態割裂；(c) tRPC——型別安全最佳，但要求前後端皆 TS，違反 ADR-1。

## ADR-3 部署目標：GCP Cloud Run（region: asia-east2 香港）

**[已被 ADR-8 取代（2026-11-19）；以下為原始決策，保留作為決策痕跡]**

- **理由**：Cloud Run = 請求導向、scale-to-zero，無閒置成本，正對目標職缺（Junior Cloud Engineer, GCP-first）的技術面；Terraform 管理全部資源，符合 IaC 紀律，可寫進 CV：`Terraform-managed Cloud Run service`。
- **替代方案（考慮後否決）**：(a) GKE——對單一 stateless 服務過度工程，但面試可說「GKE 是下一步當需要 sidecar/service mesh 時」；(b) App Engine——部署簡單但底層控制力弱、不利展示 Terraform 能力；(c) AWS——目標職缺 GCP 為主，否決。
- **注意**：`terraform apply` 需要 Ricky 的 GCP 帳號與 billing——此風險最終成為 pivot 導火線之一，見 ADR-8。

## ADR-4 CI/CD：GitHub Actions

**[採用，經 ADR-8 修訂]** PR 觸發：pytest + 安全掃描（tfsec / trivy）；merge 到 main：build → push 映像檔倉庫 → 更新雲端服務。

- **理由**：PR 上跑測試與掃描是團隊協作的基本紀律；GitHub Actions 與 repo 原生整合；供應商中立，日後加第二朵雲（M5 多雲對比）不用換 CI。
- **替代方案**：Cloud Build / CodePipeline——與各自雲整合更深但綁定單一雲，否決。
- **映像檔倉庫**：隨 ADR-8 改為 Amazon ECR（與原 Artifact Registry 同一理由：部署在同一帳號內，權限由 IAM 單一管理）。
- **雲端認證**：GitHub OIDC → IAM role（短期憑證），不存長期 Access Key 進 secrets。

## ADR-5 無資料庫（P0–P4）

**[採用]** 不引入資料庫；利益演示表由請求 JSON 帶入（或前端內建 demo 資料）。

- **理由**：計算無狀態，資料庫只會增加部署面與成本；原版工具亦無 DB，行為對齊。
- **何時翻案**：當需要「儲存客戶方案歷史」時再引（Cloud SQL 或 Firestore），屆時是獨立 ADR。

## ADR-6 前端：React + TypeScript + Vite（P4）

**[採用]** 與引擎解耦：前端只呼叫 REST API，不內嵌計算邏輯（避免雙邊邏輯漂移——原版正是全在前端計算，重建版把邏輯收斂到後端是架構改進點，面試可講）。

- **替代方案**：(a) Next.js SSR——對純內部計算工具無 SEO/SSR 需求，否決；(b) 純 HTML+JS 單檔——維護性差，否決。

## 目標架構圖（M2b 完成後）

```
┌────────┐   HTTP    ┌─────────────┐   ┌──────────────────────────────┐
│ React  │ ────────► │ ALB         │──►│ ECS Fargate                  │
│ (M4)   │ ◄──────── │ (Repo 1 M2) │   │ (FastAPI + engine, 非 root)  │
└────────┘   JSON    └─────────────┘   │  · POST /projection          │
                                       │  · POST /stress              │
                                       │  · GET  /healthz             │
                                       └───┬──────────────┬───────────┘
                                           │              │
                                      ┌────┴─────┐  ┌─────┴──────┐
                                      │   ECR    │  │ CloudWatch │
                                      │ (images) │  │ (logs)     │
                                      └──────────┘  └────────────┘
   Terraform 邊界：Repo 1 管 網路/ALB/ECR/cluster/log group/SG；
                  Repo 2 管 Dockerfile/task definition/service/CI
   跨 repo 引用：data source 依 tag 查詢（鬆耦合），非 remote state
   GitHub Actions ──OIDC──► IAM role：push ECR + 更新 service
```

## 安全與合規基線

- 輸入驗證全部在 Pydantic 層（範圍檢查：0&lt;LTV≤100、rate≥0、fx&gt;0、年份為正整數）。
- 容器以非 root 使用者執行；只暴露 8080。
- `.env`、Access Key 一律不進 repo（`.gitignore` 已備）；CI 用 GitHub OIDC 短期憑證。
- CI 靜態掃描：tfsec（Terraform）＋ trivy（映像檔漏洞）。
- CORS：M4 前端同源部署時可鎖定 origin。

## ADR-7 重建策略：砍掉實作、保留合約（2026-11-12）

**[採用]** 捨棄第一版重建的全部實作，以「測試先於實作」重新開始：新 repo 初始 commit 只含 golden-vector 合約（`tests/` + `docs/`），引擎不存在、pytest 預期全紅，實作於 milestone 分支跟進。

- **背景**：第一版重建（2026-11 上旬，舊 repo `pf-pro-rebuild`）直接實作、事後補驗證；測試與實作由同一執行流程產生，golden vectors 的獨立驗證價值未被利用——「數對」缺乏客觀錨點，無法向第三方證明正確性。
- **理由**：合約是 2026-11-09 對原版工具 live UI 逆向驗證過的資產，錨定第三方產品的觀測行為；保留合約、重寫實作，使「正確」成為可驗證的性質，且 commit 歷史順序本身呈現測試先行（TDD）。
- **替代方案**：(a) 局部重構舊版——否決：缺口是流程性的（測試非獨立產生），補丁式修補留不下決策痕跡；(b) 在舊版上補測試——否決：commit 歷史混雜，無法呈現測試先行的時間順序，證據力弱；(c) 放棄專案——否決：對標目標職缺（GCP / Terraform / CI-CD）的證據鏈中斷。
- **代價與對策**：已投入工時沉沒；deadline 不變，熔斷機制沿用（總時數上限 10h、2026-11-23 截止）。舊 repo 不刪除——archive 並標示 DEPRECATED，作為「砍掉的決心」的實體痕跡。

## ADR-8 部署平台：由 GCP Cloud Run 轉向 AWS ECS Fargate（2026-11-19）

**[採用]** M2 起的部署平台由 GCP Cloud Run 改為 AWS ECS Fargate（ap-east-1），運行在 cloud-lab（Repo 1）管理的 VPC 之上。Cloud Run 降級為日後 M5「多雲對比」的候選，不在關鍵路徑。此決策取代 ADR-3。

- **背景**：
  - (1) ADR-3 的前提是「目標職缺 GCP-first」（006 職缺評估）；2026-11 市場複檢後策略改為「不針對單一崗位，對齊香港雲端工程整體需求」——香港金融業以 AWS 為主力，且相當比例雲端職缺要求多雲能力，單壓 GCP 的證據面變窄。
  - (2) GCP 帳號至今未開通，M2 驗收只能停在 `terraform plan`，產生不了「可 curl 的部署證據」，對以證據驅動為賣點的 portfolio 是硬傷。
  - (3) cloud-lab 已完成 VPC、S3 state backend、destroy/rebuild 驗證（Task 1–A），Repo 2 可直接運行在自家地基上，形成「IaC 平台承載 IaC 應用」的雙 repo 敘事。
- **理由**：驗證證據鏈完整（apply → curl ALB → 數字對 golden vectors 的端到端驗證）；與 cloud-lab 形成可講的協同故事；Fargate 無伺服器節點管理，複雜度對單一 stateless 服務剛好，且預留升級到 EKS 的敘事空間。
- **替代方案（考慮後否決）**：
  - (a) 維持 Cloud Run、先開 GCP 帳號——否決：驗證仍受帳號/billing 阻塞，且與 cloud-lab 零協同；
  - (b) 雙雲並行——否決：工時與驗收成本翻倍，超出熔斷預算；
  - (c) AWS App Runner / Elastic Beanstalk——否決：底層控制力弱、不利展示 Terraform 與網路知識（與當年否決 App Engine 同一邏輯）；
  - (d) EKS——否決：對單一 stateless 服務過度工程（與當年否決 GKE 同一邏輯），保留為「需要 service mesh 時的下一步」敘事。
- **跨 repo 邊界**：
  - Repo 1（cloud-lab）= 平台層（VPC、subnet、ECR repository、ECS cluster、ALB、CloudWatch log group、安全群組）；Repo 2 = 應用層（Dockerfile、task definition、ECS service、CI）。
  - Repo 2 以 **Terraform data source 依 tag 查詢** Repo 1 的資源，不用 remote state——data source 是鬆耦合（Repo 1 內部 refactor 不影響 Repo 2），remote state 是強耦合（輸出改名即打斷 plan，且需互相開放 state 存取權限）。
- **代價與對策**：ADR-3 的 GCP-first 前提作廢；M2/M3 內容改寫（見修訂版 `03-roadmap.md`）；關鍵路徑變雙 repo——Repo 2 M2b 依賴 Repo 1 M1，故 M2 拆分為 M2a（Dockerfile，無依賴）與 M2b（AWS 部署）。**熔斷機制待 Ricky 拍板**：建議 2026-11-23 檢查點重新定義為「M2a 完成＋求職投遞就緒」，M2b 起列為第二期並另設預算。