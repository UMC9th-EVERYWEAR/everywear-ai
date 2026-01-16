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
import re


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
        
        # 리뷰 작성자 정보 (닉네임) - p.zds4_s96ru823
        try:
            nickname = review_element.find_element(By.CSS_SELECTOR, "p.zds4_s96ru823").text.strip()
            review_data['reviewer_info']['nickname'] = nickname if nickname else None
        except:
            review_data['reviewer_info']['nickname'] = None
        
        # 별점 추출 - 별 아이콘 개수 세기 (IconStarSolid)
        try:
            star_elements = review_element.find_elements(By.CSS_SELECTOR, "svg[data-zds-icon='IconStarSolid']")
            review_data['star_rating'] = float(len(star_elements)) if star_elements else None
        except:
            review_data['star_rating'] = None
        
        # 리뷰 날짜 - p.zds4_s96ru82j
        try:
            date = review_element.find_element(By.CSS_SELECTOR, "p.zds4_s96ru82j").text.strip()
            review_data['review_date'] = date if date else None
        except:
            review_data['review_date'] = None
        
        # 리뷰 이미지 - swiper 내부의 img 태그들
        try:
            image_elements = review_element.find_elements(By.CSS_SELECTOR, ".swiper-slide img[src*='review']")
            review_data['review_images'] = [img.get_attribute('src') for img in image_elements if img.get_attribute('src')]
        except:
            review_data['review_images'] = []
        
        # 리뷰 내용 - span.zds4_s96ru81z (class명이 정확히 일치)
        try:
            content_element = review_element.find_element(By.CSS_SELECTOR, "span.zds4_s96ru81z")
            content = content_element.text.strip()
            # "더보기" 텍스트 제거
            if content.endswith("더보기"):
                content = content[:-3].strip()
            review_data['review_content'] = content if content else ''
        except:
            review_data['review_content'] = ''
        
        # 만족도 정보 추출 (옵션, 사이즈, 퀄리티, 색감, 정보)
        try:
            # 모든 만족도 항목 찾기
            satisfaction_sections = review_element.find_elements(By.CSS_SELECTOR, "div.css-1y13n9")
            
            for section in satisfaction_sections:
                try:
                    # 라벨과 값을 찾기
                    labels = section.find_elements(By.CSS_SELECTOR, "div.zds4_s96ru82b")
                    if len(labels) >= 2:
                        label_text = labels[0].text.strip()
                        value_text = labels[1].text.strip()
                        
                        # 키를 영어로 매핑
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
        
    except Exception as e:
        print(f"리뷰 데이터 추출 중 오류: {str(e)}")
        return None


def crawl_zigzag_reviews(url, max_reviews=20):
    """지그재그 상품 리뷰 크롤링"""
    driver = setup_driver()
    
    try:
        # URL에 tab=review 파라미터 추가 (리뷰 탭으로 바로 이동)
        if '?' in url:
            review_url = f"{url}&tab=review"
        else:
            review_url = f"{url}?tab=review"
        
        print(f"페이지 로딩 중: {review_url}")
        driver.get(review_url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 리뷰가 로딩될 때까지 대기
        time.sleep(5)
        
        # 리뷰 정렬 옵션 선택 시도 (베스트순/최신순 등)
        try:
            # 정렬 버튼 찾기 (여러 패턴 시도)
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
                    print(f"정렬 옵션 선택: {selector}")
                    break
                except:
                    continue
        except:
            print("정렬 옵션을 찾을 수 없어 기본 순서로 진행합니다.")
        
        reviews = []
        
        # 리뷰 컨테이너 찾기 - data-review-feed-index 속성을 가진 div
        review_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-review-feed-index]")
        
        if not review_elements:
            print("리뷰를 찾을 수 없습니다.")
            return []
        
        print(f"총 {len(review_elements)}개의 리뷰 발견")
        
        # 최대 개수만큼 리뷰 추출
        for i, review_element in enumerate(review_elements[:max_reviews]):
            if i >= max_reviews:
                break
            
            try:
                # 리뷰가 화면에 보이도록 스크롤
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_element)
                time.sleep(0.5)
                
                review_data = extract_review_data(review_element)
                if review_data and review_data.get('review_content'):
                    reviews.append(review_data)
                    print(f"리뷰 {len(reviews)} 수집 완료")
                else:
                    print(f"리뷰 {i+1}: 내용이 없어 스킵")
            except Exception as e:
                print(f"리뷰 {i+1} 처리 중 오류: {str(e)}")
                continue
        
        print(f"총 {len(reviews)}개의 리뷰를 수집했습니다.")
        return reviews
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        driver.quit()


if __name__ == "__main__":
    # 테스트
    test_url = "https://zigzag.kr/catalog/products/143224732"
    reviews = crawl_zigzag_reviews(test_url, max_reviews=5)
    
    print("\n=== 수집된 리뷰 ===")
    for i, review in enumerate(reviews, 1):
        print(f"\n[리뷰 {i}]")
        print(f"작성자: {review['reviewer_info'].get('nickname', 'N/A')}")
        print(f"평점: {review.get('star_rating', 'N/A')}")
        print(f"날짜: {review.get('review_date', 'N/A')}")
        print(f"만족도: {review.get('satisfaction', {})}")
        print(f"내용: {review.get('review_content', 'N/A')[:100]}...")
        print(f"이미지 개수: {len(review.get('review_images', []))}")