import requests
import time
import json
from typing import List, Dict

def collect_29cm_reviews_final(item_id: str, target_total: int = 20) -> List[Dict]:
    """
    29CM API를 사용하여 지정된 개수만큼 리뷰를 수집합니다.
    """
    all_reviews = []
    page = 0
    size = 20 
    
    api_url = "https://review-api.29cm.co.kr/api/v4/reviews"
    img_base_url = "https://img.29cm.co.kr"
    
    headers = {
        'authority': 'review-api.29cm.co.kr',
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://www.29cm.co.kr',
        'referer': 'https://www.29cm.co.kr/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    }

    print(f"[정보] 29CM 상품번호 {item_id} 수집 시작 (목표: {target_total}개)")

    try:
        while len(all_reviews) < target_total:
            params = {
                'itemId': item_id,
                'page': page,
                'size': size,
                'sort': 'BEST'
            }
            
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[오류] API 호출 실패: {response.status_code}")
                break
                
            json_data = response.json()
            results = json_data.get('data', {}).get('results', [])
            
            if not results:
                break

            for item in results:
                if len(all_reviews) >= target_total:
                    break
                
                user_size = item.get('userSize') or []
                
                # 수집 데이터 항목 정의
                review_entry = {
                    'review_id': item.get('itemReviewNo'),
                    'user_id': item.get('userId'),
                    'rating': item.get('point'),
                    'content': item.get('contents', '').strip(),
                    'option': ", ".join(item.get('optionValue', [])),
                    'date': item.get('insertTimestamp'),
                    'user_info': {
                        'height': user_size[0] if len(user_size) > 0 else "",
                        'weight': user_size[1] if len(user_size) > 1 else ""
                    },
                    'images': [f"{img_base_url}{f.get('url')}" for f in item.get('uploadFiles', []) if f.get('url')],
                    'is_gift': item.get('isGift') == 'T'
                }
                all_reviews.append(review_entry)

            page += 1
            time.sleep(0.4)

        return all_reviews

    except Exception as e:
        print(f"[예외] {e}")
        return all_reviews

if __name__ == "__main__":
    ITEM_ID = "3437237"
    # 수집 개수를 20개로 설정
    results = collect_29cm_reviews_final(ITEM_ID, target_total=20)
    
    print("\n" + "="*20 + " 수집 데이터 전체 항목 출력 " + "="*20)
    # 모든 항목이 보이도록 JSON 형태로 출력
    print(json.dumps(results, indent=4, ensure_ascii=False))
    print("="*60)
    print(f"최종 수집 개수: {len(results)}개")