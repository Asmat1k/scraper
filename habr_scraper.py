from urllib.request import urlopen, Request
from urllib.parse import quote, urljoin
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
import time
import csv

BASE_URL = "https://habr.com"
SEARCH_PATH = "/ru/search/"


def fetch_article_text(article_url):
    try:
        print(f"-Scrapping article text | start | url = {article_url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        }

        request = Request(article_url, headers=headers)
        html = urlopen(request)
        soup = BeautifulSoup(html.read(), features="html.parser")

        article_body = (
                soup.select_one("div.article-formatted-body") or
                soup.select_one("div.tm-article-presenter__content") or
                soup.select_one("article") or
                soup.select_one("main")
        )

        print(f"-Scrapping article text | done | url = {article_url}\n")
        if article_body:
            for script in article_body(["script", "style"]):
                script.decompose()

            text = article_body.get_text(separator=" ", strip=True)
            return text

        return ""

    except Exception as e:
        print(f"-Scrapping article text | failed | url = {article_url} | error = {e}\n")
        return ""

def is_duplicate_article(title, existing_articles):
    if not title:
        return False
    for article in existing_articles:
        if article.get('title') == title:
            return True
    return False

def search_habr(search_term, max_pages=3, period="all", fetch_text=False):
    articles = []
    encoded_term = quote(search_term)

    for page in range(1, max_pages + 1):
        print(f"Scrapping page | start | page = {page}")
        try:
            search_url = (
                f"{BASE_URL}{SEARCH_PATH}"
                f"?q={encoded_term}"
                f"&target_type=posts"
                f"&order=relevance"
                f"&period={period}"
                f"&page={page}"
            )

            print(f"Scrapping {search_url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
            }

            request = Request(search_url, headers=headers)
            html = urlopen(request)
            soup = BeautifulSoup(html.read(), features="html.parser")

            items = soup.select("article.tm-articles-list__item") or soup.select("li.tm-articles-list__item")

            if not items:
                print(f"Scrapping page | done | page {page} is empty\n")
                break

            for item in items:
                article_data = {}

                title_a = item.select_one("a.tm-article-snippet__title-link") or item.select_one("a.tm-title__link")
                title_text = title_a.get_text()

                if is_duplicate_article(title_text, articles):
                    print(f"[DUPLICATE] Article already scrapped | skip | title = '{title_text}'")
                    continue

                if title_a:
                    article_data["title"] = title_text
                    raw_href = title_a.get("href", "").split("?")[0]
                    article_data["url"] = urljoin(BASE_URL, raw_href)

                author_a = item.select_one("a.tm-user-info__username") or item.select_one("span.tm-user-info__username")
                if author_a:
                    article_data["authors"] = author_a.get_text()

                desc = (
                        item.select_one(".tm-article-snippet__description")
                        or item.select_one(".article-formatted-body")
                        or item.select_one(".tm-article-snippet")
                )
                if desc:
                    txt = desc.get_text(" ")
                    article_data["annotation"] = txt

                if fetch_text and article_data.get("url"):
                    article_data["text"] = fetch_article_text(article_data["url"])
                    time.sleep(0.5)

                if article_data.get("title") or article_data.get("url"):
                    articles.append(article_data)

            print(f"Scrapping page | done | page = {page} | total articles = {len(articles)}\n")

            time.sleep(1)

        except HTTPError as e:
            print(f"Scrapping page | failed | page = {page} | HTTP error: {e}\n")
            if e.code in (300, 399):
                time.sleep(5)
                continue
            break
        except URLError as e:
            print(f"Scrapping page | failed | page = {page} | Save error: {e}\n")
            break
        except Exception as e:
            print(f"Scrapping page | failed | page = {page} | Unknown error: {e}\n")
            break

    return articles


def print_articles(articles):
    print(f"Found {len(articles)} articles:\n")

    for idx, article in enumerate(articles, 1):
        print(f"[{idx}] {article.get('title', 'Без названия')} - {article['url']}\n")


def save_to_file(articles, filename="articles.csv", include_text=False):
    if include_text:
        fieldnames = ["title", "authors", "annotation", "text", "url"]
    else:
        fieldnames = ["title", "authors", "annotation", "url"]

    try:
        print(f"\nSaving to CSV file | start")
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for a in articles:
                row = {
                    "title": a.get("title", ""),
                    "authors": a.get("authors", ""),
                    "annotation": a.get("annotation", "").replace("\r", " ").replace("\n", " "),
                    "url": a.get("url", ""),
                }
                if include_text:
                    row["text"] = a.get("text", "").replace("\r", " ").replace("\n", " ")

                writer.writerow(row)

        print(f"Saving to CSV file | done | file name = {filename}")
    except Exception as e:
        print(f"Saving to CSV file | failed | error = {e}")


if __name__ == "__main__":
    print(f"\n{'=' * 30}")
    print(f"HEY, WELCOME TO HABR SCRAPER!")
    print(f"{'=' * 30}\n")
    search_term = input("Enter search string: " or "web,веб").strip()

    max_pages = int(input("Enter the number of pages to scrap: ") or "1")

    period = input("Enter the period [all/year/month/week/day]: ").strip().lower() or "all"

    fetch_text_input = input("Do you want to scrap the full article text? (y/n): ").strip().lower()
    fetch_text = fetch_text_input in ("y", "yes")

    print(f"\nLooking for the articles | start | search string = {search_term}\n")

    articles = search_habr(search_term, max_pages=max_pages, fetch_text=fetch_text)

    print(f"Looking for the articles | done | search string = {search_term}\n")

    if articles:
        print_articles(articles)
        save = input("Save the result to a csv file? (y/n): ").strip().lower()
        if save == "y":
            filename = input("\nEnter file name: ").strip() or "articles.csv"
            save_to_file(articles, filename, include_text=fetch_text)
        else:
            print("You can find your results in cmd")
    else:
        print("No articles found and nothing to save!")

print(f"\n{'=' * 50}")
print(f"BYE, THANK YOU FOR USING THE HABR SCRAPER!")
print(f"{'=' * 50}\n")