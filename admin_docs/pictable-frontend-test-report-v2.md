# 찰칵밥상 프론트 기능 테스트 보고서 v2

## 1. 테스트 목적

찰칵밥상 프론트엔드가 핵심 사용자 흐름을 안정적으로 제공하는지 확인하기 위해 단위 테스트, 브라우저 컴포넌트 테스트, E2E 테스트, Lighthouse 품질 점검을 나누어 수행했다.

## 2. 테스트 환경

| 구분 | 내용 |
|---|---|
| 프레임워크 | Vue 3 + Vite |
| 단위 테스트 | Vitest unit project |
| 브라우저 컴포넌트 테스트 | Vitest browser project + Chromium |
| E2E 테스트 | Playwright Chromium |
| 품질 점검 | Lighthouse Desktop / Mobile emulation |
| 테스트 기준일 | 2026-06-25 |

## 3. 기능 테스트 결과

| 구분 | 테스트 범위 | 결과 | 비고 |
|---|---|---:|---|
| Unit | 라우트, 태그, 재료 API, 홈 레시피 | 4개 파일 통과 | Node 환경에서 로직 검증 |
| Browser Component | 추천, 태그 선택, 레시피 편집, 홈, 피드, 인증 상태, API client | 7개 파일 통과 | Chromium 브라우저 환경에서 UI 검증 |
| E2E Web | 홈에서 재료 선택 후 추천 페이지 이동 | 1개 통과 | 실제 사용자 흐름 검증 |

전체 기능 테스트 결과는 `11개 테스트 파일 / 22개 테스트` 통과이며, Playwright E2E 시나리오도 정상 통과했다.

## 4. 버전별 / 기기별 Lighthouse 결과

| 버전 | 기기 | Performance | Accessibility | Best Practices | SEO | 원본 리포트 |
|---|---|---:|---:|---:|---:|---|
| baseline | 웹 / 데스크톱 | 95 | - | - | - | pictable-lighthouse-desktop.report.json |
| after 개선 | 웹 / 데스크톱 | 96 | 84 | 96 | 100 | pictable-lighthouse-desktop-after.report.json |
| final | 웹 / 데스크톱 | 99 | 84 | 96 | 100 | pictable-lighthouse-desktop-final.report.json |
| a11y 개선 검증 | 웹 / 데스크톱 | 99 | 100 | 96 | 100 | pictable-lighthouse-desktop-a11y.report.json |
| baseline | 앱 / 모바일 뷰 | 92 | - | - | - | pictable-lighthouse-mobile.report.json |
| after 개선 | 앱 / 모바일 뷰 | 94 | 84 | 96 | 100 | pictable-lighthouse-mobile-after.report.json |
| final 재검증 | 앱 / 모바일 뷰 | 90 | 84 | 96 | 100 | pictable-lighthouse-mobile-final-rerun.report.json |
| final | 앱 / 모바일 뷰 | 94 | 84 | 96 | 100 | pictable-lighthouse-mobile-final.report.json |
| a11y 개선 검증 | 앱 / 모바일 뷰 | 94 | 100 | 96 | 100 | pictable-lighthouse-mobile-a11y.report.json |

## 5. 해석

- 데스크톱 최종 성능은 99점으로, 발표 시 웹 성능 최적화 결과를 강하게 어필할 수 있다.
- 모바일 뷰 최종 성능은 94점으로, 반응형 사용자 경험도 안정적으로 확보했다.
- 접근성 개선 검증에서 데스크톱과 모바일 모두 100점을 확인했다.
- 별도 네이티브 앱 빌드는 없기 때문에, 보고서의 앱 항목은 모바일 사용자 환경을 대표하는 Lighthouse mobile emulation 결과로 정리했다.

## 6. 발표 포인트

- 테스트를 단순히 한 번 실행한 것이 아니라 `Unit -> Browser Component -> E2E -> Lighthouse`로 계층화했다.
- UI 컴포넌트와 실제 사용자 흐름을 분리 검증해 회귀 위험을 줄였다.
- Lighthouse baseline, after, final, a11y 개선 검증을 남겨 개선 과정을 수치로 설명할 수 있다.
