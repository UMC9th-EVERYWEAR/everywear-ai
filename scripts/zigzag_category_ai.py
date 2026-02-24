######################################
### Gemini API를 이용한 카테고리 분류 ###
######################################

import os
import requests
import json
from typing import Optional


def classify_category_with_gemini(product_name: str) -> str:
    # 환경변수에서 API 키 가져오기
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    # 상품명이 없거나 "-"인 경우 "기타" 반환
    if not product_name or product_name == "-":
        return "기타"
    
    # Gemini API 엔드포인트
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # 요청 페이로드 구성
    prompt = f"""다음 상품명을 보고 이 상품이 다음 다섯 가지 카테고리 중 어느 것에 해당하는지 분류해주세요.

카테고리: 상의, 하의, 아우터, 원피스, 기타

상품명: {product_name}

위 상품명을 분석하여 정확히 하나의 카테고리만 선택하여 응답해주세요. 
응답 형식은 반드시 다음 중 하나만 출력하세요: 상의, 하의, 아우터, 원피스, 기타
다른 설명이나 추가 텍스트 없이 카테고리 이름만 출력해주세요."""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # API 호출
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        # 응답 파싱
        result = response.json()
        
        # 응답에서 카테고리 추출
        if "candidates" in result and len(result["candidates"]) > 0:
            content = result["candidates"][0].get("content", {})
            parts = content.get("parts", [])
            if len(parts) > 0:
                category_text = parts[0].get("text", "").strip()
                
                # 응답에서 카테고리 추출(오류 방지를 위해)
                valid_categories = ["상의", "하의", "아우터", "원피스", "기타"]
                for category in valid_categories:
                    if category in category_text:
                        return category
                
                # 정확한 매칭이 안 되면 첫 번째 단어나 전체 텍스트를 확인함. 공백 제거 후 비교 시도.
                category_text_clean = category_text.replace(" ", "").replace("\n", "")
                if category_text_clean in valid_categories:
                    return category_text_clean
                
                # 여전히 매칭이 안 되면 기본값 반환
                print(f"Gemini API 응답을 파싱할 수 없습니다. 응답: {category_text}, 기본값 '기타' 반환")
                return "기타"
        
        # 응답 구조가 예상과 다를 경우
        print(f"Gemini API 응답 구조가 예상과 다릅니다. 응답: {result}, 기본값 '기타' 반환")
        return "기타"
        
    except requests.exceptions.RequestException as e:
        print(f"Gemini API 호출 중 오류 발생: {str(e)}")
        return "기타"
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Gemini API 응답 파싱 중 오류 발생: {str(e)}")
        return "기타"
    except Exception as e:
        print(f"카테고리 분류 중 예상치 못한 오류 발생: {str(e)}")
        return "기타"
