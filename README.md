# 📚 博客來書籍查詢 API（FastAPI）

一個基於 Python 的 FastAPI 專案，可查詢 [博客來](https://www.books.com.tw/) 書籍的詳細資訊、排行榜與條件式搜尋結果。支援書籍介紹、作者資訊、出版細節與分類樹結構，並可回傳 JSON 格式供前端使用。

---

## 🚀 專案特色

- 🔍 支援依書名、作者、出版社、價格、出版日期等條件進行搜尋
- 📖 提供書籍詳細資訊（含作者、分類、頁數、尺寸等）
- 🧾 可查詢書籍排行榜（暢銷榜、預購榜、新書榜等）
- ⚡ 使用非同步爬蟲（httpx + BeautifulSoup）加快查詢速度
- ✅ API 規格完整，內建 OpenAPI/Swagger 文件（啟動後於 `/docs`）

---

## 📂 API 路徑總覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/book/{pd_id}` | 查詢單本書籍詳細資料 |
| GET | `/api/book/introduce/{pd_id}` | 查詢書籍簡介 |
| GET | `/api/books/search` | 多條件搜尋書籍 |
| GET | `/api/books/search/stats` | 查詢搜尋結果的統計資料 |
| GET | `/api/books/rank` | 查詢排行榜（每日、每週） |

---

## 🏗 專案架構

```
book_model.py       # 定義所有 API 的 Pydantic 資料模型
book_info.py        # 非同步爬蟲：抓取書籍詳細資訊與簡介
book_searcher.py    # 非同步爬蟲：搜尋書籍與取得排行榜
main.py             # FastAPI 主路由設定
```

---

## 🧪 快速啟動（本地執行）

1️⃣ 安裝依賴：
```bash
pip install -r requirements.txt
```

2️⃣ 執行 API：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

3️⃣ 開啟 Swagger 文件：
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## ☁️ 部署方式（推薦 Render + GitHub Education）

1. 將此專案 Push 至 GitHub Repo  
2. 前往 [Render](https://render.com) 並登入 → New Web Service  
3. 設定指令：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port 10000`
   - Python 版本：需在 `render.yaml` 或 `runtime.txt` 中指定（如 `python-3.11.8`）
4. 綁定免費子網域或自訂網域

---

## 📝 API 範例（查詢書籍）

```bash
GET /api/book/0011016236
```

回傳：
```json
{
  "ISBN": "9789573286388",
  "title": "問ChatGPT也不會的Python量化交易聖經",
  "price": 450,
  "authors": ["張峮瑋", "黃子靜"]
  ...
}
```

---

## 👨‍🎓 作者

由 GitHub Education 學生開發，使用 httpx + FastAPI + BeautifulSoup 實作，適合學術、練習或專題展示使用。