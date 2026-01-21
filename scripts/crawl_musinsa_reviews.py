#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import time
import re
import requests  # 리다이렉트 처리를 위해 필수
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    return driver

def extract_product_no_from_url(url: str) -> Optional[str]:
    """단축 URL(onelink, musinsa.link) 리다이렉트 처리 및 상품번호 추출"""
    if 'onelink.me' in url or 'musinsa.link' in url:
        try:
            # allow_redirects=True를 통해 실제 상품 상세 페이지 URL을 획득
            response = requests.get(url, allow_redirects=True, timeout=10)
            url = response.url
        except Exception as e:
            print(f"[오류] URL 리다이렉트 실패: {e}")
            return None
    
    match = re.search(r'/products/(\d+)', url)
    return match.group(1) if match else None

def normalize_date(date_str: str) -> str:
    if not date_str: return ""
    if date_str.startswith('20'): return date_str
    match = re.match(r'^(\d{2})\.(\d{2})\.(\d{2})$', date_str)
    if match:
        y, m, d = match.groups()
        return f"20{y}.{m}.{d}"
    return date_str

def parse_height_weight(text: str) -> tuple:
    h, w = None, None
    hm = re.search(r'(\d+)cm', text)
    if hm: h = int(hm.group(1))
    wm = re.search(r'(\d+)kg', text)
    if wm: w = int(wm.group(1))
    return h, w

def collect_reviews(goods_no: str, target_total: int = 20) -> List[Dict]:
    driver = setup_driver()
    # 도움순(추천순) 정렬 URL로 바로 진입
    review_url = f"https://www.musinsa.com/review/goods/{goods_no}?sort=up_cnt_desc"
    collected_reviews = {}
    
    try:
        #print(f"[정보] 무신사 상품번호 {goods_no} 리뷰 수집 시작...")
        driver.get(review_url)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.gtm-impression-content")))
        except:
            pass
        
        time.sleep(1.5)

        scroll_attempts = 0
        while len(collected_reviews) < target_total and scroll_attempts < 50:
            # 1. 모든 '더보기' 버튼 일괄 클릭 (JS) - 숨겨진 전체 내용 로드
            driver.execute_script("""
                document.querySelectorAll("span[class*='MoreButton']").forEach(btn => {
                    if (btn.innerText.includes('더보기')) {
                        btn.click();
                    }
                });
            """)
            time.sleep(0.6) 

            items = driver.find_elements(By.CSS_SELECTOR, "div.gtm-impression-content")
            new_found_this_round = 0

            for item in items:
                try:
                    review_id = item.get_dom_attribute("data-content-id")
                    if not review_id or review_id in collected_reviews:
                        continue

                    # 내용 추출: '더보기' 버튼을 제외한 순수 전체 텍스트 수집
                    content_element = item.find_element(By.CSS_SELECTOR, "div[class*='ExpandableContent'] span[class*='text-black']")
                    full_content = driver.execute_script("""
                        var el = arguments[0];
                        var clone = el.cloneNode(true);
                        var moreBtn = clone.querySelector("[class*='MoreButton']");
                        if(moreBtn) moreBtn.remove();
                        return clone.textContent.trim();
                    """, content_element)

                    # 별점/날짜
                    try:
                        score_text = item.find_element(By.CSS_SELECTOR, "div[class*='StarsScore'] span").get_attribute('textContent').strip()
                        rating = int(score_text)
                    except: rating = 5
                    
                    date_raw = item.find_element(By.CSS_SELECTOR, "span[class*='PurchaseDate']").get_attribute('textContent').strip()
                    review_date = normalize_date(date_raw)

                    # 이미지
                    images = [img.get_dom_attribute("src") for img in item.find_elements(By.CSS_SELECTOR, "div[class*='ExpandableImageGroup'] img")]

                    # 옵션/체형 파싱
                    opt_text, h, w = "", None, None
                    options = item.find_elements(By.CSS_SELECTOR, "div[class*='OptionRow__Container']")
                    for opt in options:
                        spans = opt.find_elements(By.TAG_NAME, "span")
                        if len(spans) < 2: continue
                        lbl, val = spans[0].get_attribute('textContent').strip(), spans[1].get_attribute('textContent').strip()
                        if "구매옵션" in lbl: opt_text = val
                        elif "체형정보" in lbl:
                            parts = [p.strip() for p in val.split('·')]
                            if len(parts) >= 2: h, _ = parse_height_weight(parts[1])
                            if len(parts) >= 3: _, w = parse_height_weight(parts[2])

                    # main.py UnifiedReviewItem 모델에 맞춘 데이터 구성
                    collected_reviews[review_id] = {
                        'rating': rating,
                        'content': full_content,
                        'review_date': review_date,
                        'images': images,
                        'user_height': h,
                        'user_weight': w,
                        'option_text': opt_text
                    }
                    new_found_this_round += 1
                    if len(collected_reviews) >= target_total: break
                except: continue

            #print(f"   -> 현재 {len(collected_reviews)}개 확보 중... (신규: {new_found_this_round})")

            # 2. 정체 현상 해결 (스크롤 전략)
            if new_found_this_round == 0:
                # 새로운 리뷰가 안 나오면 끝까지 강제 점프
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
            else:
                # 자연스러운 로딩을 위해 마지막 아이템으로 스크롤
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", items[-1])
                    time.sleep(1.0)
                except:
                    driver.execute_script("window.scrollBy(0, 1000);")

            scroll_attempts += 1

        return list(collected_reviews.values())[:target_total]

    finally:
        driver.quit()