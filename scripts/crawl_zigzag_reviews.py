#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 지그재그 리뷰 크롤링 (최종 최적화) ###
####################################

import random
import time
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

def setup_driver():
    """Chrome WebDriver 설정 (봇 감지 우회 및 최적화)"""
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

def normalize_date(date_str: str) -> str:
    """날짜 형식 통일 (25.10.12 -> 2025.10.12)"""
    if not date_str: return ""
    if date_str.startswith('20'): return date_str
    match = re.match(r'^(\d{2})\.(\d{2})\.(\d{2})$', date_str)
    if match:
        y, m, d = match.groups()
        return f"20{y}.{m}.{d}"
    return date_str

def parse_height_weight(text: str) -> tuple:
    """키/몸무게 텍스트에서 숫자 추출"""
    h, w = None, None
    hm = re.search(r'(\d+)cm', text)
    if hm: h = int(hm.group(1))
    wm = re.search(r'(\d+)kg', text)
    if wm: w = int(wm.group(1))
    return h, w

def crawl_zigzag_reviews(product_url: str, max_reviews: int = 20) -> List[Dict]:
    """지그재그 리뷰 수집 (통일 형식)"""
    driver = setup_driver()
    # 리뷰 탭으로 강제 이동
    review_url = f"{product_url}?tab=review" if '?' not in product_url else f"{product_url}&tab=review"
    collected_reviews = {} # 중복 방지용
    
    try:
        print(f"[정보] 지그재그 상품 리뷰 수집 시작: {review_url}")
        driver.get(review_url)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-review-feed-index]")))
        except: pass
        
        time.sleep(2.0)

        scroll_attempts = 0
        no_new_review_count = 0
        last_count = 0
        
        while len(collected_reviews) < max_reviews and scroll_attempts < 50:
            # 1. 화면 내의 모든 '더보기' 버튼 일괄 클릭 (JS)
            driver.execute_script("""
                document.querySelectorAll("p.zds4_s96ru82b").forEach(btn => {
                    if (btn.innerText.includes('더보기')) {
                        btn.click();
                    }
                });
            """)
            time.sleep(0.5)

            # 2. 리뷰 아이템 탐색
            items = driver.find_elements(By.CSS_SELECTOR, "div[data-review-feed-index]")
            new_found_this_round = 0

            for item in items:
                try:
                    review_id = item.get_dom_attribute("data-review-feed-index")
                    if not review_id or review_id in collected_reviews:
                        continue

                    # 내용 추출
                    content_element = item.find_element(By.CSS_SELECTOR, "span.zds4_s96ru81z")
                    full_content = driver.execute_script("""
                        var el = arguments[0];
                        var clone = el.cloneNode(true);
                        var moreBtn = clone.querySelector("p.zds4_s96ru82b");
                        if(moreBtn) moreBtn.remove();
                        return clone.textContent.trim();
                    """, content_element)

                    # 별점
                    try:
                        stars = item.find_elements(By.CSS_SELECTOR, "svg[data-zds-icon='IconStarSolid']")
                        rating = len(stars) if stars else 5
                    except: rating = 5
                    
                    # 날짜
                    try:
                        date_raw = item.find_element(By.CSS_SELECTOR, "p.zds4_s96ru82j").get_attribute('textContent').strip()
                        review_date = normalize_date(date_raw)
                    except: review_date = ""

                    # 이미지
                    images = [img.get_dom_attribute("src") for img in item.find_elements(By.CSS_SELECTOR, "img[src*='zigzag.kr']")]

                    # 옵션/체형 정보
                    opt_text, h, w = "", None, None
                    sections = item.find_elements(By.CSS_SELECTOR, "div.css-1y13n9")
                    for sec in sections:
                        try:
                            label = sec.find_element(By.CSS_SELECTOR, "div.zds4_s96ru82b[style*='quaternary']").get_attribute('textContent').strip()
                            value = sec.find_element(By.CSS_SELECTOR, "div.zds4_s96ru82b[style*='tertiary']").get_attribute('textContent').strip()
                            
                            if "옵션" in label:
                                opt_text = value.replace('\n', ' ')
                            elif "정보" in label:
                                h, w = parse_height_weight(value)
                        except: continue

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
                    if len(collected_reviews) >= max_reviews: break
                except: continue

            print(f"   -> 지그재그 현재 {len(collected_reviews)}개 확보 중... (신규: {new_found_this_round})")

            # 조기 종료 로직
            current_count = len(collected_reviews)
            if current_count == last_count:
                no_new_review_count += 1
                if no_new_review_count >= 5 and scroll_attempts >= 10:
                    print(f"[정보] 더 이상 리뷰 없음. 총 {current_count}개 수집 완료")
                    break
            else:
                no_new_review_count = 0
            
            last_count = current_count

            # 3. 스크롤 전략
            if new_found_this_round == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
            else:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", items[-1])
                    time.sleep(0.8)
                except:
                    driver.execute_script("window.scrollBy(0, 1000);")

            scroll_attempts += 1

        return list(collected_reviews.values())[:max_reviews]

    finally:
        driver.quit()