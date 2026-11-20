# Decision Journal

重練期間的決策紀錄。用法：每當發現自己停在一個抉擇超過約 20 分鐘，就記一筆（5 分鐘內寫完）。ADR 記「大事」，這裡記「每件小事的選擇」。

每筆五個欄位：

```
## YYYY-MM-DD — M<milestone> <抉擇主題>
- 抉擇：<在選什麼>
- 選了：<你的決定>
- 為什麼：<理由，含你當時的假設>
- 代價/省下：< trade-off，數字化更好（時間、範圍、風險）>
- 面試可用度：★★★（可講什麼；★ = 不用背，記了即可）
```

「面試可用度」欄位是刻意設計的：寫的當下就要判斷「這筆值不值得講」，值得講的就是真知識點。

---

## 2026-11-12 — 啟動 重建決策（對應 ADR-7）
- 抉擇：第一版重建缺乏客觀驗證錨點，下一步怎麼走
- 選了：砍掉實作、保留 golden-vector 合約，contract-first 重練
- 為什麼：測試與實作由同一流程產生，「數對」無法向第三方證明；合約錨定 2026-11-09 對原版工具 live UI 的逆向驗證
- 代價/省下：已投入工時沉沒；換取 commit 歷史呈現 TDD 順序 + 每個數值可追溯
- 面試可用度：★★★（sunk cost 判斷、ADR 文化、可驗證性設計）

## 2026-11-12 — 進度控制 熔斷機制沿用
- 抉擇：重練是否重置時間預算
- 選了：不重置——總時數上限 10h、2026-11-23 截止，沿用舊預算而非重新計算
- 為什麼：deadline 由求職節奏決定（offer 死線約 11/25–30），不是由工作量決定；重設預算等於合理化拖延
- 代價/省下：M4 前端做不完就砍；保住投遞優先級
- 面試可用度：★★☆（scope vs deadline 的 trade-off 思維）

<!-- 以下由 Ricky 在重練過程中填寫。每個 milestone 完成時，加一節回顧三問：
1. 當初的假設哪個錯了？
2. 如果重來一次會跳過什麼？
3. 這一步的證據在哪？（commit 連結 / CI 截圖）
-->
## 2026-11-12 — M0 IRR 求解器選擇
- 抉擇：Newton-Raphson（規格建議）vs 掃描+二分法
- 選了：掃描+二分法——Newton 在 year-5 case 第一步 r=0→2.77 發散溢出
- 為什麼：前期虧損型現金流的 NPV 曲線（圖形上）在初值附近過陡（太過敏銳）；規格 §2 允許任何正確求解器
- 代價/省下：求解器不優雅，但收斂有保證，而且專案的表現有保證，能夠很好的提供搜索區間，免除了最大壞處；日後可加分段 Newton 提速

## 2026-11-14 — M0 累計利息語義
- 抉擇：累計利息按表格列累加 vs 按日曆年累加
- 選了：日曆年——表格缺列年份利息照樣產生（year-20 差 8 年年息被 golden test 抓住）

## 2026-11-15 — M1 httpx → httpx2 遷移
- 抉擇：跟唔跟 Starlette 嘅 deprecation warning 轉 httpx2
- 選了：轉——httpx stable line 停滯 21 個月，冇安全修補路徑；httpx2 由 Pydantic Services＋原作者維護，FastAPI/OpenAI SDK 已遷移
- 為什麼：供應鏈維護性係預防式資安，唔等到 CVE 先郁
- 代價/省下：改一行依賴；pytest 加 deprecation-as-error 防回退
- 注意：★★★（supply-chain hygiene、deprecation 監控策略）

## 2026-11-15 — 流程漏洞：.gitignore 冇喺重建時轉移
- 抉擇：無——係事後發現
- 發生：sandbox 建立嘅 .gitignore 冇跟住 repo 轉移去本機，本地版本只有 .DS_Store
- 後果：egg-info 同 __pycache__ 被追蹤，git status 混濁
- 對策：重建 repo 時檢查清單加一項「逐個檔案核對 sandbox 與本機一致」

