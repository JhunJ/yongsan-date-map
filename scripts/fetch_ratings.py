#!/usr/bin/env python3
"""Fetch Google / Naver / Kakao ratings for places via browser automation."""
import json, re, time, urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

PLACES = [
    "업스탠딩", "콤포트", "콤포타블 커피 남산점", "포디 서울", "버번스캐빈", "3F LOBBY",
    "자키러브", "빌라커피바", "토크메모리", "빈스미스 커피 로스터스", "유틸리티 커피 로스터스",
    "크놀프", "엔지니어링클럽", "폰트 용산점", "더 체임버 커피", "피어커피 바", "언더트",
    "어프로치커피", "HHSS HOUSE", "괄호", "우이고", "포스트톤즈", "타케모토", "자니덤플링 본관",
    "다로베", "우동 키노야", "미미옥 신용산점", "한땀스시", "오일제", "테디뵈르하우스",
    "그래픽", "PDF 서울", "후지필름 하우스 오브 포토그래피 서울", "푸투라서울",
    "서울시립 사진미술관", "서울문화예술교육센터 용산", "믹상", "나의 아저씨 촬영지",
    "윤슬", "율디세", "젤라또 피케"
]

def parse_google(page, name):
    q = urllib.parse.quote(name + " 서울")
    page.goto(f"https://www.google.com/maps/search/{q}", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(2500)
    text = page.inner_text("body")
    m = re.search(rf"{re.escape(name)}[\s\S]{{0,120}}?([0-9]\.[0-9])", text)
    if not m:
        m = re.search(r"([0-9]\.[0-9])", text)
    count = None
    cm = re.search(r"([0-9]\.[0-9])\s*\(([0-9,]+)\)", text)
    if cm:
        return {"score": float(cm.group(1)), "count": int(cm.group(2).replace(",", ""))}
    if m:
        return {"score": float(m.group(1)), "count": count}
    return None

def parse_naver(page, name):
    q = urllib.parse.quote(name)
    page.goto(f"https://map.naver.com/p/search/{q}", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(3000)
    text = page.inner_text("body")
    # e.g. 4.52 리뷰 1,234 or 별점 4.5
    patterns = [
        r"([0-9]\.[0-9]{1,2})\s*(?:점|/5)?\s*(?:리뷰|후기|평점)\s*([0-9,]+)",
        r"별점\s*([0-9]\.[0-9]{1,2})\s*(?:리뷰|후기)?\s*([0-9,]+)?",
        r"방문자\s*리뷰\s*([0-9,]+)[\s\S]{0,80}?([0-9]\.[0-9]{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            g = m.groups()
            if g[0].replace(".", "").isdigit() and len(g[0]) <= 4:
                score = float(g[0])
                count = int(g[1].replace(",", "")) if len(g) > 1 and g[1] else None
                return {"score": score, "count": count}
    m = re.search(r"\b([4-5]\.[0-9])\b", text)
    if m:
        return {"score": float(m.group(1)), "count": None}
    return None

def parse_kakao(page, name):
    q = urllib.parse.quote(name + " 서울")
    page.goto(f"https://map.kakao.com/?q={q}", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(3000)
    text = page.inner_text("body")
    m = re.search(r"([0-9]\.[0-9])\s*(?:점|\/)?\s*(?:리뷰|후기)?\s*([0-9,]+)?", text)
    if m:
        count = int(m.group(2).replace(",", "")) if m.group(2) else None
        return {"score": float(m.group(1)), "count": count}
    return None

def main():
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        for i, name in enumerate(PLACES):
            print(f"[{i+1}/{len(PLACES)}] {name}")
            entry = {"google": None, "naver": None, "kakao": None}
            try:
                entry["google"] = parse_google(page, name)
            except Exception as e:
                print("  google err", e)
            try:
                entry["naver"] = parse_naver(page, name)
            except Exception as e:
                print("  naver err", e)
            try:
                entry["kakao"] = parse_kakao(page, name)
            except Exception as e:
                print("  kakao err", e)
            out[name] = entry
            print(" ", entry)
            time.sleep(0.8)
        browser.close()
    path = Path(__file__).resolve().parent.parent / "ratings.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", path)

if __name__ == "__main__":
    main()
