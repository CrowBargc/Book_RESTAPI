import httpx
from bs4 import BeautifulSoup
import json
import re
import asyncio
from datetime import datetime
from urllib.parse import quote
class AsyncBookSearcher:
    __PAGES_TO_FETCH = 5
    __MAX_CONCURRENT_REQUESTS = 3

    def _compose_keyword(self, keyword: str, author: str, publisher: str) -> str:
        components = [keyword]
        if author:
            components.append(author)
        if publisher:
            components.append(publisher)
        return quote(" ".join(components))

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }

    def parse_book_data(self, response_text):
        try:
            sp = BeautifulSoup(response_text, "html.parser")
            books = []
            book_items = sp.find_all('tbody', id=lambda x: x and x.startswith('itemlist_'))
            for item in book_items:
                book_data = {}
                title_tag = item.find('a', rel='mid_name')
                if title_tag:
                    book_data['Title'] = title_tag.get('title', '')
                img_tag = item.find('img', {'class': ['itemimg', 'b-lazy']})
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src', '')
                    if img_url and not img_url.startswith('http'):
                        img_url = 'https:' + img_url
                    book_data['Image'] = img_url
                authors = []
                author_tags = item.find_all('a', rel='go_author')
                for author_tag in author_tags:
                    if author_tag.text.strip():
                        authors.append(author_tag.text.strip())
                book_data['Authors'] = authors
                publisher_tag = item.find('a', {'target': '_blank', 'href': lambda x: x and 'mid_publish' in x})
                if publisher_tag:
                    book_data['Publisher'] = publisher_tag.text.strip()
                product_id_tag = item.find('input', {'name': 'prod_check'})
                if product_id_tag:
                    book_data['ProductID'] = product_id_tag.get('value', '')
                list_date_tag = item.find('ul', class_='list-date clearfix')
                if list_date_tag:
                    date_and_language = list_date_tag.find('li')
                    if date_and_language:
                        text = date_and_language.text.strip()
                        language_tag = date_and_language.find('span')
                        if language_tag:
                            book_data['Language'] = language_tag.text.strip()
                        date_match = re.search(r'出版日期:\s*(\d{4}-\d{2}-\d{2})', text)
                        if date_match:
                            book_data['PublishDate'] = date_match.group(1)
                books.append(book_data)
            return books
        except Exception as e:
            print(f"Error parsing book data: {e}")
            return []

    def get_search_stats(self, response_text):
        try:
            sp = BeautifulSoup(response_text, "html.parser")
            results_div = sp.find('div', class_='search_results')
            if results_div:
                total_items = results_div.find('span').text.strip()
                total_pages = results_div.text.split('/')[-1].strip()
                return (
                    int(total_items),
                    int(total_pages)
                )
        except Exception as e:
            print(f"解析搜尋統計資料時發生錯誤: {str(e)}")
        return (0, 0)

    async def check_search_connection(self, keyword, stock=1, author='', publisher='', date_after='', price_min='0',
                                      price_max='999999'):
        try:
            if date_after:
                try:
                    datetime.strptime(date_after, '%Y-%m-%d')
                except ValueError:
                    return 400, '日期格式錯誤！請使用 YYYY-MM-DD 格式'

            price_min = price_min if str(price_min).isdigit() else "0"
            price_max = price_max if str(price_max).isdigit() else "999999"

            base_url = 'https://search.books.com.tw/search/query/sort/1/v/0'
            if stock:
                base_url += f'/adv_forsale/{stock}'
            if price_min != "0" or price_max != "999999":
                base_url += f'/adv_price_min/{price_min}/adv_price_max/{price_max}'
            if date_after:
                base_url += f'/adv_date/{date_after}'

            keyword_encoded = self._compose_keyword(keyword, author, publisher)
            final_url = f'{base_url}/key/{keyword_encoded}'

            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.get(final_url)
                if response.status_code == 200:
                    return 200, response.text
                else:
                    return response.status_code, f'HTTP錯誤: {response.status_code}'
        except Exception as e:
            return 500, f'發生錯誤: {str(e)}'

    async def get_search_results(self, keyword, stock=1, author='', publisher='', date_after='', price_min=0,
                                 price_max=999999, start_page=1):
        try:
            if date_after:
                try:
                    datetime.strptime(date_after, '%Y-%m-%d')
                except ValueError:
                    return None, None, None, '日期格式錯誤！請使用 YYYY-MM-DD 格式'

            price_min = int(price_min) if isinstance(price_min, (int, str)) and str(price_min).isdigit() else 0
            price_max = int(price_max) if isinstance(price_max, (int, str)) and str(price_max).isdigit() else 999999

            base_url = 'https://search.books.com.tw/search/query/sort/1/v/0'
            if stock:
                base_url += f'/adv_forsale/{stock}'
            if price_min != "0" or price_max != "999999":
                base_url += f'/adv_price_min/{price_min}/adv_price_max/{price_max}'
            if date_after:
                base_url += f'/adv_date/{date_after}'

            keyword_encoded = self._compose_keyword(keyword, author, publisher)
            first_page_url = f'{base_url}/page/1/key/{keyword_encoded}'

            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.get(first_page_url)
                if response.status_code != 200:
                    return None, None, None, f'HTTP錯誤: {response.status_code}'

                total_items, total_pages = self.get_search_stats(response.text)
                if start_page > total_pages:
                    return None, None, None, f'起始頁碼 {start_page} 超過總頁數 {total_pages}'

                end_page = min(start_page + self.__PAGES_TO_FETCH - 1, total_pages)#__PAGES_TO_FETCH == 5
                semaphore = asyncio.Semaphore(self.__MAX_CONCURRENT_REQUESTS) #__MAX_CONCURRENT_REQUESTS = 3
                async def fetch_and_parse(page):
                    page_url = f'{base_url}/page/{page}/key/{keyword_encoded}'
                    async with semaphore:
                        res = await client.get(page_url)
                        if res.status_code == 200:
                            return self.parse_book_data(res.text)
                        else:
                            print(f"獲取第 {page} 頁失敗: {res.status_code}")
                            return []

                tasks = [fetch_and_parse(page) for page in range(start_page, end_page + 1)]
                all_page_results = await asyncio.gather(*tasks)


                all_books = []
                if date_after:
                    try:
                        date_after_obj = datetime.strptime(date_after, '%Y-%m-%d')
                    except ValueError:
                        return None, None, None, f'date_after 格式錯誤，請用 YYYY-MM-DD'

                    for page_books in all_page_results:
                        for book in page_books:
                            publish_date_str = book.get('PublishDate') or book.get('publishDate')  # 保險些
                            # try:
                            if publish_date_str:
                                publish_date_obj = datetime.strptime(publish_date_str, '%Y-%m-%d')
                                if publish_date_obj >= date_after_obj:
                                        all_books.append(book)
                                    # else:
                                    #     #print(f" 排除 {book.get('Title', '')}（出版日 {publish_date_str}）")
                                # else:
                                #     print(f"⚠ 無出版日，排除：{book.get('Title', '')}")
                            # except ValueError:
                            #     print(f"⚠ 出版日格式錯誤，排除：{book.get('Title', '')}")
                else:
                    # 無 date_after 就全部納入
                    all_books = [book for page in all_page_results for book in page]

            search_criteria = {
                'keyword': keyword,
                'author': author or None,
                'publisher': publisher or None,
                'in_stock_only': stock == 1,
                'price_range': {
                    'min': int(price_min),
                    'max': int(price_max)
                },
                'date_after': date_after or None
            }

            stats = {
                'total_items': total_items,
                'total_pages': total_pages,
                'start_page': start_page,
                'end_page': end_page,
                'collected_books': len(all_books)
            }

            return search_criteria, stats, all_books, None
        except Exception as e:
            return None, None, None, f'發生錯誤: {str(e)}'

    async def book_rank(self, rank_type=2, book_type="0", is_weekly=False):
        rank_type_mapping = {
            0: "realtime",
            1: "newbook",
            2: "saletop",
            3: "pre-ordertop"
        }
        rank_type_key = rank_type_mapping.get(rank_type)

        if rank_type_key == "saletop":
            attribute = "7" if is_weekly else "30"
            url = f"https://www.books.com.tw/web/sys_saletopb/books/{book_type}/?attribute={attribute}"
        else:
            url_templates = {
                "realtime": "https://www.books.com.tw/web/sys_tdrntb/books/",
                "newbook": "https://www.books.com.tw/web/sys_newtopb/books/",
                "pre-ordertop": "https://www.books.com.tw/web/sys_pretopb/books/"
            }
            url = url_templates.get(rank_type_key)

        if not url:
            return {"status_code": 400, "error": "無效的排行榜類型參數"}

        try:
            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return {"status_code": response.status_code, "error": f"HTTP 錯誤: {response.status_code}"}

                soup = BeautifulSoup(response.text, "html.parser")
                target_area = soup.select_one("div.mod.type02_m035.clearfix ul")
                if not target_area:
                    return {"status_code": 404, "error": "無法找到排行榜內容區域"}

                return self.parse_book_rank(target_area)

        except httpx.RequestError as e:
            return {"status_code": 500, "error": f"連線錯誤: {str(e)}"}

    def parse_book_rank(self, target_area):
        books = []
        for item in target_area.find_all("li", class_="item"):
            rank = item.find("strong", class_="no").text if item.find("strong", class_="no") else None
            image_url = item.find("img", class_="cover")["src"] if item.find("img", class_="cover") else None
            product_link = item.find("h4").find("a")["href"] if item.find("h4") and item.find("h4").find("a") else None
            title = item.find("h4").find("a").text if item.find("h4") and item.find("h4").find("a") else None

            authors = []
            author_list_element = item.find("ul", class_="msg")
            if author_list_element:
                author_li = author_list_element.find("li")
                if author_li:
                    author_links = author_li.find_all("a")
                    authors_raw = [author.text.strip() for author in author_links if author and author.text]
                    for raw_author in authors_raw:
                        authors.extend([name.strip() for name in raw_author.split(",")])

            price_raw = item.find("li", class_="price_a")
            if price_raw and price_raw.find_all("b"):
                price_text = price_raw.find_all("b")[-1].text
                try:
                    price = int(price_text.replace(",", "").strip())  # 去除逗號，轉為整數
                except ValueError:
                    price = None
            else:
                price = None

            books.append({
                "rank": rank,
                "image_url": image_url,
                "product_link": product_link,
                "title": title,
                "authors": authors,
                "price": price,
            })

        return books

searcher = AsyncBookSearcher()

async def run():
    criteria, stats, books, error = await searcher.get_search_results(keyword='python',publisher='深智數位')
    if error:
        print("錯誤:", error)
    else:
        print(json.dumps({
            "criteria": criteria,
            "stats": stats,
            "books": books[:]
        }, ensure_ascii=False, indent=4))

# if __name__ == "__main__":
#     asyncio.run(main())