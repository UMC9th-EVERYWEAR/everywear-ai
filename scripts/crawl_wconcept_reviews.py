#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### W concept 상품 상세 페이지 크롤링 ###
####################################
import time
import re
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    return driver

def extract_wconcept_review_data(review_element) -> Dict:
    """사용자가 제공한 HTML 구조 기반 데이터 추출"""
    data = {'score': 0.0, 'option': '', 'user_id': '', 'date': '', 'satisfaction': {}, 'content': '', 'images': []}
    try:
        # 1. 별점 계산 (style="width:100%" 등 추출)
        try:
            star_strong = review_element.find_element(By.CSS_SELECTOR, ".star-grade strong")
            style_str = star_strong.get_attribute('style')
            # 숫자만 추출 (예: width:100% -> 100)
            width_match = re.search(r'width:\s*(\d+)%', style_str)
            if width_match:
                width_val = int(width_match.group(1))
                data['score'] = width_val / 20.0 # 100 -> 5.0, 80 -> 4.0
        except: pass

        # 2. 옵션 및 사용자 정보
        try:
            # "구매옵션 :", "사이즈 정보 :" 텍스트가 포함된 p 태그들 수집
            info_elements = review_element.find_elements(By.CSS_SELECTOR, ".pdt_review_option p")
            data['option'] = " | ".join([el.text.strip() for el in info_elements if el.text.strip()])
        except: pass

        # 3. 작성자 및 날짜
        try:
            info_right = review_element.find_element(By.CLASS_NAME, "product_review_info_right")
            data['user_id'] = info_right.find_element(By.TAG_NAME, "em").text.strip()
            data['date'] = info_right.find_element(By.TAG_NAME, "span").text.strip()
        except: pass

        # 4. 만족도 상세 (사이즈, 색상, 소재)
        try:
            eval_items = review_element.find_elements(By.CSS_SELECTOR, ".product_review_evaluation li")
            for item in eval_items:
                label = item.find_element(By.TAG_NAME, "strong").text.strip()
                val = item.find_element(By.TAG_NAME, "em").text.strip()
                data['satisfaction'][label] = val
        except: pass

        # 5. 리뷰 내용 및 이미지
        try:
            data['content'] = review_element.find_element(By.CLASS_NAME, "pdt_review_text").text.strip()
            imgs = review_element.find_elements(By.CSS_SELECTOR, ".pdt_review_photo img")
            data['images'] = [img.get_attribute('src') for img in imgs if img.get_attribute('src')]
        except: pass

    except Exception as e:
        print(f"[DEBUG] 파싱 에러: {e}")
    return data

def collect_wconcept_reviews(url: str, target_total: int = 20) -> List[Dict]:
    driver = setup_driver()
    all_reviews = []
    current_page = 1
    
    try:
        # 리뷰 섹션으로 직접 이동
        target_url = url if "#review" in url else f"{url}#review"
        driver.get(target_url)
        time.sleep(3)

        while len(all_reviews) < target_total:
            try:
                # 리뷰 행(tr) 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "pdt_review_text"))
                )
                
                # 'pdt_review_text'를 포함하는 tr들 찾기
                rows = driver.find_elements(By.XPATH, "//tr[descendant::p[@class='pdt_review_text']]")
                
                for row in rows:
                    if len(all_reviews) >= target_total: break
                    item = extract_wconcept_review_data(row)
                    # 중복 수집 방지 (user_id와 content 조합으로 체크)
                    if item['content']:
                        all_reviews.append(item)

                if len(all_reviews) >= target_total: break

                # --- 페이지네이션 처리 (사용자가 찾은 구조 적용) ---
                current_page += 1
                try:
                    # id="reviewPageNavigation" 내부에서 title 속성이 다음 페이지 번호인 <a> 태그 찾기
                    pagination_id = "reviewPageNavigation"
                    # title="2", title="3" 등 정확한 번호 매칭
                    next_page_xpath = f"//*[@id='{pagination_id}']//a[@title='{current_page}']"
                    
                    next_page_btn = driver.find_element(By.XPATH, next_page_xpath)
                    
                    # 버튼이 화면에 보이도록 스크롤 후 클릭
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_page_btn)
                    
                    print(f"[INFO] {current_page}페이지 클릭 완료")
                    time.sleep(2.5) # 페이지 로딩 대기
                    
                except NoSuchElementException:
                    print(f"[INFO] {current_page}페이지 버튼을 찾을 수 없어 종료합니다.")
                    break

            except TimeoutException:
                print("[ERROR] 리뷰 로딩 시간 초과")
                break

        return all_reviews
    finally:
        driver.quit()