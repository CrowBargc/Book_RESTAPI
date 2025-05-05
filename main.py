from fastapi import FastAPI, Path, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from book_model import BookSearchResponse, BookIntroduce, BookInfo, BookRankResponse, BookStats, BookSearchCriteria, \
    BookSearchResultItem
import json
from book_info import scrape_book_info, scrape_book_introduce
from book_searcher import AsyncBookSearcher

app = FastAPI(
    title="博客來 書籍查詢 API",
    version="1.0",
    description="提供書籍詳細資料、相關書籍列表、書籍排行榜等資料"
)
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

searcher = AsyncBookSearcher()

# 加入 CORS 中介層
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/book/{pd_id}",
    response_model=BookInfo,
    summary="取得書籍詳細資料",
    description="根據指定的博客來書籍 ID 查詢書籍詳細資料與規格。",
    responses={
        200: {
            "description": "書籍詳細資料",
            "content": {
                "application/json": {
                    "example": BookInfo.model_config["json_schema_extra"]["example"]
                }
            }
        },
        404: {"description": "找不到書籍"},
        500: {"description": "伺服器錯誤"}
    }
)
async def get_book_info(
        pd_id: str = Path(..., description="博客來商品 ID"),
        introduce: Optional[int] = Query(0, description="是否包含簡介（1=包含，0=不含）")
):
    try:
        include_introduce = bool(introduce)
        result = await scrape_book_info(pd_id, include_introduce)
        if result:
            return BookInfo(**result)
        raise HTTPException(status_code=404, detail="找不到書籍資料，請確認書籍ID是否正確")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/book/introduce/{pd_id}",
    response_model=BookIntroduce,
    summary="取得書籍介紹資料",
    description="根據博客來書籍 ID 查詢書籍介紹。",
    responses={
        200: {
            "description": "書籍簡介資料",
            "content": {
                "application/json": {
                    "example": BookIntroduce.model_config["json_schema_extra"]["example"]
                }
            }
        },
        404: {"description": "找不到書籍介紹"},
        500: {"description": "伺服器錯誤"}
    }
)
async def get_book_introduce(
        pd_id: str = Path(..., description="博客來商品 ID")
):
    try:
        result = await scrape_book_introduce(pd_id)
        if result:
            result_obj = json.loads(result)
            return BookIntroduce(**result_obj)

        raise HTTPException(status_code=404, detail="找不到書籍資料，請確認書籍ID是否正確")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/books/search",
    response_model=BookSearchResponse,
    summary="搜尋相關書籍",
    description="依關鍵字與條件搜尋博客來書籍，支援作者、出版社、價格、上架時間等條件。",
    responses={
        200: {
            "description": "搜尋結果資料",
            "content": {
                "application/json": {
                    "example": BookSearchResponse.model_config["json_schema_extra"]["example"]
                }
            }
        },
        400: {"description": "搜尋條件錯誤"},
        500: {"description": "伺服器錯誤"}
    }
)
async def search_books(
        keyword: str = Query(..., description="書名或關鍵字"),
        all_atr: bool = Query(False, description="是否包含所有書籍屬性（如語言、出版日期）"),
        page: int = Query(1, ge=1, description="起始頁碼"),
        is_stock: int = Query(1, description="是否只查有庫存書籍（1=是, 0=不限）"),
        author: str = Query('', description="作者名稱（可空）"),
        publisher: str = Query('', description="出版社名稱（可空）"),
        date_after: str = Query('', description="指定出版日期之後（YYYY-MM-DD）"),
        price_min: str = Query('0', description="最低價格"),
        price_max: str = Query('999999', description="最高價格")
):
    try:
        status_code, result = await searcher.check_search_connection(
            keyword, is_stock, author, publisher, date_after, price_min, price_max
        )
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=result)

        search_criteria, stats, books_data, error = await searcher.get_search_results(
            keyword, is_stock, author, publisher, date_after, price_min, price_max, page
        )
        if error:
            raise HTTPException(status_code=400, detail=error)

        formatted_books = []
        for book_item in books_data:
            base_info = {
                'productId': book_item.get('ProductID', ''),
                'title': book_item.get('Title', ''),
                'author': book_item.get('Authors', []),
                'publisher': book_item.get('Publisher', ''),
                'image': book_item.get('Image', ''),
                'language': book_item.get('Language') if all_atr else None,
                'publishDate': book_item.get('PublishDate') if all_atr else None
            }

            formatted_books.append(base_info)

        return BookSearchResponse(
            search_criteria=BookSearchCriteria(**search_criteria),
            stats=BookStats(**stats),
            books=[BookSearchResultItem(**book) for book in formatted_books]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/books/search/stats",
    response_model=BookStats,
    summary="取得搜尋結果統計資料",
    description="根據搜尋條件回傳符合條件的書籍總筆數與總頁數。",
    responses={
        200: {
            "description": "搜尋統計資料",
            "content": {
                "application/json": {
                    "example": BookStats.model_config["json_schema_extra"]["example"]
                }
            }
        },
        500: {"description": "伺服器錯誤"}
    }
)
async def get_search_stats(
        keyword: str = Query(..., description="書名或關鍵字"),
        is_stock: int = Query(1, description="是否只查有庫存書籍（1=是, 0=不限）"),
        author: str = Query('', description="作者名稱"),
        publisher: str = Query('', description="出版社名稱"),
        date_after: str = Query('', description="指定出版日期之後（YYYY-MM-DD）"),
        price_min: int = Query(0, description="最低價格"),
        price_max: int = Query(99999, description="最高價格")
):
    try:
        status_code, response = await searcher.check_search_connection(
            keyword, is_stock, author, publisher, date_after, price_min, price_max
        )
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=response)
        total_items, total_pages = searcher.get_search_stats(response)
        return {
            'total_items': total_items,
            'total_pages': total_pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/books/rank",
    response_model=BookRankResponse,
    summary="取得書籍排行榜",
    description="依排行榜類型與書籍分類查詢博客來書籍排行榜。",
    responses={
        200: {
            "description": "書籍排行榜",
            "content": {
                "application/json": {
                    "example": BookRankResponse.model_config["json_schema_extra"]["example"]
                }
            }
        },
        400: {"description": "查詢錯誤"},
        500: {"description": "伺服器錯誤"}
    }
)
async def get_books_rank(
        rank_type: int = Query(
            2, description="排行榜類型（0=即時榜、1=新書榜、2=暢銷榜、3=預購榜）"
        ),
        book_type: str = Query(
            "0",
            description=(
                    "書籍分類代碼：\n"
                    "0 - 總榜\n"
                    "01 - 文學小說\n"
                    "02 - 商業理財\n"
                    "03 - 藝術設計\n"
                    "04 - 人文社科\n"
                    "07 - 心理勵志\n"
                    "12 - 宗教命理\n"
                    "06 - 自然科普\n"
                    "08 - 醫療保健\n"
                    "09 - 飲食\n"
                    "10 - 生活風格\n"
                    "11 - 旅遊\n"
                    "14 - 童書/青少年文學\n"
                    "24 - 國中小參考書\n"
                    "13 - 親子教養\n"
                    "22 - 影視偶像\n"
                    "15 - 輕小說\n"
                    "16 - 漫畫/圖文書\n"
                    "17 - 語言學習\n"
                    "18 - 考試用書\n"
                    "19 - 電腦資訊\n"
                    "20 - 專業/教科書/政府出版品"
            )
        ),
        is_weekly: bool = Query(
            False, description="是否查詢七日榜（False=30天榜, True=7天榜）"
        )
):
    try:
        result = await searcher.book_rank(rank_type, book_type, is_weekly)
        if isinstance(result, dict) and 'error' in result:
            raise HTTPException(status_code=result.get('status_code', 400), detail=result['error'])
        return BookRankResponse(root=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
