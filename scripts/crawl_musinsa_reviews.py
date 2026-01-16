#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 무신사 리뷰 크롤링 (셀레니움 강화 버전) ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

def setup_driver():
    """Chrome WebDriver 설정 (봇 감지 우회 및 최적화)"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def extract_product_no_from_url(url: str) -> Optional[str]:
    """URL에서 상품번호 추출 (공유 URL 및 일반 URL 대응)"""
    if 'onelink.me' in url or 'musinsa.link' in url:
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            url = response.url
        except: return None
    
    match = re.search(r'/products/(\d+)', url)
    return match.group(1) if match else None

def collect_reviews(goods_no: str, target_total: int = 20) -> List[Dict]:
    """
    DOM Recycling을 극복하기 위해 마지막 요소를 추적하며 스크롤 수집
    """
    driver = setup_driver()
    # 전체 리뷰 보기 URL (정렬: 도움순)
    review_url = f"https://www.musinsa.com/review/goods/{goods_no}?sort=up_cnt_desc"
    
    collected_reviews = {} # {content_id: review_data} 형태의 중복 방지 저장소
    
    try:
        print(f"[정보] 무신사 상품번호 {goods_no} 리뷰 수집 시작...")
        driver.get(review_url)
        
        # 페이지 본문 로드 대기
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        scroll_attempts = 0
        max_attempts = 50 # 충분한 스크롤 시도 횟수 설정

        while len(collected_reviews) < target_total and scroll_attempts < max_attempts:
            # 현재 화면(DOM)에 존재하는 리뷰 노드들 획득
            items = driver.find_elements(By.CSS_SELECTOR, "div.gtm-impression-content")
            
            if not items:
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)
                scroll_attempts += 1
                continue

            current_batch_new = 0
            for item in items:
                try:
                    # 1. 고유 ID 추출 (중복 체크 핵심)
                    review_id = item.get_attribute("data-content-id")
                    if not review_id or review_id in collected_reviews:
                        continue

                    # 2. 닉네임 및 작성일
                    nickname = item.find_element(By.CSS_SELECTOR, "span[class*='Nickname']").text.strip()
                    date_val = item.find_element(By.CSS_SELECTOR, "span[class*='PurchaseDate']").text.strip()
                    
                    # 3. 별점 (StarsScore 내의 텍스트 숫자 추출)
                    try:
                        score_text = item.find_element(By.CSS_SELECTOR, "div[class*='StarsScore'] span").text.strip()
                        score = int(score_text)
                    except:
                        score = 5

                    # 4. 옵션/체형/만족도 (반복되는 Container 구조 파싱)
                    options_info = item.find_elements(By.CSS_SELECTOR, "div[class*='OptionRow__Container']")
                    survey = {}
                    option_text = ""
                    user_body = {"sex": "미선택", "height": "", "weight": ""}

                    for opt in options_info:
                        spans = opt.find_elements(By.TAG_NAME, "span")
                        if len(spans) < 2: continue
                        label = spans[0].text.strip()
                        value = spans[1].text.strip()
                        
                        if "구매옵션" in label:
                            option_text = value
                        elif "체형정보" in label:
                            parts = [p.strip() for p in value.split('·')]
                            user_body["sex"] = parts[0] if len(parts) > 0 else "미선택"
                            user_body["height"] = parts[1] if len(parts) > 1 else ""
                            user_body["weight"] = parts[2] if len(parts) > 2 else ""
                        elif "만족도" in label:
                            # '사이즈 조금 큼 · 색감 비슷' 구조 파싱
                            s_parts = [s.strip() for s in value.split('·')]
                            for i, s_val in enumerate(s_parts):
                                survey[f"satisfaction_{i}"] = s_val

                    # 5. 리뷰 텍스트 (더보기 이전 텍스트만 가져오거나 전체 구조 선택)
                    content = item.find_element(By.CSS_SELECTOR, "div[class*='ExpandableContent'] span[class*='text-black']").text.strip()

                    # 6. 이미지 URL 리스트
                    images = [img.get_attribute("src") for img in item.find_elements(By.CSS_SELECTOR, "div[class*='ExpandableImageGroup'] img")]

                    # 7. 도움돼요(추천수)
                    try:
                        help_text = item.find_element(By.CSS_SELECTOR, "button[class*='HelpButton'] span").text.strip()
                        help_count = int(re.sub(r'[^0-9]', '', help_text))
                    except:
                        help_count = 0

                    # 딕셔너리에 저장 (ID 기반 자동 중복 제거)
                    collected_reviews[review_id] = {
                        'product_no': goods_no,
                        'review_no': review_id,
                        'content': content,
                        'date': date_val,
                        'score': score,
                        'option': option_text,
                        'user_info': user_body,
                        'satisfaction': survey,
                        'help_count': help_count,
                        'images': images
                    }
                    current_batch_new += 1
                    
                    if len(collected_reviews) >= target_total:
                        break
                        
                except Exception:
                    continue

            print(f"   -> 수집 중: {len(collected_reviews)}개 확보 (새로 발견: {current_batch_new}개)")

            # 8. 스크롤 전략 수정: 
            # 현재 찾은 아이템 중 '가장 마지막 요소'로 화면을 이동시켜 무한 스크롤 트리거
            if items:
                driver.execute_script("arguments[0].scrollIntoView();", items[-1])
                time.sleep(2) # 새 요소가 로드되고 이전 요소가 DOM에서 제거될 시간 부여
            
            scroll_attempts += 1
            
        return list(collected_reviews.values())[:target_total]

    except Exception as e:
        print(f"[오류] 크롤링 중 중단됨: {e}")
        return list(collected_reviews.values())
    finally:
        driver.quit()

if __name__ == "__main__":
    # 테스트 코드
    results = collect_reviews("5685149", 20)
    print(f"\n최종 수집 완료: {len(results)}개")