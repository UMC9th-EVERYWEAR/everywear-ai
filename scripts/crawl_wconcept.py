####################################
### W컨셉 상품 상세 페이지 크롤링 ###
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


# 여러 XPath를 순차적으로 시도하여 요소 추출 (fallback 처리)
def extract_by_xpath_with_fallback(driver, xpath_list, wait_time=10, is_attribute=False, attribute_name='src'):
    for xpath in xpath_list:
        try:
            element = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            if is_attribute:
                value = element.get_attribute(attribute_name)
            else:
                value = element.text.strip()

            if value:
                return value
        except (TimeoutException, NoSuchElementException):
            continue

    return "-"


# 단일 XPath로 요소 추출
def extract_by_xpath(driver, xpath, wait_time=10, is_attribute=False, attribute_name='src'):
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


# W컨셉 상품 상세 페이지에서 모든 정보 크롤링
def crawl_product_details(url):
    driver = setup_driver()

    try:
        print(f"페이지 로딩 중: {url}")
        driver.get(url)

        # 페이지 로딩 대기 (JavaScript 렌더링 고려)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='frmproduct']"))
        )

        # 추가 대기 (동적 콘텐츠 로딩)
        time.sleep(2)

        result = {}

        # 1. 쇼핑몰 이름
        result['shoppingmall_name'] = "W컨셉"

        # 2. 상품 URL
        result['product_url'] = url

        # 3. 카테고리 추출
        category_xpath_absolute = "//*[@id='cateDepth3']/button"
        category_xpath_relative = "//div[@id='cateDepth3']//button | //button[contains(@class, 'category') or contains(@class, 'cate')]"

        category = extract_by_xpath_with_fallback(
            driver,
            [category_xpath_absolute, category_xpath_relative]
        )

        # 카테고리 분류 로직
        final_category = "기타"  # 기본값

        if category and category != "-":
            category = category.strip()

            if category == "아우터":
                final_category = "아우터"
            elif category == "원피스":
                final_category = "원피스"
            elif category == "블라우스":
                final_category = "상의"
            elif category == "상의":
                final_category = "상의"
            elif category == "셔츠":
                final_category = "상의"
            elif category == "티셔츠":
                final_category = "상의"
            elif category == "니트":
                final_category = "상의"
            elif category == "스커트":
                final_category = "원피스"
            elif category == "팬츠":
                final_category = "하의"
            elif category == "데님":
                final_category = "하의"
            elif category == "라운지웨어":
                final_category = "기타"
            elif category == "언더웨어":
                final_category = "기타"
            else:
                final_category = "기타"

        result['category'] = final_category

        # 4. 대표 이미지 추출
        image_xpath_absolute = "//*[@id='img_01']"
        image_xpath_relative = "//img[@id='img_01'] | //div[@id='img_01']//img[1] | //img[contains(@class, 'main') or contains(@class, 'product')][1]"

        image_url = extract_by_xpath_with_fallback(
            driver,
            [image_xpath_absolute, image_xpath_relative],
            is_attribute=True,
            attribute_name='src'
        )
        # src 속성이 없으면 data-src 또는 다른 이미지 속성 시도
        if not image_url or image_url == "-":
            image_url = extract_by_xpath_with_fallback(
                driver,
                [image_xpath_absolute, image_xpath_relative],
                is_attribute=True,
                attribute_name='data-src'
            )
        result['product_img_url'] = image_url if image_url and image_url != "-" else "-"

        # 5. 상품명 추출
        product_name_xpath_absolute = "//*[@id='frmproduct']/div[1]/div/h3"
        product_name_xpath_relative = "//form[@id='frmproduct']//div[1]//h3 | //div[contains(@class, 'product')]//h3[1]"

        product_name = extract_by_xpath_with_fallback(
            driver,
            [product_name_xpath_absolute, product_name_xpath_relative]
        )
        result['product_name'] = product_name if product_name else "-"

        # 6. 브랜드명 추출
        brand_xpath_absolute = "//*[@id='frmproduct']/div[1]/h2/a"
        brand_xpath_relative = "//form[@id='frmproduct']//h2//a | //div[contains(@class, 'product')]//h2//a[1]"

        brand_name = extract_by_xpath_with_fallback(
            driver,
            [brand_xpath_absolute, brand_xpath_relative]
        )
        result['brand_name'] = brand_name if brand_name else "-"

        # 7. 가격 추출 (두 가지 케이스)
        price_xpath_case1 = "//*[@id='frmproduct']/div[3]/dl/dd[2]/em"
        price_xpath_case2 = "//*[@id='frmproduct']/div[3]/dl/dd/em"
        price_xpath_relative = "//form[@id='frmproduct']//div[3]//dl//dd//em | //div[contains(@class, 'price')]//em | //dl[contains(@class, 'price')]//em"

        price = extract_by_xpath_with_fallback(
            driver,
            [price_xpath_case1, price_xpath_case2, price_xpath_relative]
        )

        # 가격에 "원" 단위 추가 (이미 "원"이 포함되어 있지 않은 경우)
        if price and price != "-":
            price = price.strip()
            numbers = re.findall(r'[\d,]+', price)
            if numbers:
                price_value = max(numbers, key=len)
                if not price_value.endswith('원'):
                    price = price_value + '원'
                else:
                    price = price_value
            else:
                if not price.endswith('원'):
                    price = price + '원'
        else:
            price = "-"

        result['price'] = price

        # 8. 별점 추출
        starpoint_xpath_absolute = "//*[@id='frmproduct']/div[2]/p[2]"
        starpoint_xpath_relative = "//form[@id='frmproduct']//div[2]//p[2] | //div[contains(@class, 'rating') or contains(@class, 'star') or contains(@class, 'review')]//p"

        starpoint = extract_by_xpath_with_fallback(
            driver,
            [starpoint_xpath_absolute, starpoint_xpath_relative]
        )
        # 별점이 "-"이거나 없으면 None, 있으면 float로 변환 시도
        if not starpoint or starpoint == "-":
            result['star_point'] = None
        else:
            try:
                # 숫자 문자열인 경우 float로 변환
                result['star_point'] = float(starpoint)
            except (ValueError, TypeError):
                result['star_point'] = None

        # 9. AI 리뷰
        result['AI_review'] = None

        return result

    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"shoppingmall_name": "W컨셉", "product_url": url, "category": "-", "product_img_url": "-", "product_name": "-", "brand_name": "-", "price": "-", "star_point": None, "AI_review": None}

    finally:
        driver.quit()