## 2026-11-19 — M2 部署平台 pivot（對應 ADR-8）
- 抉擇：M2 部署平台維持 GCP Cloud Run 還是轉向 AWS ECS Fargate
- 選了：AWS ECS Fargate（ap-east-1），Cloud Run 降級為 M5 多雲對比候選
- 為什麼：策略由「崗位針對性（GCP-first）」改為「香港雲端市場整體需求」——香港金融業 AWS 為主力、多雲是常態要求；且 GCP 帳號未開通，Cloud Run 路線驗收只能停在 plan，產生不了可 curl 的證據；cloud-lab 地基現成
- 代價/省下：ADR-3 前提作廢、M2/M3 改寫（約 1h 文件工）；換取端到端可驗證證據＋雙 repo 協同敘事
- 面試可用度：★★★（pivot 的決策框架：證據鏈完整性 &gt; 單一平台熟練度；sunk cost 與前提失效的辨識）

## 2026-11-19 — 雙 repo 邊界劃分
- 抉擇：Repo 2 如何引用 cloud-lab 的網路資源（remote state vs data source）
- 選了：Terraform data source 依 tag 查詢
- 為什麼：鬆耦合——Repo 1 內部 refactor 不影響 Repo 2；remote state 需互相開放 state 權限且輸出改名即打斷 plan
- 代價/省下：data source 無法強制「資源必定存在」，靠驗收條件與文件約定補
- 面試可用度：★★★（耦合度權衡、跨團隊 infra 協作模式）

## 2026-11-19 — 熔斷機制重新定義（已拍板）
- 抉擇：ADR-7 的 11-23 deadline 與 10h 上限在 pivot 後如何處理
- 選了：建議 11-23 重新定義為「M2a 完成＋求職投遞就緒」，M2b 起列第二期另設預算
- 為什麼：deadline 由求職節奏決定，不是工作量；M2b 卡在 Repo 1 M1 前置，硬守原 deadline 只會兩邊都半成品
- 面試可用度：★★☆（scope vs deadline、檢查點設計）

## 2026-11-19 — M2a 完成回顧（containerize）
1. 當初的假設哪個錯了？（自己填——例如對 Docker layer caching 或映像檔大小的預期）
2. 重來一次會跳過什麼？（自己填）
3. 證據在哪：merge commit da6e889；驗收輸出（docker build OK / /healthz 200 / id -u ≠ 0 / year-7 projection 對 golden vectors bit-for-bit）；tag m2a-complete

## 2026-11-19 — 流程教訓：雙軌提交＋branch 切點偏差（reflog 還原）
- 抉擇：無——事後用 git reflog 還原操作序列時發現
- 發生：(1) docs branch 從未合併的 feature commit（4749069）切出，而非 main；(2) 同一份 stage-0 編輯直接 commit 到 main（103b49a）、又複製到 branch（d17f2e4）
- 後果：merge 時 01-architecture.md 衝突；main 側編輯 A 變「插入」、殘留語義矛盾的舊狀態行；解法用 git checkout --theirs 取 branch 側
- 對策：branch 一律 `git switch -c &lt;name&gt; main` 切點寫死＋切完 `git log main..HEAD --oneline` 自檢為空；所有變更（含純文件）一律走 branch，main 只接受 merge
- 面試可用度：★★★（root cause 分析、reflog 還原、branch=commit 上的標籤這個資料模型）

## 2026-11-19 — commit message typo（EC2→ECS Fargate）的處置
- 抉擇：兩筆 commit message 誤寫 EC2 Fargate，改寫歷史還是留痕？
- 判斷標準：是否已推送。已推送的 da6e889 不動（force-push 的解釋成本高於 typo，且與「未修飾證據鏈」的定位矛盾）；未推送的 d17f2e4 用 rebase --rebase-merges + reword 修正
- 插曲：自動化 one-liner 因 macOS BSD sed `-i` 須接備份副檔名而失敗（GNU sed 可裸用）；第一輪 reword 未生效；第二輪互動式成功，且學到 HEAD~1=第一 parent、HEAD^2=第二 parent（merge commit 導航）
- 面試可用度：★★★（已發布/未發布歷史的處置框架、GNU/BSD userland 差異、~ 與 ^ 語義）