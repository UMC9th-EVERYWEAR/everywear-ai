#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#####################################
# FastAPI 서버 - 상품/리뷰 크롤링 API #
#####################################

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import sys
import os
import asyncio

# scripts 폴더의 크롤링 모듈 import
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# 상품 크롤링 모듈
try:
    from crawl_musinsa import crawl_product_details as crawl_musinsa_product
    from crawl_zigzag import crawl_product_details as crawl_zigzag_product
    from crawl_29cm import crawl_product_details as crawl_29cm_product
    from crawl_wconcept import crawl_product_details as crawl_wconcept_product
except ImportError as e:
    print(f"상품 크롤링 모듈 import 실패: {e}", file=sys.stderr)
    raise

# 리뷰 크롤링 모듈
try:
    from crawl_musinsa_reviews import extract_product_no_from_url, collect_reviews
    from crawl_zigzag_reviews import crawl_zigzag_reviews
    from crawl_29cm_reviews import extract_item_id_from_url, collect_29cm_reviews
    from crawl_wconcept_reviews import collect_wconcept_reviews
except ImportError as e:
    print(f"리뷰 크롤링 모듈 import 실패: {e}", file=sys.stderr)
    raise

# DB 핸들러
try:
    from db_handler import get_db_connection
except ImportError as e:
    print(f"DB 핸들러 import 실패: {e}", file=sys.stderr)
    raise

