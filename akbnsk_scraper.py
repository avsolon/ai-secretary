#!/usr/bin/env python3
"""
Скрипт для парсинга сайта akbnsk.ru - каталог аккумуляторных батарей.
Извлекает: наименование, цену, полярность, ёмкость, габаритные размеры.
Сохраняет результат в JSON и TXT для базы знаний ИИ-агента.
"""

import requests
import json
import re
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://akbnsk.ru"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

CATEGORIES = [
    "/katalog/tyumen-battery-premium",
    "/katalog/tyumen-battery-standart",
    "/katalog/tyumen-battery-asia",
    "/katalog/zver",
    "/katalog/delkor",
    "/katalog/bars",
    "/katalog/tudor-high-tech-ispaniya",
    "/katalog/tab-sloveniya",
    "/katalog/solite-yu-koreya",
    "/katalog/super-president",
    "/katalog/topla",
    "/katalog/rocket-mf-30",
    "/katalog/rocket-smf-50",
    "/katalog/afa-plus",
    "/katalog/varta",
    "/katalog/bosch",
    "/katalog/fb-yaponiya",
    "/katalog/elab",
    "/katalog/reactor",
    "/katalog/solite",
    "/katalog/solite-silver-yu-koreya",
    "/katalog/2018-08-01-13-23-59",
    "/katalog/2018-09-30-13-19-39",
]

session = requests.Session()
session.headers.update(HEADERS)


def get_product_links_from_category(cat_path):
    """Extract product detail links that belong to this specific category."""
    cat_url = urljoin(BASE_URL, cat_path)
    try:
        resp = session.get(cat_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ERROR fetching {cat_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()

    # Extract product URLs from the horizontal product grid
    # The "spacer product-container" divs contain each product
    for spacer in soup.find_all("div", class_="spacer"):
        a_tag = spacer.find("a", class_="product-details")
        if a_tag and a_tag.get("href"):
            href = a_tag["href"]
            full_url = urljoin(BASE_URL, href)
            # Only add if the URL belongs to this category
            if full_url.startswith(cat_url.rstrip("/") + "/") or "/katalog/" in full_url:
                links.add(full_url)

    # Also look for h2 links (product name links)
    for h2 in soup.find_all("h2"):
        a_tag = h2.find("a")
        if a_tag and a_tag.get("href"):
            href = a_tag["href"]
            full_url = urljoin(BASE_URL, href)
            if "-v-novosibirske" in full_url:
                links.add(full_url)

    return list(links)


def extract_product_data(html, url):
    """Extract full product data from a product detail page."""
    soup = BeautifulSoup(html, "html.parser")
    data = {"url": url}

    # --- Наименование ---
    h1 = soup.find("h1", class_="prod-name")
    if h1:
        data["name"] = h1.get_text(strip=True)
    else:
        h1 = soup.find("h1")
        if h1:
            data["name"] = h1.get_text(strip=True)

    # --- Цена ---
    price_span = soup.find("span", class_="PricesalesPrice")
    if price_span:
        price_text = price_span.get_text(strip=True)
        price_match = re.search(r"(\d[\d\s]*\d)", price_text)
        if price_match:
            data["price"] = int(price_match.group(1).replace(" ", ""))

    # --- Характеристики ---
    fields = {}

    # Find the ha block with product specifications
    ha_block = soup.find("div", class_="ha")
    if ha_block:
        product_fields = ha_block.find_all("div", class_="product-field")
    else:
        # Fallback: find product fields in product-fields container
        pf_container = soup.find("div", class_="product-fields")
        if pf_container:
            product_fields = pf_container.find_all("div", class_="product-field")
        else:
            product_fields = soup.find_all("div", class_="product-field")

    for pf in product_fields:
        title_el = pf.find("span", class_="product-fields-title")
        if not title_el:
            continue
        key = title_el.get_text(strip=True).lower()
        if not key or key in ("обычная цена:",):
            continue

        # Value can be in div or span
        value_el = pf.find("div", class_="product-field-display") or pf.find("span", class_="product-field-display")
        if not value_el:
            continue
        value = value_el.get_text(strip=True)

        # Append dimension description if present
        desc_el = pf.find("div", class_="product-field-desc") or pf.find("span", class_="product-field-desc")
        if desc_el:
            value += " " + desc_el.get_text(strip=True)

        fields[key] = value

    data["polarity"] = fields.get("полярность", "")
    data["capacity_ah"] = fields.get("емкость ач", "")
    data["dimensions"] = fields.get("габариты", "")
    data["terminal_type"] = fields.get("тип клемм", "")
    data["starting_current"] = fields.get("пусковой ток", "")
    data["voltage"] = fields.get("напряжение", "")
    data["car_class"] = fields.get("класс авто", "")

    return data


def main():
    all_product_urls = set()

    # Phase 1: collect all product URLs from all categories
    print("=== Phase 1: Collecting product URLs ===")
    for cat in CATEGORIES:
        links = get_product_links_from_category(cat)
        for link in links:
            all_product_urls.add(link)
        print(f"  {cat}: {len(links)} links (total unique: {len(all_product_urls)})")
        time.sleep(0.3)

    print(f"\nTotal unique product URLs: {len(all_product_urls)}")

    # Phase 2: visit each product page and extract details
    print("\n=== Phase 2: Extracting product details ===")
    products = []
    for i, url in enumerate(sorted(all_product_urls)):
        print(f"  [{i+1}/{len(all_product_urls)}] {url}")
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = extract_product_data(resp.text, url)
            if data.get("name"):
                products.append(data)
                print(f"    -> {data['name'][:60]} | Price: {data.get('price', 'N/A')} | Pol: {data.get('polarity', 'N/A')} | Cap: {data.get('capacity_ah', 'N/A')} | Dim: {data.get('dimensions', 'N/A')}")
            else:
                print(f"    -> WARNING: No name found")
            time.sleep(0.3)
        except Exception as e:
            print(f"    -> ERROR: {e}")

    print(f"\nTotal products scraped: {len(products)}")

    # Save JSON
    with open("akbnsk_products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"Saved to akbnsk_products.json")

    return products


if __name__ == "__main__":
    main()
