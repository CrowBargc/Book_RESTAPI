import httpx
from bs4 import BeautifulSoup
import json
import re
import asyncio
from typing import Dict, Optional

def _get_category_tree(soup: BeautifulSoup) -> list:
    categories = []
    sort_lists = soup.select(".bd > .sort > li")
    for sort_list in sort_lists:
        category_tags = sort_list.select("a")
        if category_tags:
            current_node = {"name": category_tags[0].get_text(strip=True), "children": []}
            parent_node = current_node
            for tag in category_tags[1:]:
                category_name = tag.get_text(strip=True)
                new_node = {"name": category_name, "children": []}
                parent_node["children"].append(new_node)
                parent_node = new_node
            categories.append(current_node)
    return categories if categories else [{"name": None, "children": []}]

def _get_image_url(soup: BeautifulSoup) -> str:
    img_tag = soup.find("img", class_="cover")
    return img_tag.get("src") if img_tag else ""

def _get_title(soup: BeautifulSoup) -> str:
    title_tag = soup.find("div", class_="mod type02_p002 clearfix")
    return title_tag.get_text(strip=True) if title_tag else ""

def _get_author(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    author_info = {
        "authors": [],
        "original_authors": [],
        "translators": [],
        "publisher": None,
        "publish_date": None,
        "language": None
    }

    #  HTML 結構(作者)是否存在檢查
    author_section = soup.find("div", class_="type02_p003 clearfix")
    if not author_section:
        print("⚠️ 找不到作者資訊區塊 (type02_p003 clearfix)，跳過作者解析")
        return author_info

    items = author_section.find_all("li")
    for item in items:
        text = item.get_text(separator=" ", strip=True)
        if "作者：" in text and not "原文作者：" in text:
            links = item.find_all("a", recursive=False)
            link_texts = [
                link.get_text(strip=True)
                for link in links
                if link.get("href") and link.get_text(strip=True) not in ["取消", "確定", "新功能介紹"]
            ]
            author_info["authors"].extend(link_texts)
        elif "原文作者：" in text:
            links = item.find_all("a", recursive=False)
            author_info["original_authors"].extend(link.get_text(strip=True) for link in links)
        elif "譯者：" in text:
            links = item.find_all("a", recursive=False)
            author_info["translators"].extend(link.get_text(strip=True) for link in links)
        elif "出版社：" in text:
            publisher_tag = item.find("a", recursive=False)
            if publisher_tag:
                author_info["publisher"] = publisher_tag.get_text(strip=True)
        elif "出版日期：" in text:
            author_info["publish_date"] = text.split("出版日期：", 1)[1].strip()
        elif "語言：" in text:
            author_info["language"] = text.split("語言：", 1)[1].strip()

    for key in ["authors", "original_authors", "translators"]:
        author_info[key] = list(filter(None, set(author_info[key])))

    return author_info


def _get_price(soup: BeautifulSoup) -> int:
    price_tag = soup.select_one(".price > li:nth-child(1) > em:nth-child(1)")
    if price_tag:
        price_text = price_tag.get_text(strip=True).replace(',', '')
        return int(price_text) if price_text.isdigit() else 0
    return 0

def _get_additional_info(soup: BeautifulSoup) -> Dict[str, str]:
    additional_info = {}
    sections = soup.find_all("div", class_="mod_b type02_m057 clearfix")
    for section in sections:
        header = section.find("h3")
        content = section.find("div", class_="content")
        if header and content:
            key = header.get_text(strip=True)
            value = content.get_text(separator=" ", strip=True)
            value = re.sub(r'[\n\r\u0089\u00a0]', '', value)
            additional_info[key] = value
    return additional_info

def _get_detail_info(soup: BeautifulSoup) -> Dict[str, str]:
    detail_info = {}
    info_tags = soup.find_all("div", class_="bd")
    for info_tag in info_tags:
        info_items = info_tag.find_all("li")
        for item in info_items:
            info_text = item.get_text(separator=" ", strip=True).replace(" ", "")
            if "本書分類" not in info_text:
                key_value = info_text.split("：")
                if len(key_value) == 2:
                    if key_value[0] == "規格":
                        specs = key_value[1].split("/")
                        for spec in specs:
                            spec = spec.strip()
                            if spec.endswith("裝"):
                                detail_info["裝訂方式"] = spec
                            elif spec.endswith("頁"):
                                detail_info["頁數"] = spec
                            elif spec.endswith("cm"):
                                detail_info["尺寸"] = spec
                            elif spec.endswith("級"):
                                detail_info["分級"] = spec
                            elif spec.endswith("刷"):
                                detail_info["印刷方式"] = spec
                            elif spec.endswith("版"):
                                detail_info["版次"] = spec
                    else:
                        detail_info[key_value[0]] = key_value[1]
    return detail_info

async def scrape_book_info(book_id: str, include_introduce: bool = False) -> Optional[str]:
    url = f'https://www.books.com.tw/products/{book_id}?sloc=main'
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            # 如果不是 200，手動記錄錯誤並回傳 None
            if response.status_code != 200:
                print(f"⚠ 無法取得書籍頁面：HTTP {response.status_code} {url}")
                return None
            soup = BeautifulSoup(response.text, "html.parser")
            book_info = {
                "image": _get_image_url(soup),
                "title": _get_title(soup),
                "price": _get_price(soup)
            }
            author_info = _get_author(soup)
            detail_info = _get_detail_info(soup)
            isbn = detail_info.pop("ISBN", "")
            category_trees = _get_category_tree(soup)
            result = {
                "ISBN": isbn,
                **book_info,
                **author_info,
                "category_trees": category_trees,
                "detail_info": detail_info
            }
            if include_introduce:
                additional_info = _get_additional_info(soup)
                result.update(additional_info)
            return result
    except Exception as e:
        print(f"錯誤：{str(e)}")
        return None

async def scrape_book_introduce(book_id: str) -> Optional[str]:
    url = f'https://www.books.com.tw/products/{book_id}?sloc=main'
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            result = {
                "title": _get_title(soup)
            }
            additional_info = _get_additional_info(soup)
            result.update(additional_info)
            return json.dumps(result, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"錯誤：{str(e)}")
        return None

# 非同步 CLI 測試入口
async def main():
    while True:
        book_id = input("請輸入博客來書籍ID（或輸入'q'退出）: ").strip()
        if book_id.lower() == 'q':
            break
        json_data = await scrape_book_info(book_id)
        if json_data:
            print(json_data)
        else:
            print("無法獲取書籍信息，請確認書籍ID是否正確。")

if __name__ == "__main__":
    asyncio.run(main())

