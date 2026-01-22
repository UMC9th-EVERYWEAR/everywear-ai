#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### MySQL DB 연결 및 저장 로직 ###
####################################

import pymysql
import os
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
import json


def get_db_connection():
    """
    MySQL DB 연결 생성
    환경변수에서 DB 접속 정보 가져오기
    """
    database_url = os.getenv('DATABASE_URL', '')
    
    if database_url:
        # URL 파싱: mysql://user:password@host:port/database?charset=utf8mb4
        parsed = urlparse(database_url)
        
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        user = parsed.username or 'root'
        password = parsed.password or ''
        # path는 /database 형태이므로 앞의 / 제거
        database = parsed.path.lstrip('/') if parsed.path else 'everywear'
        
        # 쿼리 파라미터에서 charset 추출 (있으면 사용, 없으면 기본값)
        query_params = parse_qs(parsed.query)
        charset = query_params.get('charset', ['utf8mb4'])[0]
    else:
        # DATABASE_URL이 없으면 개별 환경변수 사용 (로컬 개발용)
        host = os.getenv('DB_HOST', 'localhost')
        port = int(os.getenv('DB_PORT', '3306'))
        database = os.getenv('DB_NAME', 'everywear')
        user = os.getenv('DB_USER', 'root')
        password = os.getenv('DB_PASSWORD', '')
        charset = 'utf8mb4'
    
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset=charset,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    return connection


def save_reviews_only(product_id: int, reviews_data: List[dict]) -> dict:
    """
    리뷰 데이터만 DB에 저장 (통일된 형식)
    
    Args:
        product_id: 상품 ID (백엔드에서 이미 생성됨)
        reviews_data: 리뷰 리스트 [
            {
                "rating": 5,
                "content": "좋아요",
                "review_date": "2025.01.22",
                "images": ["url1", "url2"],
                "user_height": 170,
                "user_weight": 60,
                "option_text": "FREE"
            }
        ]
    
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
            review_count = 0
            
            if reviews_data:
                # Review 테이블 INSERT (통일된 7개 필드)
                review_sql = """
                    INSERT INTO review (
                        product_id,
                        rating,
                        content,
                        review_date,
                        images,
                        user_height,
                        user_weight,
                        option_text,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                for review in reviews_data:
                    # images는 List[str]를 JSON 문자열로 변환
                    images_json = json.dumps(review.get('images', []), ensure_ascii=False)
                    
                    review_values = (
                        product_id,
                        review.get('rating', 5),
                        review.get('content', ''),
                        review.get('review_date', ''),
                        images_json,
                        review.get('user_height'),  # None 허용
                        review.get('user_weight'),  # None 허용
                        review.get('option_text'),  # None 허용
                        datetime.now(),
                        datetime.now()
                    )
                    
                    cursor.execute(review_sql, review_values)
                    review_count += 1
                
                print(f"✅ Review 저장 완료: {review_count}개")
            
            # 커밋
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


def check_reviews_exist(product_id: int) -> bool:
    """
    해당 상품의 리뷰가 이미 DB에 있는지 확인
    
    Args:
        product_id: 상품 ID
    
    Returns:
        True: 리뷰 있음, False: 리뷰 없음
    """
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(*) as count FROM review WHERE product_id = %s"
            cursor.execute(sql, (product_id,))
            result = cursor.fetchone()
            
            return result['count'] > 0
            
    finally:
        connection.close()