app = FastAPI(
    title="EveryWear AI API",
    version="1.0.0",
    root_path="/crawler"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# Request/Response 모델
# ========================================

class CrawlRequest(BaseModel):
    product_url: str

class ReviewCrawlRequest(BaseModel):
    product_url: str
    review_count: Optional[int] = 20

class UnifiedReviewCrawlRequest(BaseModel):
    product_id: int
    product_url: str
    shoppingmall_name: str
    review_count: int = 20

class CrawlResponse(BaseModel):
    shoppingmall_name: str
    product_url: str
    category: str
    product_img_url: str
    product_name: str
    brand_name: str
    price: str
    star_point: Optional[float] = None
    AI_review: Optional[str] = None

# ========================================
# 헬스체크
# ========================================

@app.get("/")
async def root():
    return {"message": "EveryWear AI API Server", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ========================================
# 상품 크롤링 API (기존)
# ========================================

def _normalize_star_point(result: dict) -> Optional[float]:
    star_point = result.get('star_point')
    if star_point is None:
        return None
    if isinstance(star_point, str):
        try:
            return float(star_point)
        except (ValueError, TypeError):
            return None
    if isinstance(star_point, (int, float)):
        return float(star_point)
    return None

@app.post("/crawl/musinsa", response_model=CrawlResponse)
async def crawl_musinsa(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_musinsa_product, request.product_url)
        star_point = _normalize_star_point(result)
        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', '무신사'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/zigzag", response_model=CrawlResponse)
async def crawl_zigzag(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_zigzag_product, request.product_url)
        star_point = _normalize_star_point(result)
        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', '지그재그'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/29cm", response_model=CrawlResponse)
async def crawl_29cm(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_29cm_product, request.product_url)
        star_point = _normalize_star_point(result)
        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', '29CM'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/wconcept", response_model=CrawlResponse)
async def crawl_wconcept(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_wconcept_product, request.product_url)
        star_point = _normalize_star_point(result)
        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', 'W컨셉'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")

# ========================================
# 개별 리뷰 크롤링 API (기존 - 유지)
# ========================================

@app.post("/crawl/musinsa/reviews")
async def crawl_musinsa_reviews_endpoint(request: ReviewCrawlRequest):
    try:
        goods_no = extract_product_no_from_url(request.product_url)
        if not goods_no:
            raise HTTPException(status_code=400, detail="상품번호를 추출할 수 없습니다.")
        reviews = collect_reviews(goods_no, target_total=request.review_count)
        return {
            "product_no": goods_no,
            "product_url": request.product_url,
            "total_reviews": len(reviews),
            "reviews": reviews
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/zigzag/reviews")
async def crawl_zigzag_reviews_endpoint(request: ReviewCrawlRequest):
    try:
        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(crawl_zigzag_reviews, request.product_url, max_reviews)
        return {
            "product_url": request.product_url,
            "total_reviews": len(reviews),
            "reviews": reviews
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/29cm/reviews")
async def crawl_29cm_reviews_endpoint(request: ReviewCrawlRequest):
    try:
        item_id = extract_item_id_from_url(request.product_url)
        if not item_id:
            raise HTTPException(status_code=400, detail="상품 ID를 추출할 수 없습니다.")
        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(collect_29cm_reviews, request.product_url, max_reviews)
        return {
            "item_id": item_id,
            "product_url": request.product_url,
            "total_reviews": len(reviews),
            "reviews": reviews
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/wconcept/reviews")
async def crawl_wconcept_reviews_endpoint(request: ReviewCrawlRequest):
    try:
        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(collect_wconcept_reviews, request.product_url, max_reviews)
        if not reviews:
            raise HTTPException(status_code=404, detail="해당 상품의 리뷰를 찾을 수 없습니다.")
        return {
            "product_url": request.product_url,
            "total_reviews": len(reviews),
            "reviews": reviews
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

# ========================================
# 통합 리뷰 크롤링 API (신규 - 백그라운드)
# ========================================

@app.post("/crawler/review/crawl")
async def crawl_reviews_unified(request: UnifiedReviewCrawlRequest, background_tasks: BackgroundTasks):
    """
    통합 리뷰 크롤링 API
    - 모든 쇼핑몰 지원
    - 백그라운드에서 크롤링 후 DB 직접 저장
    """
    background_tasks.add_task(
        _crawl_and_save_reviews,
        request.product_id,
        request.product_url,
        request.shoppingmall_name,
        request.review_count
    )
    
    return {
        "status": "started",
        "product_id": request.product_id
    }

async def _crawl_and_save_reviews(product_id: int, url: str, shoppingmall: str, count: int):
    """
    백그라운드에서 리뷰 크롤링 및 DB 저장
    """
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            # 1. Product 상태 업데이트 (PROCESSING)
            cursor.execute(
                "UPDATE product SET review_crawl_status='PROCESSING' WHERE product_id=%s",
                (product_id,)
            )
            connection.commit()
            print(f"[INFO] 리뷰 크롤링 시작: product_id={product_id}, shoppingmall={shoppingmall}")
            
            # 2. 쇼핑몰별 크롤링
            reviews = []
            if shoppingmall == "무신사":
                goods_no = extract_product_no_from_url(url)
                if goods_no:
                    reviews = await asyncio.to_thread(collect_reviews, goods_no, count)
                else:
                    raise ValueError("무신사 상품번호 추출 실패")
                    
            elif shoppingmall == "지그재그":
                reviews = await asyncio.to_thread(crawl_zigzag_reviews, url, count)
                
            elif shoppingmall == "29CM":
                reviews = await asyncio.to_thread(collect_29cm_reviews, url, count)
                
            elif shoppingmall == "W컨셉":
                reviews = await asyncio.to_thread(collect_wconcept_reviews, url, count)
                
            else:
                raise ValueError(f"지원하지 않는 쇼핑몰: {shoppingmall}")
            
            print(f"[INFO] 크롤링 완료: {len(reviews)}개 리뷰 수집")
            
            # 3. DB 저장
            for review in reviews:
                _save_review_to_db(cursor, product_id, review, shoppingmall)
            
            connection.commit()
            
            # 4. Product 상태 업데이트 (COMPLETED)
            cursor.execute(
                "UPDATE product SET review_crawl_status='COMPLETED' WHERE product_id=%s",
                (product_id,)
            )
            connection.commit()
            
            print(f"✅ 리뷰 크롤링 완료: product_id={product_id}, count={len(reviews)}")
            
    except Exception as e:
        print(f"❌ 리뷰 크롤링 실패: product_id={product_id}, error={str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE product SET review_crawl_status='FAILED' WHERE product_id=%s",
                    (product_id,)
                )
                connection.commit()
        except Exception as db_error:
            print(f"❌ 상태 업데이트 실패: {str(db_error)}")
            
    finally:
        connection.close()

def _save_review_to_db(cursor, product_id: int, review: dict, shoppingmall: str):
    """
    쇼핑몰별 리뷰 데이터를 통일된 형식으로 DB에 저장
    """
    try:
        if shoppingmall == "무신사":
            review_sql = """
                INSERT INTO review (
                    product_id, star_point, review_contact, review_date,
                    user_height, user_weight, option_text, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(review_sql, (
                product_id,
                float(review.get('score', 0)),
                review.get('content', ''),
                review.get('date', ''),
                review.get('user_info', {}).get('height', ''),
                review.get('user_info', {}).get('weight', ''),
                review.get('option', '')
            ))
            review_id = cursor.lastrowid
            
            # 이미지 저장
            for img_url in review.get('images', []):
                cursor.execute(
                    "INSERT INTO reviewPhoto (review_id, photo_url) VALUES (%s, %s)",
                    (review_id, img_url)
                )
        
        elif shoppingmall == "지그재그":
            review_sql = """
                INSERT INTO review (
                    product_id, star_point, review_contact, review_date,
                    user_height, user_weight, option_text, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(review_sql, (
                product_id,
                float(review.get('star_rating', 0)),
                review.get('review_content', ''),
                review.get('review_date', ''),
                '',
                '',
                review.get('satisfaction', {}).get('option', '')
            ))
            review_id = cursor.lastrowid
            
            for img_url in review.get('review_images', []):
                cursor.execute(
                    "INSERT INTO reviewPhoto (review_id, photo_url) VALUES (%s, %s)",
                    (review_id, img_url)
                )
        
        elif shoppingmall == "29CM":
            review_sql = """
                INSERT INTO review (
                    product_id, star_point, review_contact, review_date,
                    user_height, user_weight, option_text, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(review_sql, (
                product_id,
                float(review.get('rating', 0)),
                review.get('content', ''),
                review.get('date', ''),
                review.get('user_info', {}).get('height', ''),
                review.get('user_info', {}).get('weight', ''),
                review.get('option', '')
            ))
            review_id = cursor.lastrowid
            
            for img_url in review.get('images', []):
                cursor.execute(
                    "INSERT INTO reviewPhoto (review_id, photo_url) VALUES (%s, %s)",
                    (review_id, img_url)
                )
        
        elif shoppingmall == "W컨셉":
            review_sql = """
                INSERT INTO review (
                    product_id, star_point, review_contact, review_date,
                    user_height, user_weight, option_text, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(review_sql, (
                product_id,
                float(review.get('score', 0)),
                review.get('content', ''),
                review.get('date', ''),
                '',
                '',
                review.get('option', '')
            ))
            review_id = cursor.lastrowid
            
            for img_url in review.get('images', []):
                cursor.execute(
                    "INSERT INTO reviewPhoto (review_id, photo_url) VALUES (%s, %s)",
                    (review_id, img_url)
                )
                
    except Exception as e:
        print(f"[ERROR] 리뷰 저장 실패: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)