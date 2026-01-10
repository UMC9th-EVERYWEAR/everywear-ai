#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 무신사 상품 상세 페이지 크롤링 ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
import re
import time


# Chrome WebDriver 설정
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver


# XPath로 요소를 찾아 텍스트 또는 속성값 추출
def extract_text_by_xpath(driver, xpath, wait_time=10, is_attribute=False, attribute_name='src'):
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if is_attribute:
            return element.get_attribute(attribute_name)
        else:
            return element.text.strip()
    except (TimeoutException, NoSuchElementException):
        return "-"


# 무신사 상품 상세 페이지에서 크롤링
def crawl_product_details(url):
    driver = setup_driver()
    
    try:
        print(f"페이지 로딩 중: {url}")
        driver.get(url)
        
        # 페이지 로딩 대기 (JavaScript 렌더링 고려)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='root']"))
        )
        
        # 추가 대기 (동적 콘텐츠 로딩)
        time.sleep(2)
        
        result = {}
        
        # 1. 쇼핑몰 이름
        result['shoppingmall_name'] = "무신사"
        
        # 2. 상품 URL
        result['product_url'] = url
        
        # 3. 카테고리 추출
        category_xpath = "//*[@data-category-name]"
        
        # 카테고리 크롤링이 안 되는 경우가 있어 추가.
        # 카테고리 요소가 나타날 때까지 대기 (headless 모드에서 더 오래 걸릴 수 있음)
        try:
            WebDriverWait(driver, 15).until(
                lambda d: len(d.find_elements(By.XPATH, category_xpath)) > 0
            )
        except TimeoutException:
            pass  # 카테고리 요소가 없을 수도 있으므로 계속 진행
        
        category_elements = driver.find_elements(By.XPATH, category_xpath)
        
        category = "-"
        if category_elements:
            # 모든 카테고리 이름 수집
            category_names = []
            for element in category_elements:
                category_name = element.get_attribute('data-category-name')
                if category_name:
                    category_names.append(category_name)
            
            if category_names:
                # 우선순위에 따라 카테고리 선택
                # 우선순위: 아우터 > 바지 > 상의 > 원피스/스커트 > 기타
                priority_categories = ["아우터", "바지", "상의", "원피스/스커트"]
                
                selected_category_name = None
                for priority_cat in priority_categories:
                    if priority_cat in category_names:
                        selected_category_name = priority_cat
                        break
                
                # 우선순위 카테고리가 없으면 첫 번째 기타 카테고리 사용
                if selected_category_name is None:
                    selected_category_name = category_names[0]
                
                # 카테고리 값에 따라 처리
                if selected_category_name == "아우터":
                    category = "아우터"
                elif selected_category_name == "바지":
                    category = "하의"
                elif selected_category_name == "상의":
                    category = "상의"
                elif selected_category_name == "원피스/스커트":
                    category = "원피스"
                else:
                    category = "기타"
        
        result['category'] = category
        
        # 4. 대표 이미지 추출
        image_xpath = "//*[@id='root']/div[1]/div[1]/div[1]/div[1]/div[1]/div/div[1]/img"
        image_url = extract_text_by_xpath(driver, image_xpath, is_attribute=True, attribute_name='src')
        result['product_img_url'] = image_url if image_url else "-"
        
        # 5. 상품명 추출
        product_name_xpath = "//span[contains(@class, 'text-title_18px_med') and contains(@class, 'font-pretendard') and @data-mds='Typography']"
        product_name_elements = driver.find_elements(By.XPATH, product_name_xpath)
        product_name_texts = [elem.text.strip() for elem in product_name_elements if elem.text.strip()]
        product_name = product_name_texts[-1] if product_name_texts else "-"
        result['product_name'] = product_name
        
        # 6. 브랜드명 추출
        brand_xpath = "//*[@id='root']/div[1]/div[1]/div[5]/div[2]/div/div[1]/div/span"
        brand_name = extract_text_by_xpath(driver, brand_xpath)
        result['brand_name'] = brand_name if brand_name else "-"
        
        # 7. 가격 추출
        price_xpath = "//span[contains(@class, 'text-title_18px_semi') and contains(@class, 'font-pretendard') and @data-mds='Typography']"
        price_elements = driver.find_elements(By.XPATH, price_xpath)
        price_texts = [elem.text.strip() for elem in price_elements if elem.text.strip()]
        price = price_texts[-1] if price_texts else "-"
        result['price'] = price
        
        # 8. 별점 추출
        starpoint_xpath = "//span[contains(@class, 'text-body_13px_med') and contains(@class, 'font-pretendard') and @data-mds='Typography']"
        starpoint_elements = driver.find_elements(By.XPATH, starpoint_xpath)
        starpoint_texts = [elem.text.strip() for elem in starpoint_elements if elem.text.strip()]
        
        starpoint = None
        for text in starpoint_texts:
            try:
                # 텍스트 전체가 숫자와 소수점만으로 구성되어 있는지 확인
                text_stripped = text.strip()
                if re.match(r'^\d+\.?\d*$', text_stripped):
                    value = float(text_stripped)
                    if 0 <= value <= 5:
                        starpoint = value
                        break
            except (ValueError, AttributeError):
                continue

        result['star_point'] = starpoint
        
        # 9. AI 리뷰
        result['AI_review'] = None
        
        return result
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        return {"shoppingmall_name": "무신사", "product_url": url, "category": "-", "product_img_url": "-", "product_name": "-", "brand_name": "-", "price": "-", "star_point": None, "AI_review": None}
        
    finally:
        driver.quit()
