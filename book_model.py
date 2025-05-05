from pydantic import BaseModel
from typing import List, Optional, Dict


class BookInfo(BaseModel):
    ISBN: Optional[str]
    image: str
    title: str
    price: int
    authors: List[str]
    original_authors: List[str]
    translators: List[str]
    publisher: Optional[str]
    publish_date: Optional[str]
    language: Optional[str]
    category_trees: List[Dict]
    detail_info: Dict[str, str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "ISBN": "9789573286388",
                "image": "https://example.com/image.jpg",
                "title": "問ChatGPT也不會的Python量化交易聖經",
                "price": 450,
                "authors": ["張峮瑋", "黃子靜"],
                "original_authors": [],
                "translators": ["王大明"],
                "publisher": "深智數位",
                "publish_date": "2023-12-01",
                "language": "繁體中文",
                "category_trees": [{"name": "商業理財", "children": []}],
                "detail_info": {"裝訂方式": "平裝", "頁數": "320頁"}
            }
        }
    }


class BookIntroduce(BaseModel):
    title: str
    內容簡介: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "問ChatGPT也不會的Python量化交易聖經",
                "內容簡介": "這是一本由實戰經驗分享的量化交易實用書籍..."
            }
        }
    }


class BookStats(BaseModel):
    total_items: int
    total_pages: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_items": 2824,
                "total_pages": 48
            }
        }
    }


class BookSearchCriteria(BaseModel):
    keyword: str
    author: Optional[str]
    publisher: Optional[str]
    in_stock_only: bool
    price_range: Dict[str, int]
    date_after: Optional[str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "keyword": "Python",
                "author": "張峮瑋",
                "publisher": "深智數位",
                "in_stock_only": True,
                "price_range": {"min": 0, "max": 999999},
                "date_after": "2023-01-01"
            }
        }
    }


class BookSearchResultItem(BaseModel):
    productId: str
    title: str
    author: List[str]
    publisher: str
    image: str
    language: Optional[str]
    publishDate: Optional[str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "productId": "0011016236",
                "title": "Python量化交易",
                "author": ["張峮瑋"],
                "publisher": "深智數位",
                "image": "https://example.com/image.jpg",
                "language": "繁體中文",
                "publishDate": "2023-11-01"
            }
        }
    }


class BookSearchResponse(BaseModel):
    search_criteria: BookSearchCriteria
    stats: BookStats
    books: List[BookSearchResultItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "search_criteria": BookSearchCriteria.model_config["json_schema_extra"]["example"],
                "stats": BookStats.model_config["json_schema_extra"]["example"],
                "books": [BookSearchResultItem.model_config["json_schema_extra"]["example"]]
            }
        }
    }


class BookRankItem(BaseModel):
    rank: int
    image_url: str
    product_link: str
    title: str
    authors: List[str]
    price: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "rank": 1,
                "image_url": "https://example.com/book1.jpg",
                "product_link": "https://www.books.com.tw/products/0011016236",
                "title": "Python量化交易",
                "authors": ["張峮瑋"],
                "price": 420
            }
        }
    }


class BookRankResponse(BaseModel):
    root: List[BookRankItem]

    model_config = {
        "json_schema_extra": {
            "example": [BookRankItem.model_config["json_schema_extra"]["example"]]
        }
    }