# KICKOFF — M2a 容器化（Dockerfile）

## 任務
為本 repo 建立 production-ready 的 `Dockerfile` 與 `.dockerignore`，把 M1 的 FastAPI 服務容器化。**只做這件事。**

## 硬性規則
1. `src/`、`tests/`、`tests/vectors.json` 一律不得修改——測試是合約，不可弱化。
2. 不新增 Python 依賴到 `pyproject.toml` 的 runtime 依賴（builder 階段裝 dev 依賴沒問題，runtime 映像只裝 runtime 依賴）。
3. 不寫任何 Terraform、CI yaml——那是 M2b/M3。
4. Conventional Commits；做完即停，輸出 completion report。
5. 規格沒寫的地方（如 base image 版本、健康檢查寫法）是你的 judgment call，逐條列進 report，不要默默決定。

## 規格
- Multi-stage：builder 階段（含 build tools）→ runtime 階段基於 `python:3.12-slim`。
- **非 root 用戶**運行 uvicorn，監聽 0.0.0.0:8080。
- `.dockerignore` 排除 `.git`、`tests/`（映像檔不需測試）、`docs/`、`__pycache__`、`.venv`。

## 驗收指令（report 必須附上實際輸出）
```
docker build -t pfpro:m2a .
docker run -d --name pfpro-m2a -p 8080:8080 pfpro:m2a
curl -sf localhost:8080/healthz          # 期望 200
docker exec pfpro-m2a id -u              # 期望 ≠ 0
docker stop pfpro-m2a && docker rm pfpro-m2a
```

## Completion report 格式
1. 驗收指令與實際輸出（逐條）。
2. Commit 列表。
3. Judgment calls（規格留白處你怎麼決定、為什麼）。
4. 異常（任何預期外狀況，包括環境問題）。