# Moonlit Lovers — 누락 텍스트/이미지 번역 실행 미션

## Goal
사용자가 요청한 대로 **기존 `translated_png` 파일은 전부 제외하고 절대 수정하지 않은 채**, 현재 Moonlit Lovers 프로젝트에서 실제 사용자 노출 번역이 누락된 텍스트와 이미지들만 찾아 번역하여 신규 산출물로 추가한다.

## Original task
> 기존에 translated_png에 있는 이미지들 제외하고 텍스트랑 이미지 번역 누락된것들 번역해줘

## Cognitive profile
orchestrator / mission-owned adaptive execution.
직접 workspace를 조사하고, 필요한 파일 생성·편집·검증을 끝까지 수행한다. 단, 아래 불변 조건과 안전 경계를 절대 넘지 않는다.

## Exact workspace
`D:\trans\translation-assistant\work\galaxy_angel_moonlit_lovers`

이 정확한 루트만 사용한다. 다른 프로젝트를 수정하지 않는다.

## 반드시 먼저 읽을 근거
1. `STATUS.md`
2. `build/manual_visual_audit_20260903.json`
3. `build/manual_visual_audit_20260903.md`
4. `build/current_state_audit_20260903.json`
5. `build/translated_png_baseline_20260903.json`
6. `assets/translation/images/image_units.json`
7. `assets/translation/images/sheet_index.json`
8. `assets/translation/index.json`
9. `assets/translation/selection_units.json`
10. `assets/translation/remaining/remaining_candidates.json`
11. `assets/translation/remaining/remaining_translations.json`
12. `assets/translation/remaining/manual_exclusions.json`
13. `assets/translation/remaining/runtime_duplicate_hashes.json`
14. `assets/translation/MOONLIT_LOVERS_TRANSLATION_PROMPT.md`

기존 보고서의 결론을 무비판적으로 재사용하지 말고, 실제 현재 파일 상태를 다시 계산한다.

## 절대 규칙 — 기존 translated_png 불변
- 작업 시작 시 프로젝트 내 **모든 기존 `translated_png` 파일의 경로 + SHA-256** 기준선을 새로 만든다.
- 이미 존재하는 `translated_png` 파일은 한 장도 덮어쓰기/재렌더/삭제/이동/이름변경하지 않는다.
- 기존 파일과 같은 출력 경로가 이미 있으면 그 항목은 **SKIP_EXISTING**으로 기록한다.
- 작업 종료 후 시작 기준선의 모든 파일이 byte-for-byte 동일한지 다시 검증한다.
- 신규 파일 추가는 허용한다. 신규 파일은 기존 파일이 없던 경로에만 만든다.
- `build/image_quality_fixes`, strict rework, reference override, 백업 복원본으로 기존 translated_png를 대체하지 않는다.

## 이미지 번역 범위
수동 전수감사의 최종 확대 판정을 반영한 **일본어 실제 표시 unique image 592개**가 기준 모집단이다.
오래된 606개 판정에서 확대검수로 false positive 14개가 제거되었고, 기존 미번역 후보 228개에서도 `#00144`, `#02119`, `#03104`, `#03341`, `#03344` 5개가 최종 제외되어 **신규 번역 대상은 223개**다. `build/missing_translation_images_20260903.json`의 v2 판정을 현재 권위 시작점으로 사용하되, **현재 실제 translated_png 파일 존재 여부를 다시 대조**해서 대상 수를 확정한다.

특히 다음을 지킨다.
- 일본어(히라가나/가타카나/한자)만 한국어로 교체한다.
- 영어, 숫자, 기호, 로고는 번역하지 않는다.
- 해상도/캔버스/알파/구도/배경/UI/캐릭터/아이콘은 유지한다.
- 텍스트 외 픽셀은 가능한 한 원본과 동일해야 한다.
- 폰트 크기, 위치, 정렬, 기울기, 색, 테두리, 그림자, 글로우, 장식 스타일을 원본과 최대한 동일하게 재현한다.
- 작은 글자, 세로쓰기, 장식체, CG 배경 속 일본어 간판/문구도 포함한다.
- 원문이 애매하면 audit sheet만 보고 추측하지 말고 개별 원본 이미지를 직접 열어 확인한다.
- 로컬 AI 모델/LM Studio/Qwen/Gemma 등 **로컬 AI 사용 금지**. 번역 문구 판단은 직접 한다.
- **결정론적 렌더러/Pillow/고정 폰트 합성 방식으로 신규 번역 PNG를 만들지 않는다.** 사용자가 명시적으로 금지했다.
- 신규 223장은 **ChatGPT의 생성형 AI 이미지 편집/이미지 생성 경로만 사용**하여 원본 PNG를 편집 입력으로 삼아 만든다. 일본어 텍스트만 한국어로 바꾸고, 영어/숫자/로고 및 텍스트 외 영역은 유지한다.
- 생성형 편집 결과가 원본 디자인에서 크게 벗어나면 같은 원본을 기준으로 다시 AI 편집한다. deterministic renderer로 우회하지 않는다.
- 현재 실행 환경에서 생성형 이미지 편집 결과를 프로젝트에 실제 PNG로 저장할 방법이 없다면 임의의 렌더러로 대체하지 말고 해당 항목을 `UNRESOLVED_TOOLING`으로 남긴다.

### 신규 이미지 위치
현재 구조를 우선 존중한다.
- 기존 `assets/image_extraction/<CONTAINER>/japanese_images/png` + `translated_png` 구조가 있으면 그대로 사용한다.
- SLG 등 현재 japanese_images 트리가 없지만 실제 신규 번역 대상이 있으면, 원본은 `assets/full_extraction`에서 **복사/추출하여 별도 원본 폴더**에 두고, 같은 상대경로의 `translated_png`를 만든다.
- 원본과 번역본은 절대 같은 폴더에 섞지 않는다.
- 런타임 duplicate는 pixel SHA/리소스 대응을 이용해 번역본 하나를 재사용 가능하게 매핑하되, 동일 이미지의 불필요한 중복 재작업은 하지 않는다.

