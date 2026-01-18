#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 지그재그 상품 리뷰 크롤링 ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


def setup_driver():
    """Chrome WebDriver 설정"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver


def extract_review_data(review_element):
    """개별 리뷰 요소에서 데이터 추출"""
    try:
        review_data = {
            'reviewer_info': {},
            'satisfaction': {},
            'review_content': '',
            'star_rating': None,
            'review_images': [],
            'review_date': None
        }
        
        try:
            nickname = review_element.find_element(By.CSS_SELECTOR, "p.zds4_s96ru823").text.strip()
            review_data['reviewer_info']['nickname'] = nickname if nickname else None
        except:
            review_data['reviewer_info']['nickname'] = None
        
        try:
            star_elements = review_element.find_elements(By.CSS_SELECTOR, "svg[data-zds-icon='IconStarSolid']")
            review_data['star_rating'] = float(len(star_elements)) if star_elements else None
        except:
            review_data['star_rating'] = None
        
        try:
            date = review_element.find_element(By.CSS_SELECTOR, "p.zds4_s96ru82j").text.strip()
            review_data['review_date'] = date if date else None
        except:
            review_data['review_date'] = None
        
        try:
            image_elements = review_element.find_elements(By.CSS_SELECTOR, ".swiper-slide img[src*='review']")
            review_data['review_images'] = [img.get_attribute('src') for img in image_elements if img.get_attribute('src')]
        except:
            review_data['review_images'] = []
        
        try:
            content_element = review_element.find_element(By.CSS_SELECTOR, "span.zds4_s96ru81z")
            content = content_element.text.strip()
            if content.endswith("더보기"):
                content = content[:-3].strip()
            review_data['review_content'] = content if content else ''
        except:
            review_data['review_content'] = ''
        
        try:
            satisfaction_sections = review_element.find_elements(By.CSS_SELECTOR, "div.css-1y13n9")
            
            for section in satisfaction_sections:
                try:
                    labels = section.find_elements(By.CSS_SELECTOR, "div.zds4_s96ru82b")
                    if len(labels) >= 2:
                        label_text = labels[0].text.strip()
                        value_text = labels[1].text.strip()
                        
                        key_mapping = {
                            '옵션': 'option',
                            '사이즈': 'size',
                            '퀄리티': 'quality',
                            '색감': 'color',
                            '정보': 'info'
                        }
                        
                        key = key_mapping.get(label_text, label_text)
                        review_data['satisfaction'][key] = value_text
                except:
                    continue
        except:
            pass
        
        return review_data
        
    except Exception:
        return None


def crawl_zigzag_reviews(url, max_reviews=20):
    """지그재그 상품 리뷰 크롤링"""
    driver = setup_driver()
    
    try:
        # s.zigzag.kr 단축 URL 리다이렉트 처리
        if 's.zigzag.kr' in url or 'zigzag.link' in url:
            try:
                import requests
                response = requests.head(url, allow_redirects=True, timeout=10)
                url = response.url
            except:
                pass
        
        # URL에 tab=review 파라미터 추가 (리뷰 탭으로 바로 이동)
        if '?' in url:
            review_url = f"{url}&tab=review"
        else:
            review_url = f"{url}?tab=review"
        
        driver.get(review_url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(5)
        
        try:
            sort_selectors = [
                "//button[contains(text(), '베스트')]",
                "//button[contains(text(), '인기')]",
                "//button[contains(text(), '추천')]",
                "//select[contains(@class, 'sort')]"
            ]
            
            for selector in sort_selectors:
                try:
                    sort_button = driver.find_element(By.XPATH, selector)
                    driver.execute_script("arguments[0].click();", sort_button)
                    time.sleep(2)
                    break
                except:
                    continue
        except:
            pass
        
        reviews = []
        
        review_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-review-feed-index]")
        
        if not review_elements:
            return []
        
        for i, review_element in enumerate(review_elements[:max_reviews]):
            if i >= max_reviews:
                break
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_element)
                time.sleep(0.5)
                
                review_data = extract_review_data(review_element)
                if review_data and review_data.get('review_content'):
                    reviews.append(review_data)
            except Exception:
                continue
        
        return reviews
        
    except Exception:
        return []
        
    finally:
        driver.quit()