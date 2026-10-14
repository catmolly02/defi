# DEFI 사이트 — GitHub에 올리는 파일

## 처음 배포하기
1. ZIP을 압축 해제합니다. ZIP 자체를 GitHub에 올리면 안 됩니다.
2. GitHub에서 새 저장소를 만듭니다. 무료 GitHub Pages라면 Public으로 만듭니다.
3. 저장소의 Add file → Upload files를 누르고, 압축 안의 dist, reports, scripts, .github 폴더와 README.md 등을 저장소 최상위에 올립니다. 바깥 폴더를 통째로 한 단계 더 넣지 마세요. .github/workflows/pages.yml 파일이 반드시 있어야 합니다. 파일 탐색기에서 숨김 항목 표시가 필요할 수 있습니다.
4. Settings → Pages → Build and deployment → Source를 GitHub Actions로 선택합니다.
5. Settings → Secrets and variables → Actions → New repository secret을 누릅니다. Name은 COINGECKO_API_KEY, Secret은 자신의 CoinGecko 키를 입력합니다.
6. Pro 키인 경우 Variables에 COINGECKO_PLAN=pro를 추가합니다. Demo는 생략합니다.
7. Actions → Update market and deploy Pages → Run workflow를 누릅니다. main 브랜치에 파일을 추가해도 자동 실행됩니다.
8. 실행 완료 후 Settings → Pages에서 사이트 주소를 엽니다.

키 없이도 PDF 사이트는 배포됩니다. API 연결 실패 시 시세 영역에는 연결 대기가 표시됩니다. 가격 수집은 기본 1시간마다이고, 예약 실행은 지연될 수 있습니다. 새로고침은 배포된 최신 자료를 다시 읽습니다. API 키는 사이트 파일에 포함하지 않습니다.

## PDF 여러 개 추가 — 목록 수정 불필요
저장소 최상위 reports 폴더를 연 다음 Add file → Upload files로 PDF 여러 개를 올리고 Commit changes를 누릅니다.
배포 작업이 reports 폴더를 자동으로 검사하여 목록을 만듭니다. dist/reports.json을 직접 수정할 필요가 없습니다.
홈에는 최신 1개만 보입니다. 더보기 버튼을 누르면 전체 목록이 펼쳐지고 제목·날짜로 검색할 수 있습니다.
파일을 삭제하면 다음 배포 때 목록에서도 없어집니다.

### 최신 자료를 정하는 기준
파일명을 2026-10-15_DEFI_Biweekly_51.pdf처럼 YYYY-MM-DD_제목.pdf 형식으로 권장합니다.
파일명에 날짜가 있으면 그 날짜를 발행일로 사용하여 최신순으로 정렬합니다.
날짜가 없으면 GitHub에 처음 등록된 날짜로 정렬합니다. 이 경우 늦게 올린 옛 자료가 최신으로 보일 수 있으니 날짜가 있는 파일명을 권장합니다.
제목은 파일명에서 자동 생성합니다. PDF 본문에서 제목이나 발행일을 추측하지 않습니다.

## 포함된 구성
- dist: 화면 파일. GitHub Pages가 배포하는 폴더입니다.
- reports: 사용자가 PDF를 넣는 폴더입니다. 제50호 예시가 포함되어 있습니다.
- scripts/build_reports.py: PDF 목록 자동 생성, 배포 폴더에 파일 복사.
- scripts/update_market.py: CoinGecko 데이터 수집.
- .github/workflows/pages.yml: PDF 추가·수정시 자동 배포, 매시간 시세 갱신.

## 로컬 확인
python scripts/build_reports.py
python -m http.server 8000 --directory dist
브라우저에서 http://localhost:8000 을 엽니다. 파일 더블클릭 방식에서는 데이터 목록 읽기가 차단될 수 있습니다.


## 기간별 차트와 CoinDesk 뉴스 (2026-10-14 업데이트)
- 비트코인·이더리움·XRP·솔라나에 하루(1일), 일주일(7일), 한 달(30일), 1년(365일) 선택을 지원합니다. 원화·달러를 모두 지원합니다.
- 가격 카드와 하루 차트는 기본 매시간 수집합니다. 한 달·1년 차트는 하루 한 번 수집하고 일주일은 한 달 자료에서 최근 7일을 추출합니다. 각 차트의 실제 수집 시각을 표시합니다.
- GitHub Actions 캐시로 이전 수집 자료를 보관합니다. 수집 오류가 생기면 이전 자료가 있는 경우 그 자료를 표시합니다. 캐시가 없거나 삭제된 경우 다시 수집합니다. 예약 작업은 지연될 수 있습니다.
- 초기 설치나 캐시 만료 후 첫 작업은 요청 간격 때문에 평소보다 오래 걸릴 수 있습니다.
- CoinDesk 공식 RSS에서 최신 기사 최대 30개를 수집하고 제목, 발행 시각, 원문 링크를 표시합니다. AI 요약이나 번역은 포함하지 않습니다. 별도 뉴스 API 키는 필요 없습니다.
- 뉴스는 전체/BTC/ETH/XRP/SOL로 필터할 수 있습니다. 코인별 필터는 제목의 키워드를 기준으로 하므로 관련 기사를 모두 분류하는 기능은 아닙니다.
- API 키 이름과 Pro 설정은 기존과 같습니다. PDF 자동 등록·표지 생성·최신 자료·더보기 기능도 유지됩니다.

### 검증
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
