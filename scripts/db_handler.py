#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### MySQL DB 연결 및 저장 로직 ###
####################################

import pymysql
import os
from datetime import datetime
from typing import Dict, List, Optional
import re


def get_db_connection():
    """
    MySQL DB 연결 생성
    환경변수에서 DB 접속 정보 가져오기
    """
    # DB_URL 파싱: jdbc:mysql://host:port/dbname?params
    db_url = os.getenv('DB_URL', '')
    
    # URL에서 정보 추출
    pattern = r'jdbc:mysql://([^:]+):(\d+)/([^?]+)'
    match = re.search(pattern, db_url)
    
    if match:
        host = match.group(1)
        port = int(match.group(2))
        database = match.group(3)
    else:
        # 기본값
        host = os.getenv('DB_HOST', 'localhost')
        port = int(os.getenv('DB_PORT', '3306'))
        database = os.getenv('DB_NAME', 'everywear')
    
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')
    
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    return connection


def save_product_and_reviews(product_info: Dict, reviews_data: Dict) -> Dict:
    """
    상품 정보와 리뷰를 DB에 저장
    
    Args:
        product_info: 상품 정보 (crawl_product_details 결과)
        reviews_data: 리뷰 데이터 (crawl_reviews_from_url 결과)
    
    Returns:
        {
            "product_id": int,
            "status": "saved",
            "review_count": int
        }
    """
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            # 1. Product 테이블에 INSERT
            product_sql = """
                INSERT INTO product (
                    product_url, 
                    product_name, 
                    brand, 
                    price, 
                    star, 
                    product_img_url, 
                    AI_review, 
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 가격에서 숫자만 추출 (예: "29,000원" -> 29000)
            price_str = product_info.get('price', '0')
            price_numeric = int(''.join(filter(str.isdigit, price_str))) if price_str != '-' else 0
            
            product_values = (
                product_info.get('product_url'),
                product_info.get('product_name', '-'),
                product_info.get('brand_name', '-'),
                price_numeric,
                product_info.get('star_point', 0.0),
                product_info.get('product_img_url', '-'),
                None,  # AI_review는 NULL (나중에 백엔드에서 업데이트)
                datetime.now()
            )
            
            cursor.execute(product_sql, product_values)
            product_id = cursor.lastrowid
            
            print(f"✅ Product 저장 완료: product_id={product_id}")
            
            # 2. Review 테이블에 INSERT (여러 개)
            reviews = reviews_data.get('reviews', [])
            review_count = 0
            
            if reviews:
                review_sql = """
                    INSERT INTO review (
                        product_id,
                        star_point,
                        review_contact,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s)
                """
                
                for review in reviews:
                    review_values = (
                        product_id,
                        float(review.get('score', 0)),
                        review.get('content', ''),
                        datetime.now(),
                        datetime.now()
                    )
                    
                    cursor.execute(review_sql, review_values)
                    review_count += 1
                
                print(f"✅ Review 저장 완료: {review_count}개")
            
            # 3. 커밋
            connection.commit()
            
            return {
                "product_id": product_id,
                "status": "saved",
                "review_count": review_count
            }
            
    except Exception as e:
        connection.rollback()
        print(f"❌ DB 저장 실패: {str(e)}")
        raise
        
    finally:
        connection.close()


def check_product_exists(product_url: str) -> Optional[int]:
    """
    상품 URL로 DB에 이미 존재하는지 확인
    
    Returns:
        product_id (있으면) 또는 None (없으면)
    """
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT product_id FROM product WHERE product_url = %s"
            cursor.execute(sql, (product_url,))
            result = cursor.fetchone()
            
            if result:
                return result['product_id']
            return None
            
    finally:
        connection.close()