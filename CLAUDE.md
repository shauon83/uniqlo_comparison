# 🛍️ 유니클로 한·일 가격 비교 및 일본 한정 상품 대시보드 웹 앱 제작 요청

웹 브라우저에서 바로 열어서 볼 수 있는 **단일 HTML 파일(`index.html`) 형태의 유니클로 가격 비교 대시보드 애플리케이션**을 만들어 주세요.

이 사이트는 **일본 유니클로(Uniqlo JP)**와 **한국 유니클로(Uniqlo KR)** 온라인 매장의 동일 제품 가격(할인 행사 적용가 포함) 및 환율 차액을 비교하고, **일본에서만 판매하는 한정 상품**을 별도로 모아볼 수 있는 대시보드입니다.

---

## 🎯 핵심 요구사항 Summary

1. **단일 HTML 파일 구성**: HTML, CSS(Tailwind CSS CDN 활용), JavaScript(Vanilla JS 또는 Vue.js 3 CDN)를 단 1개의 HTML 파일 내에 모두 포함해 주세요.
2. **유니클로 브랜드 디자인**: 유니클로 특유의 미니멀하고 깔끔한 신문/잡지 스타일 UI를 반영해 주세요. (메인 포인트 컬러: 유니클로 레드 `#E60012`, 연연한 회색 배경, 명확한 타이포그래피)
3. **환율 실시간 계산 기능**: JPY $\rightarrow$ KRW 환율을 사용자가 직접 수정하거나 기본 적용할 수 있는 입력창을 제공해 주세요. (기본값 예시: 100 JPY = 900 KRW)
4. **더미 데이터(Sample Data) 내장**: 최소 8~10개 이상의 현실적인 유니클로 인기도 높은 상품(히트텍, 울트라라이트다운, 에어리즘, 감탄팬츠 등)의 한·일 가격 정보와 할인 상태, 그리고 3~4개의 **일본 한정(Japan Exclusive)** 상품 데이터를 JSON 형태로 스크립트에 내장해 주세요.

---

## 🎨 화면 구조 및 주요 기능

### 1. 헤더 & 환율 설정 바 (Header & Exchange Rate Bar)
* **타이틀**: UNIQLO Price Compare (유니클로 한·일 가격 비교)
* **환율 계산기**: 100엔당 원화 환율 입력 필드 (예: `[ 900 ]` 원/100엔 입력 시 실시간으로 한국 가격 대비 일본 가격 환산 및 차액 계산)
* **요약 카운터**: 
  * 비교 중인 동일 상품 수
  * 평균 일본 직구/구매 시 절약 비율 (%)
  * 일본 한정 상품 수

### 2. 필터 및 탭 전환 (Filter & Tab Navigation)
* **탭 메뉴**:
  1. 📊 전체 비교 (Same Products Comparison)
  2. 🏷️ 할인 중인 상품만 (On Sale)
  3. 🇯🇵 일본 한정 상품 (Japan Exclusives)
* **검색 & 분류**: 상품명 검색창, 카테고리 필터 (Outer, Tops, Bottoms, Innerwear 등)

### 3. 메인 콘텐츠 섹션 (Main Content Grid & Table)

#### A. 동일 상품 비교 카드/테이블뷰 (Product Comparison)
각 상품 카드는 아래 정보를 한눈에 볼 수 있게 표시해야 합니다.
* **상품 이미지**: 고화질 유니클로 스타일 썸네일 이미지 (Placeholder 또는 Unsplash 패션 이미지 URL 활용)
* **상품명**: 한국어 상품명 / 일본어(한자/가타카나) 상품명 동시 표시
* **가격 비교 박스**:
  * **일본 가격 (JPY)**: 정가 및 현재 세일가 ($\yen$), 세일 시 `SALE` 뱃지 및 할인율 표시
  * **한국 가격 (KRW)**: 정가 및 현재 세일가 ($\text{₩}$), 세일 시 `SALE` 뱃지 표시
  * **환율 환산 비교**: 일본 세일가를 원화로 환산한 금액 vs 한국 세일가
  * **차액 뱃지**: "일본이 $\text{₩}X,XXX$ 더 저렴 (XX% 절약)" 형태의 직관적인 초록색/레드 뱃지 표시

#### B. 일본 한정 상품 전용 섹션 (Japan Exclusives)
* 일본 매장/온라인몰에서만 판매되고 한국에는 미출시된 상품들 모아보기
* **특징**: "🇯🇵 일본 한정" 전용 뱃지, 일본 엔화 가격($\yen$) 및 환산 원화 가격($\text{₩}$), 상품 특징 요약 태그(예: *구라시키 데님*, *콜라보 UT*, *특수 사이즈* 등)

---

## 💡 샘플 데이터 구조 예시 (JavaScript 내장용)

```json
[
  {
    "id": "item-01",
    "name_kr": "울트라 라이트 다운 재킷",
    "name_jp": "ウルトラライトダウンジャケット",
    "category": "Outer",
    "image": "https://images.unsplash.com/photo-1544441893-675973e31985?w=500&q=80",
    "jp_price": 6990,
    "jp_sale_price": 5990,
    "kr_price": 79900,
    "kr_sale_price": 69900,
    "is_jp_exclusive": false,
    "jp_link": "#",
    "kr_link": "#"
  },
  {
    "id": "item-jp-only-01",
    "name_kr": "[일본한정] 린넨 블렌드 오픈컬러 셔츠 (특수 컬러)",
    "name_jp": "リネンブレンドオープンカラーシャツ (限定色)",
    "category": "Tops",
    "image": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&q=80",
    "jp_price": 2990,
    "jp_sale_price": 1990,
    "kr_price": null,
    "kr_sale_price": null,
    "is_jp_exclusive": true,
    "jp_link": "#",
    "tags": ["일본 매장 한정", "2026 S/S 신상"]
  }
]
```

---

## 🛠️ 기술 스택 및 구현 조건

1. **CSS**: `<script src="https://cdn.tailwindcss.com"></script>` 적용
2. **Icons**: Lucide Icons CDN 또는 FontAwesome CDN 적용
3. **JS 로직**:
   * 환율 변경 시 화면에 표시되는 모든 엔화 환산 원화 금액과 차액이 즉시 재계산되어 업데이트되어야 합니다.
   * 탭 클릭 및 검색 시 필터링이 부드럽게 작동해야 합니다.
   * 반응형 웹(Mobile / Tablet / Desktop) 지원.

완벽하게 작동하는 단일 `index.html` 코드를 작성해 주세요!