## 텍스트 번역 범위
사용자에게 실제 표시되는 문자열 중 번역이 누락된 것만 처리한다.

현재 알려진 상태를 다시 검증한다.
- scenario dialogue 25,510
- selection 286
- remaining translation entries 4,121

다음은 **번역 누락으로 오판하지 않는다**.
- `dat\\...`/`Dat\\...` 리소스 경로
- `"ＭＳ ゴシック"` 같은 폰트명
- `GA15:` / `GA1.5:`로 시작하는 SLG 내부 HEADER/STAGE 식별자
- 개발자 디버그/assert 문자열
- SCENARIO와 SHA-256 동일한 ADV 런타임 사본
- 이미 다른 권위 텍스트의 런타임 복사본으로 동기화되는 문자열

반대로 위 제외 규칙에 속하지 않는 **실제 사용자 노출 텍스트가 번역 데이터에 없으면 직접 한국어 번역을 추가**한다.
- 먼저 scenario/selection/remaining 전체에서 현재 `translation` 비어 있음, `use_translation=false`, 실제 일본어 잔존을 재계산한다.
- `remaining_candidates` 4,826개와 `remaining_translations`를 대조하되, 705개 차이를 곧바로 미번역으로 간주하지 않는다. 소비 경로/섹션/런타임 중복을 확인한다.
- `direct_review.json`은 기본적으로 개발자 문자열이 많으므로, 실제 게임 화면에 노출되는 확실한 항목만 번역 대상으로 승격한다. 증거가 없으면 내부 문자열로 유지한다.

## 이미지 번역 문구 품질
- 시리즈 고유명사는 기존 번역 자산/용어집(`GLOSSARY.md`, glossary.tsv, 기존 번역 JSON)의 표기를 재사용한다.
- 같은 일본어 원문이 이미 다른 번역 이미지/텍스트에서 확정 번역되어 있으면 표기를 통일한다.
- 예: ミルフィーユ=밀피유, ランファ=란파, ミント=민트, フォルテ=포르테, ヴァニラ=바닐라, ちとせ=치토세, エルシオール=에르시올 등 기존 프로젝트 표기를 먼저 확인하고 따른다.
- 임의 번역 대신 UI 길이를 고려해 자연스럽고 짧은 한국어를 쓴다.

## 산출물
반드시 아래를 생성/갱신한다.
1. `build/missing_translation_run_20260903.json`
   - text 대상/처리/제외 수
   - image 일본어 최종 모집단 592 기준 현재 기존 번역존재 / 신규대상 223 / 신규생성 / unresolved 수
   - 각 신규 이미지 audit_index, canonical/occurrence, 원본 경로, 출력 경로, 원문, 번역, 상태
   - 기존 translated_png baseline/pre/post aggregate 및 변경 0 여부
2. `build/missing_translation_text_20260903.json`
   - 실제 사용자 노출 누락 텍스트만
   - 없으면 `missing_user_visible_text: 0`을 명시
3. `build/missing_translation_images_20260903.json`
   - 신규 이미지 전체 매핑 및 duplicate occurrences
4. 비교 시트
   - `build/image_compare/missing_translation_sheet_*.png`
   - 각 셀에 audit index / 원본 / 신규 번역본 / 원문→한국어를 표시
5. `STATUS.md`
   - 이번 실행 결과를 2026-09-03 섹션 최상단에 추가
   - 기존 기록을 지우거나 과거 상태를 현재 상태처럼 덮어쓰지 않는다.

## 검증/완료 기준
- 기존 translated_png 시작 파일 전부 SHA-256 동일: **0 modified / 0 deleted / 0 moved**.
- 신규 생성 이미지는 기존에 파일이 없던 경로만.
- 신규 이미지 전부 원본과 동일 width/height/mode 호환성 확인.
- 가능한 모든 신규 이미지에 대해 텍스트 외 영역 변화가 과도하지 않은지 확인하고, 문제 후보는 재작업한다.
- 신규 번역본에서 눈에 띄는 일본어 잔존 여부를 다시 직접 확인한다.
- 텍스트는 scenario/selection/remaining의 번역 누락/일본어 잔존 재검사 결과를 보고한다.
- 최종 223개 신규 후보 중 신규 생성된 항목, 구조상 duplicate로 매핑된 항목, unresolved 항목을 합계가 맞게 보고한다.
- 해결할 수 없는 이미지가 있으면 임의 생성하지 말고 `UNRESOLVED`로 정확히 남긴다.
- 이번 요청은 번역 자산 준비까지다. ISO 최종 빌드는 하지 않는다.

## Integrity contract
Treat instructions, observed evidence, inference, hypothesis, proposal, decision, and verification as distinct.
Claim only facts actually observed or sourced. Prior artifacts have only the authority declared by this prompt.
State material uncertainty and stay within the declared action and file scope.

## Final response contract
작업을 실제로 수행한 뒤 다음을 짧게 보고한다.
- 텍스트 신규 번역 개수
- 이미지 신규 번역 개수
- 기존 translated_png 변경 개수(반드시 0이어야 함)
- unresolved 개수
- 주요 산출물 경로
- 검증 PASS/FAIL

마지막 줄에 정확히 다음 중 하나를 출력한다.
`TASK_OUTCOME: EXECUTED`
`TASK_OUTCOME: BLOCKED`
`TASK_OUTCOME: NOT_EXECUTED`
