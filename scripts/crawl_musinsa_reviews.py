#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 무신사 리뷰 크롤링 ###
####################################

import requests
import json
import time
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs


def extract_product_no_from_share_url(share_url: str) -> Optional[str]:
    """
    공유 URL에서 상품번호를 추출합니다.
    예: https://musinsa.onelink.me/ANAQ/g4nadm4c -> 상품번호 추출
    
    Args:
        share_url: 무신사 공유 URL
        
    Returns:
        상품번호 또는 None
    """
    try:
        # 리다이렉트를 따라가서 최종 URL 확인
        response = requests.head(share_url, allow_redirects=True, timeout=10)
        final_url = response.url
        
        print(f"[INFO] 공유 URL: {share_url}")
        print(f"[INFO] 최종 URL: {final_url}")
        
        # URL에서 상품번호 추출
        # 패턴 1: /products/12345
        match = re.search(r'/products/(\d+)', final_url)
        if match:
            return match.group(1)
        
        # 패턴 2: goodsNo=12345 (쿼리 파라미터)
        parsed_url = urlparse(final_url)
        query_params = parse_qs(parsed_url.query)
        if 'goodsNo' in query_params:
            return query_params['goodsNo'][0]
        
        return None
        
    except Exception as e:
        print(f"[ERROR] 상품번호 추출 실패: {e}")
        return None


def extract_product_no_from_url(url: str) -> Optional[str]:
    """
    일반 무신사 URL에서 상품번호를 추출합니다.
    예: https://www.musinsa.com/products/5432652 -> 5432652
    
    Args:
        url: 무신사 상품 URL
        
    Returns:
        상품번호 또는 None
    """
    # 공유 URL인 경우
    if 'onelink.me' in url or 'musinsa.link' in url:
        return extract_product_no_from_share_url(url)
    
    # 일반 URL인 경우
    match = re.search(r'/products/(\d+)', url)
    if match:
        return match.group(1)
    
    # 쿼리 파라미터에서 추출
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if 'goodsNo' in query_params:
        return query_params['goodsNo'][0]
    
    return None


def collect_reviews(goods_no: str, target_total: int = 20) -> List[Dict]:
    """
    특정 상품의 리뷰를 수집합니다.
    
    Args:
        goods_no: 상품 번호
        target_total: 수집할 리뷰 개수 (기본값: 20)
        
    Returns:
        리뷰 데이터 리스트
    """
    all_reviews = []
    page = 0
    has_more = True
    
    print(f"[시작] 상품번호 {goods_no} 리뷰 수집 중...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.musinsa.com/products/{goods_no}',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://www.musinsa.com',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    }
    
    try:
        while has_more and len(all_reviews) < target_total:
            # API 요청
            response = requests.get(
                'https://goods.musinsa.com/api2/review/v1/view/list',
                params={
                    'page': page,
                    'pageSize': 20,
                    'goodsNo': goods_no,
                    'sort': 'up_cnt_desc'
                },
                headers=headers,
                timeout=30
            )
            
            # 응답 확인
            if response.status_code != 200:
                print(f"[ERROR] API 요청 실패: {response.status_code}")
                break
            
            # JSON 파싱
            try:
                json_data = response.json()
            except Exception as e:
                print(f"[ERROR] JSON 파싱 실패: {e}")
                break
            
            # data 필드 확인
            if json_data is None:
                print(f"[ERROR] 응답이 None입니다.")
                break
            
            data = json_data.get('data', {})
            if not data:
                print(f"[ERROR] 'data' 필드가 없습니다. 응답 구조: {list(json_data.keys())}")
                break
            
            review_list = data.get('list', [])
            
            if not review_list:
                print(f"[INFO] 더 이상 리뷰가 없습니다. (페이지 {page})")
                break
            
            # 리뷰 데이터 처리
            for item in review_list:
                if len(all_reviews) >= target_total:
                    break
                
                # 만족도 설문 데이터 처리 (None 안전 처리)
                survey = {}
                satisfaction_data = item.get('reviewSurveySatisfaction') or {}
                questions = satisfaction_data.get('questions') or []
                
                for q in questions:
                    attribute = q.get('attribute', '')
                    answers = q.get('answers') or []
                    answer_text = answers[0].get('answerShortText', '') if answers else ''
                    if attribute:
                        survey[attribute] = answer_text
                
                # 이미지 URL 완성
                images = []
                for img in (item.get('images') or []):
                    image_url = img.get('imageUrl', '')
                    if image_url:
                        # 이미 전체 URL인 경우
                        if image_url.startswith('http'):
                            images.append(image_url)
                        else:
                            images.append(f"https://image.msscdn.net{image_url}")
                
                # 사용자 정보 안전 처리
                user_profile = item.get('userProfileInfo') or {}
                
                # 리뷰 데이터 구성
                review_data = {
                    'product_no': goods_no,
                    'review_no': str(item.get('no', '')),  # 문자열로 변환
                    'content': (item.get('content') or '').strip(),
                    'date': item.get('createDate', ''),
                    'score': int(item.get('grade', 0)),
                    'option': item.get('goodsOption', ''),
                    'user_info': {
                        'sex': user_profile.get('reviewSex', '미선택'),
                        'height': f"{user_profile.get('userHeight', '')}cm" if user_profile.get('userHeight') else '',
                        'weight': f"{user_profile.get('userWeight', '')}kg" if user_profile.get('userWeight') else ''
                    },
                    'satisfaction': survey,
                    'help_count': item.get('likeCount', 0),
                    'images': images
                }
                
                all_reviews.append(review_data)
            
            print(f"   -> 현재 {len(all_reviews)}개 수집됨 (페이지 {page})")
            
            # 다음 페이지 존재 여부 확인
            page_info = data.get('page', {})
            total_pages = page_info.get('totalPages', 1)
            
            if page >= total_pages - 1:
                has_more = False
            
            page += 1
            
            # 차단 방지 딜레이
            time.sleep(0.6)
        
        return all_reviews
        
    except Exception as e:
        print(f"[ERROR] 리뷰 수집 중 오류 발생 (상품번호 {goods_no}): {e}")
        import traceback
        traceback.print_exc()
        return all_reviews