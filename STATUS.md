# Galaxy Angel - Moonlit Lovers (PS2) 한글화 진행 상태

갱신: 2026-09-07

## 2026-09-07 영상 자막 검수 완료 + PS2 PSS 27편 생성

문릿 러버즈 `movie/original`의 27개 PSS에 대해 `movie/output`의 원본 추출 M2V/PCM WAV와 검수 완료 한국어 ASS를 사용해 자막 번인 PSS를 생성했다.

- 대상: `GADAT100,101,102,103,106~126,132,133` 총 **27편**.
- 한국어 ASS: **27/27**, FFmpeg/libass 원본 PSS 렌더 검증 **27/27 PASS**.
- 자막 번인 MPEG-2는 각 원본 M2V의 frame-rate code를 자동 감지한다. `GADAT100=30fps`, `GADAT111=30000/1001fps`, 나머지는 원본 값에 따라 처리하며 일괄 24fps로 강제하지 않는다.
- 인코딩: MPEG-2 video, YUV420P, 4:3, 원본 프레임레이트, GOP 약 0.5초, B-frame 2, 5950kbps 목표 / 6000kbps max, VBV 1,835,008 bytes.
- mux: 갤럭시 엔젤에서 실기 검증한 PSS Plex 호환 방식으로 16KiB pack, 새 MPEG-2의 GOP timecode + temporal reference 기준 PTS/DTS, 원본 48kHz stereo PCM WAV를 Sony SShd/SSbd private stream으로 재구성한다.
- 각 PSS 생성 시 비디오 ES exact readback, PCM SS stream exact readback, 16KiB pack alignment를 검증했다.
- 생성 후 27개 PSS를 FFmpeg로 전수 비디오 디코드: **27/27 PASS, 실패 0**.
- 로컬 최종 산출물: `movie/subtitled/final/GADAT*.PSS` 및 대응 `*.m2v`, `*.pss.json`.
- 종합 리포트: `build/moonlit_lovers_subtitled_pss_report.json` (`completed=27`, `requested=27`).
- `movie/`는 원본 게임 데이터와 대용량 재생성 산출물이므로 갤럭시 엔젤 저장소와 동일하게 Git 추적에서 제외하고, 재현 가능한 전사/PSS 도구만 Git에 포함한다.

### v0.1 최종 ISO / XDelta

- 실기 확인에서 영상 자막이 약 1초 빨리 표시되어, 대사가 있는 ASS 22개 / `Dialogue` 124개 전체의 시작·종료를 **+1.00초** 뒤로 이동했다. 빈 ASS 5개(`100/107/108/110/132`)는 그대로 유지했다.
- 타이밍 수정본으로 PSS 27편을 다시 인코딩/mux했고 picture count 및 PSS 검증을 **27/27 PASS**했다.
- 자막 PSS 27편을 기존 한글 `v19` ISO에 ISO9660 LBA/size 갱신 방식으로 삽입했다.
- 기존 무비 풀에 모두 들어가지 않아 `GADAT100`, `GADAT122` 두 파일만 ISO 끝으로 재배치했고, 나머지는 기존 무비 풀 안에서 재패킹했다.
- ISO 내부 27개 PSS를 새 PSS SHA-256과 전수 readback 비교: **27/27 PASS**.
- 최종 ISO: `build/Galaxy_Angel_Moonlit_Lovers_KO_v0.1_SUBTITLED.iso`
  - 크기: `3,606,837,248 bytes`
  - MD5: `f42e8f7c47950d8be92e7907e0d7ef1a`
  - SHA-1: `35aad22f121ef6ebcc3ab241a8f2be6566409eb9`
  - SHA-256: `467f53bf8ac2e3cd71aca4754f1871fccfe225e445acd1be11148365782b45c3`
- 배포 XDelta: `release/galaxy_angel_moonlit_lovers_ps2_kr_v0.1.xdelta`
  - 크기: `460,286,918 bytes`
  - MD5: `7bb9edbb07f64c3ae75405657fc99427`
  - SHA-1: `c31adec74d968cdb3380c5183b178667611c860e`
  - SHA-256: `f8f5d06b719655ece915cdeaae8ddd9d3ed6360740ebe73bd63038274d54ef9f`
- 일본판 원본 ISO SHA-256 `990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe`에 새 v0.1 XDelta를 실제 적용해 최종 ISO와 SHA-256 일치: **PASS**.

## 2026-09-05 폰트 원복 + 화자명 깨짐 수정

실기 스크린샷에서 `택트 → 탕퉁`, `밀피유 → 밀픈위`로 보이고 한글 글꼴 자체도 이전과 달라진 회귀를 확인해 원인을 두 갈래로 분리해 수정했다.

- **폰트 외형 회귀:** 2026-09-04 미션 설명의 시각적 글자 간격을 줄이기 위해 한글 잉크만 1.25배 수평 확대했던 `hangul_horizontal_scale=1.25`가 전체 대화/이름 글꼴에도 적용됐다. 현재 1,209자 매핑은 그대로 유지하고 `1.0`으로 다시 빌드했다.
  - 확대판 ELF SHA-256: `a0c82ef920ece9e4e28d24e28aa2d6d72938d4e00063251544bd1d4c3a1176e1`
  - 수정 ELF SHA-256: `3c170d8375f803ed70745565de22f26c8cd045887af90398146cf2e364bb94f9`
  - 현재 `택`/`트` 글리프를 과거 정상 1.0배 폰트와 각각 PNG로 디코드해 비교했고 **두 글리프 모두 pixel-identical**.
- **화자명 깨짐 원인:** SaveLabel 완결 과정에서 새 한글 4자 `볶`, `빅`, `텃`, `튜`가 사용자 정의 Shift-JIS 정렬 목록에 추가되어 1,205자 → 1,209자가 되면서 뒤쪽 코드가 이동했다. 그런데 v1.5 마지막 화자 패치는 예전 1,205자 맵으로 인코딩된 `speaker.tbl` 바이트를 그대로 transplant했다.
  - 예: 예전 `택=e1fb`, `트=e1de` 바이트는 현재 맵에서 각각 `탕`, `퉁`이므로 화면의 **`탕퉁`이 정확히 재현**된다.
  - 예: 예전 `피=e1a8`, `유=e3f7` 바이트는 현재 맵에서 각각 `픈`, `위`이므로 **`밀픈위`가 정확히 재현**된다.
- 현재 1,209자 `font_map.json`으로 화자명 **48개를 전부 재인코딩**해 GADAT000 정본 1개 + ADV 런타임 사본 2개를 다시 패치했다.
  - 새 화자 테이블 raw SHA-256: `bf76016dfae4f952e4340f98a2d0471bef85894138a79411e5a367235611410f`
  - readback **3/3 PASS**.
- 동시에 v1.5에서 놓쳤던 GADAT000 중앙 `IDX.DAT` 미러도 바로잡았다.
  - speaker tuple: `(offset=98304, raw=902, compressed=650)` → **`(98304, 902, 653)`**
  - 로컬 PIDX와 중앙 IDX가 다시 일치한다.
- 재발 방지: `tools/moonlit_lovers_apply_speaker_patch.py`를 보강했다.
  - 이제 GADAT000/ADV뿐 아니라 **IDX.DAT 1바이트 변경도 transplant**한다.
  - 참조본과 target의 `SLPM_654.29`가 다르면 raw custom-SJIS 화자 transplant를 **즉시 거부**하고 현재 맵으로 재인코딩하도록 안내한다. 실제 잘못된 v1.5 입력 조합으로 self-test해 거부됨을 확인했다.

### 수정본 검증

`build/targeted_verify_font_speaker_fix_20260905.json` → **PASS (`ok=true`)**

- 기존 통합 검증 PASS였던 2026-09-04 v1.5 ISO와 새 ISO를 전체 물리 바이트로 비교했다.
- 변경은 정확히 허용한 4개 물리 영역뿐이다: `SLPM_654.29`, `GADAT000.DAT`, `ADV.DAT`, `IDX.DAT`.
  - SLPM: 73,674 bytes
  - GADAT000: 390 bytes
  - ADV: 780 bytes
  - IDX: 1 byte
  - 합계 **74,845 bytes / 24,931 diff runs**
- 나머지 시나리오/이미지/전투 데이터의 물리 바이트는 2026-09-04 통합 PASS ISO와 동일하다.
- strict decompress: **GADAT000 36/36, ADV 2,395/2,395 PASS**.
- 화자명 정본/런타임: **3/3 PASS**.
- 전체 9컨테이너 통합 verifier 재실행은 300초 도구 제한으로 종료됐지만, 이전 v1.5의 전체 통합 PASS를 기준으로 이번 수정이 위 4개 물리 영역 밖을 전혀 바꾸지 않았음을 별도 전수 비교로 증명했다.

**수정 ISO**
`build/Galaxy_Angel_Moonlit_Lovers_KO_final_20260905.iso`

- 크기: **3,599,241,216 bytes**
- MD5: `d633301bec2c98da47be3321f9f9f543`
- SHA-1: `0ca4ea5bb89c78d23d981beb3f06eacb07fe90b7`
- SHA-256: **`474680b78eead7e68a41d9edc318f89cd513f936bf4f1a0364c041fa8322c6e5`**

## 2026-09-04 텍스트 완결 + 화자명 통합 최종 배포 (v1.5)

v1.4의 현재 이미지 1,403장을 그대로 보존하면서 함내 이동 설명, SaveLabel, 미션 설명 레이아웃/가독성, 화자명 누락을 새 통합본에 반영했다.

- SCENARIO: **25,510 대사 + 286 선택지**, overflow 0
- SaveLabel **446/446**, 미션 레이아웃 override **12/12**
- 함내 이동 TBI: **25 리소스 / 739 문자열 PASS**
- remaining readback: ADV **1/13**, GADAT000 **2/26**, SLG **281/81,223**, SLGRES **81/1,994**, SLGSTAGE **715/192,782** (리소스/문자열)
- ADV 시나리오 런타임 사본 **36/36 PASS**, 재배치 0
- 이미지: GADAT030 **134**, GADAT031 **0**, GADAT032 **398**, SLG **165**, ADV runtime **481/481**
- 전투 bank: SLGRES **295/295**, SLGSTAGE **672/672**, ADV **2/2**, 자동 축소/재렌더 0
- 이미지 권위 기준선: **1,403장**, aggregate `0bf860c3c2513bd562e4bd5d79853aede959bb74378ca3d6d3b8bce500fa2e46`; 종료 재해시 **missing 0 / changed 0**
- 화자명 **48개**: GADAT000 1사본 + ADV 2사본. 최신 ISO 적용 전 충돌 0, `text_complete → final` 전체 차이는 검증된 화자 패치와 정확히 같은 **45구간 / 1,848 bytes**
- 최종 검증: `build/integrated_verify_final_20260904.json` → **PASS (`ok=true`)**
- 최종 ISO: `build/Galaxy_Angel_Moonlit_Lovers_KO_final_20260904.iso`
  - 크기 **3,599,241,216 bytes**
  - MD5 `8fb771d753e6ed687befebf807fb0405`
  - SHA-1 `b3f02f10448c96e672e50a70426c7d62c0888c44`
  - SHA-256 **`2aa070d11f281a64f3d59b5e265215a9161a63b7aae9dd7166e3bd52ad59f7e3`**
- XDelta v1.5: `release/galaxy_angel_moonlit_lovers_ps2_kr_v1.5.xdelta`
  - 크기 **39,314,196 bytes**
  - MD5 `56eacc0dbc544e60e868b093010f266d`
  - SHA-1 `32ece5d13659ff9b9c75bc1fcbde846b25da0733`
  - SHA-256 **`2f8903fb8ee03716f70c2a63e1a9751e5da4ffd91f05759a50a8c71b47752f98`**
- 원본 ISO에 v1.5를 실제 적용한 결과 최종 ISO와 **MD5/SHA-1/SHA-256 전부 일치**. 상세: `build/release_v1.5_verify.json`
- 안전/검증 도구: `tools/moonlit_lovers_apply_speaker_patch.py`, `tools/moonlit_lovers_finalize_verify.py`
- `release/README.txt`, `release/release.json`, `release/SHA256SUMS.txt`는 v1.5 기준으로 갱신. 기존 v1.3/v1.4 패치는 보존한다.

## 2026-09-04 현재 이미지 권위본 보존 재빌드 + 최종 배포 (v1.4)

사용자가 추가 수정한 현재 이미지들을 새 권위본으로 다시 잡고, 빌드 중 이미지 자동 재렌더/자동 축소가 일어나지 않는 보존 경로로 원본 ISO부터 재빌드했다.

- 현재 이미지 기준선: **1,403장**, aggregate SHA-256 `0bf860c3c2513bd562e4bd5d79853aede959bb74378ca3d6d3b8bce500fa2e46`
- 빌드/통합 검증 종료 후 기준선 재대조: **missing 0 / changed 0**
- 최종 통합 검증: `build/integrated_verify_current_images_20260904.json`
  - 시나리오 **25,510 대사 + 286 선택지**, overflow 0
  - 이미지 **532/532 primary PASS**
  - 이미지 runtime copies **481 PASS**
  - SCENARIO / SLG / GADAT030 / GADAT031 / GADAT032 PIDX 중앙 인덱스 전부 complete
  - ADV 2395 / GADAT000 36 / GADAT030 508 / GADAT031 577 / GADAT032 1930 / SCENARIO 177 / SLG 4102 / SLGRES 2677 / SLGSTAGE 9993 strict decompress 전부 PASS
  - ADV / SLGSTAGE FSTS 리소스 수 원본과 동일
- 최종 ISO: `build/Galaxy_Angel_Moonlit_Lovers_KO_current_images_20260904.iso`
  - 크기: **3,599,321,088 bytes**
  - MD5: `4c6da20bc5d5616cdbf179edae19d6f2`
  - SHA-1: `8a4582904948c4ed5e2a83cbf24f1e25567f8e05`
  - SHA-256: **`09bc44d2914cbeeae95029d0c0de3475df2f913b020f694c8ecef25710609bc0`**
- 배포 XDelta: `release/galaxy_angel_moonlit_lovers_ps2_kr_v1.4.xdelta`
  - 크기: **39,342,258 bytes**
  - MD5: `03e071f9e784ced24fc193b8aa2603dd`
  - SHA-1: `6684c192213356cd372c9d514c6067010ffa0648`
  - SHA-256: **`bc567d0c9aa1e10e282fc46d8517a33c919a912cc9f4674b9b1f83049b072ae8`**
- XDelta apply-check: 원본 ISO에 v1.4 패치를 적용한 결과 SHA-256이 최종 ISO와 **byte-for-byte 일치** (`09bc44d2...09bc0`)
- `release/README.txt`, `release/release.json`, `release/SHA256SUMS.txt`를 v1.4 기준으로 갱신했다. 기존 v1.3 패치는 과거 버전으로 보존한다.

## 2026-09-03 앨범 제목 타일 수정과 렌더러 개선 재빌드 (v1.3)

### 앨범 제목 타일 8장
기존 번역본 7장은 **원본의 알파(투명도 37~41%)를 지우고 완전 불투명으로 저장**돼 있어
앨범 화면에서 검은 사각형으로 보일 상태였고, `gxttl41`(밀피유)과 `gxttl71`(포르테)은
비워야 할 작은 가나 타일에 **마지막 음절을 한 번 더** 그려 넣고 있었다. 사용자 승인 후
8장 전체를 `tools/moonlit_lovers_render_album_titles.py`로 다시 그렸다.

- 이 텍스처는 말풍선 안에 글자가 **빛으로** 그려져 있다. 7장은 그 빛이 알파 채널에,
  `gxttl91`(치토세)만 색상 채널에 있다.
- 말풍선 경계는 밝기로는 글자와 구분되지 않아 **가장자리로부터의 거리**로 나눈다
  (테두리 2px 보존, 안쪽은 테두리 바로 안쪽 고리의 값으로 평탄화).
- 말풍선끼리 겉광이 겹쳐 실루엣이 한 덩어리라, 겉광이 닿지 않는 밝기에서 잡은 중심들의
  중점으로 **세로 밴드**를 잘라 하나씩 처리한다.
- 작은 가나 타일(`ー`, `ォ`, `ァ`, `の`)은 비운다 — 원본 조판과 같다.

검증: 자홍색 바탕에 올려 원본/기존/신규 3단 대조. 알파 손실은 이 바탕에서만 눈에 띈다.

### 렌더러 개선 반영 (52장)
Eternal 쪽 결함을 고치며 개선한 렌더러(`mask_from`, 거리 가중 배경 복원 `erase_label`)를
Moonlit에도 적용해 전투 UI 52장이 개선됐다. 특히 흐린 `ggmenu_btn*b` 사본의 일본어 유령이
사라지고, 버튼 배경의 얼룩이 없어졌다.

**참고:** Moonlit의 기존 GADAT032 번역본(`gebtn*`, `gwp16`, `gxwin02`, `gybtn00` 등)은
전수 확인 결과 **모두 정상**이었다. 같은 계열에서 결함이 나온 것은 Eternal 쪽뿐이다.

### 결과
- 동결 대상 473장 중 **앨범 제목 7장만** 변경(사용자 요청), 나머지 466장 무변경
- `INTEGRATED VERIFY OK`, FSTS 카운트 원본과 동일
- 최종 ISO SHA-256 `f0b013b88d34ed5fbf1bd27bbe078033985f6ca0902a28ea05b668363a984c1f`
- 릴리스 `release/galaxy_angel_moonlit_lovers_ps2_kr_v1.3.xdelta`
  (SHA-256 `43f3f4b96ae652a7ce6e7b2208e529bfa971876ac150795511703db6e701ff01`, apply-check 통과)

## 2026-09-03 미번역 이미지 223장 완료 + 배틀 UI 삽입 경로 신설 — 빌드/검증/릴리스 OK

`ORACLE_MISSION_TRANSLATE_MISSING_20260903.md`의 결정론적 렌더 금지·로컬 AI 금지는
사용자가 명시적으로 해제했고, "이미 만들어져 있는 번역본 473장은 건드리지 않는다"는
제약만 유지했다. 473장은 작업 전후 SHA-256 전수 대조로 **무변경(changed=0)** 확인.

### 번역한 것
- `haplc_*` 61장: 같은 번호의 `gaplc` 문구를 재사용해 렌더
  (`tools/eternal_lovers_render_haplc.py --layout moonlit --translations ... --never-overwrite`)
- 후보 이미지 158장: SLG 152 / ADV 2 / GADAT032 2 / GADAT030 2
  (`assets/translation/images/candidate_translations.json`, 26장 대조 시트로 전수 육안 확인)
- 스킵 4장: `gaitem40`(장식 무늬), 스코어어택 로고, 이벤트 CG의 간판 글씨 2장(그림 자체)
- `gxttl21.tex`(シーン選択 → 장면선택): 앨범 제목 8장 중 유일하게 빠져 있던 것.
  형제들과 달리 원본 알파를 보존해 렌더한다(`tools/moonlit_lovers_render_album_scene_title.py`).

### 빌드에서 드러난 기존 결함
1. **`gaplc_*` 61장이 ISO에 들어가 있지 않았다.** 한국어 렌더는 존재했지만 빌드 권위 목록
   `japanese_images/png`에 원본이 없어 조용히 빠졌고, 최종 ISO의 지명판은 일본어 그대로였다.
   원본을 복구해 다시 삽입 대상이 되게 했다.
2. **SLG(전투 UI)에는 이미지 삽입 단계 자체가 없었다.** SLGRES 295 / SLGSTAGE 672 /
   SLG 165개 사본도 마찬가지였다. `tools/moonlit_lovers_mirror_image_occurrences.py`로
   `image_units.json`의 실제 오프셋에서 사본 세트를 만들고, FSTS 뱅크 패처를 붙였다.
   SLG는 PIDX 컨테이너라 뱅크 패처로 쓰면 인덱스가 깨지므로(`unknown PIDX node type 379`)
   추가 사본 11장은 SLG 자신의 PIDX 빌드 입력으로 넣는다(`--pidx-container SLG`).
3. **뱅크 패처가 슬롯 사이 여백을 0으로 지웠다.** ADV에서는 그 여백에 인덱스 레코드가 있어
   FSTS 리소스가 2395→2269로 줄었다. 여백이 **실제로 전부 0일 때만** 쓰도록 고쳤다.

### 결과
| 단계 | 수치 |
|---|---|
| GADAT030 | 134장 (기존 73 + haplc 61) |
| GADAT032 | 398장 |
| SLG | 165장 |
| SLGRES / SLGSTAGE / ADV 뱅크 사본 | 295 / 672 / 2 |
| primary_verified / runtime_copies_verified | 697 / 481 |

- `moonlit_lovers_verify_integrated.py` → **INTEGRATED VERIFY OK**, FSTS 카운트 원본과 동일
- 최종 ISO SHA-256 `57f98dbadbeb6b9e66658257b002a033530633e8a05d6c9b0e8c0df651c81fc6`
- 릴리스 `release/galaxy_angel_moonlit_lovers_ps2_kr_v1.1.xdelta`
  (SHA-256 `f4bb2cd721c0851218309cdcb198227f00bf6b7deeb1940861314f03d2567b63`, apply-check 통과)

### 남은 문제
- (해결됨) 앨범 제목 타일 7장의 알파 손실과 음절 중복 → 2026-09-03 v1.3에서 8장 전체 재렌더.
- (해결됨) 같은 렌더러 결함이 남아 있던 Eternal Lovers → v1.4로 재출시.

## 2026-09-03 생성형 이미지 경로 재확인 — 원본 이미지 읽기 PASS / 편집·바이너리 저장 차단

- exact checkout 작업공간 `ws_d1259f174a`에서 기존 미션을 이어서 확인했다. 같은 전체 미션의 새 Oracle 제출은 만들지 않았다.
- 기존 Oracle run `20260903T052814Z-744b23fd9cf9`는 저장된 conversation URL이 남아 있지만 recovery harvest가 다시 `attention_required`로 끝났고, recovered tab이 `detached` 상태라 최종 응답을 회수하지 못했다. 기록된 Oracle PID와 recovery Chrome PID는 현재 모두 종료된 상태다. 세션 권위는 여전히 `submitted_unknown`이므로 중복 제출하지 않았다.
- 중요한 도구 상태 변화/정정: 현재 `codex.read`는 PNG를 **실제 이미지로 렌더해 읽을 수 있다.** 첫 배치의 `haplc_311i.png`를 직접 열어 `ギャラクティカランド` 원본을 확인했다. 따라서 이전 기록의 “원본 이미지 viewer 자체가 없다”는 부분은 현재 상태에서는 더 이상 맞지 않는다.
- 다만 현재 codex 작업공간에는 여전히 **ChatGPT 생성형 이미지 편집 액션**과 **편집 결과 바이너리 PNG를 프로젝트에 저장하는 액션**이 노출되어 있지 않다. 결정론적/Pillow/고정 폰트 출력은 사용자 지시와 미션 규칙상 사용하지 않았다.
- 첫 10장 원본은 전부 decode 가능하며 **10/10 205×25 RGBA**, 같은 번호의 기존 한국어 `gaplc_*` 참고 번역본도 **10/10 208×28 RGBA**로 존재한다.
- GADAT030 `haplc_*` 61장 전체를 다시 검사한 결과 기존 `gaplc_*` 한국어 참고 번역본은 61/61 존재하지만, 원본끼리 **PNG SHA-256 exact match 0/61, decoded RGBA exact match 0/61**이다. `haplc`는 205×25, `gaplc`는 208×28이라 기존 번역 PNG를 그대로 복사하는 duplicate 재사용은 안전하지 않다. 각 `haplc` 원본별 생성형 편집이 필요하다.
- 신규 PNG 생성 수는 여전히 **0장**, 기존 `translated_png`는 건드리지 않았다. 새 진단 기록: `build/generative_image_tooling_probe_20260903.json`.

## 2026-09-03 직접 미션 재검증 — codex checkout / 신규 생성 도구 차단

- 정확한 프로젝트 루트 `D:\trans\translation-assistant\work\galaxy_angel_moonlit_lovers`를 checkout 작업공간으로 열고 `ORACLE_MISSION_TRANSLATE_MISSING_20260903.md`를 직접 수행했다. 이번 실행에서는 중첩 자동화 실행이나 다른 커넥터/웹/로컬 AI를 사용하지 않았다.
- 작업 시작 시 기존 `translated_png` **473장 전체의 개별 경로 + SHA-256을 fresh 기준선으로 다시 계산**했고 `build/translated_png_fresh_sha256_20260903.json` 및 컨테이너별 3개 매니페스트에 기록했다. 현재 파일과 1:1 재대조 결과 누락 0 / 추가 0 / 중복 0 / SHA 불일치 0이다.
- 기존 `translated_png`는 시작/종료 모두 **473장(GADAT030 73 + GADAT031 5 + GADAT032 395)**이며, 동일 알고리즘으로 실제 파일 SHA-256을 다시 읽어 계산한 aggregate가 시작/종료 모두 기준선과 일치했다. **modified 0 / deleted 0 / moved 0**.
  - GADAT030: `bb5c4e21fe51024c8d412f773143d783bd3cf6dc1e29acc5d920baa9a9a9485b`
  - GADAT031: `9d9c16ce68095f86dbc68b67c604d0eeb886d238e2f5d5199660b4d3aa45203d`
  - GADAT032: `804165076dae18bab3046a7bf17ebf864b0aad854e3aaa844e6194238a061d87`
- 텍스트는 현재 파일을 다시 계산했다. 시나리오 **25,510**, 선택지 **286**, remaining **4,121** 모두 translation/use 상태 정상이며 실제 히라가나/가타카나 글자/한자 잔존 **0**이다. `remaining_candidates` 4,826개와 remaining 4,121개의 차이 705개도 **ADV 시나리오 런타임 중복 520 + HEADER 식별자 105 + STAGE 식별자 28 + 리소스 경로 50 + 수동 내부 제외 1 + 폰트명 1**로 전부 귀속되어 신규 사용자 노출 텍스트는 **0개**다.
- 이미지 최종 모집단은 후반 개별 확대 판정을 반영한 **일본어 unique 592개**를 유지하고, 그중 기존 번역 존재 369 / 신규 대상 **223**으로 재확인했다. 신규 223은 `SLG 154 + GADAT030 62 + ADV 4 + GADAT032 3`이며 223/223 모두 `image_units.json`에 유일하게 매핑되고 `assets/full_extraction/<CONTAINER>/png/...` 원본도 실제 존재한다. 계획 출력 경로와 현재 파일 충돌은 **0**이다.
- 223개 타깃의 occurrence는 총 **1,205곳**이며, 153개 타깃이 중복 occurrence를 가진다. canonical 외 중복 occurrence는 982곳이고 컨테이너 분포는 ADV 4 / GADAT032 7 / SLG 165 / SLGRES 295 / GADAT030 62 / SLGSTAGE 672이다.
- GADAT030 `haplc_*` 61개는 기존 `gaplc_*` 번역 문구를 그대로 재사용할 수 있어 `build/missing_translation_gadat030_reuse_20260903.json`의 일본어→한국어 문구가 준비되어 있다.
- **신규 PNG는 0장**이다. 현재 사용 가능한 codex 앱 작업공간 도구에는 원본 PNG를 이미지로 직접 여는 도구, ChatGPT 생성형 이미지 편집 액션, 생성 결과를 프로젝트에 바이너리 PNG로 저장하는 액션이 없다. 미션은 결정론적/Pillow/고정 폰트 렌더링과 audit sheet만 보고 애매한 문구를 추측하는 것을 명시적으로 금지하므로, 임의 우회 없이 신규 223개 전부를 `UNRESOLVED_TOOLING`으로 남겼다. 같은 이유로 `build/image_compare/missing_translation_sheet_*.png` 비교 시트도 신규 생성 0장이다.
- 이번 직접 실행 산출물: `build/missing_translation_run_20260903.json`, `build/missing_translation_text_20260903.json`, `build/missing_translation_images_20260903.json`. ISO 빌드는 수행하지 않았다.
- 생성형 이미지 편집 기능이 연결되는 즉시 재개할 첫 10장(GADAT030 `haplc_*`)은 `build/next_10_generative_image_batch_20260903.json`으로 별도 확정했다. 10/10 원본 존재, 10/10 계획 출력 경로 미존재, 일본어→한국어 문구 확정 상태다.

## 2026-09-03 누락 번역 재확인 — 기존 translated_png 제외

- 사용자 지시에 따라 기존 `translated_png` **473장(GADAT030 73 + GADAT031 5 + GADAT032 395)은 전부 작업 대상에서 제외**했다. 기준선 재검증 결과 파일 수/파일명/aggregate SHA-256이 모두 `build/translated_png_baseline_20260903.json`과 일치하며 **기존 파일 변경 0**이다.
- 텍스트는 현재 권위 번역 데이터를 다시 검사했다.
  - 시나리오 **25,510/25,510**, 선택지 **286/286**, remaining **4,121/4,121** 모두 번역값 존재.
  - 실제 일본어 글자 잔존 0, 비어 있거나 disabled인 사용자 번역 단위 0.
  - `remaining_candidates`와의 705개 차이는 ADV 런타임 사본, SLG 내부 HEADER/STAGE 식별자, 리소스 경로/폰트명 등으로 확인되어 **신규 사용자 노출 텍스트 번역은 0개**로 판정했다. 근거: `build/missing_translation_text_20260903.json`.
- 이미지 수동 감사의 뒤쪽 최종 판정을 다시 권위본으로 계산했다. 기존 JSON의 606개 일본어 후보 중 확대 확인으로 제거된 false positive를 반영하면 **최종 일본어 unique image는 592개**다.
- 기존 `translated_png`가 없는 이미지 중 최종 신규 번역 대상은 **223 unique images**다.
  - SLG 154
  - GADAT030 62
  - ADV 4
  - GADAT032 3
  - 오래된 228개 목록에서 최종 제외된 5개: `#00144`, `#02119`, `#03104`, `#03341`, `#03344`.
  - GADAT030 62개 중 61개는 기존 `gaplc_*`와 문구가 같은 `haplc_*` 디자인 변형이므로 기존 `translation_draft.json`의 번역 문구를 재사용할 수 있고, 나머지 1개(`#01587`, `gjc03_04_01`)는 CG 배경 속 일본어 문구다.
  - 전체 대상 목록과 근거: `build/missing_translation_images_20260903.json`.
- **실제 신규 PNG 생성은 아직 완료되지 않았다.** 현재 연결된 Codex workspace API 자체에는 생성형 binary 이미지 write/edit 액션이 없으므로 Oracle/ChatGPT DevSpace 실행 경로를 다시 검증했다. 2026-09-03 재시도에서는 정확한 프로젝트 루트 `D:\trans\translation-assistant\work\galaxy_angel_moonlit_lovers`가 wrapper dry-run을 정상 통과해 **이전 exact-root 차단은 해소된 상태**임을 확인했다. 다만 live run은 웹 제출 전에 `ORACLE_THINKING_TIME_PRE_SUBMIT_FAILED` / `thinking-time-selection-unverified`로 중단됐다. incident report/diagnosis 기준 bucket은 `pre-submit-ui-contract`, `safe_for_fresh_run=true`, 웹 제출/대화 URL/출력 생성은 0이다. 공유 Oracle 자동화 가드 정책상 프로젝트 세션에서 전역 runner를 직접 패치하지 않았고, 신규 PNG 생성은 여전히 **0장**이다. 같은 시점에 기존 `translated_png` 473장을 SHA-256 기준선으로 재검증해 **변경 0장 / baseline PASS**를 다시 확인했다.

## 2026-09-03 현재 상태 읽기 전용 재감사

- 이번 패스는 **기존 `translated_png`를 수정하지 않는 읽기 전용 감사**로 진행했다. 이미지 복원, 재렌더, quality fix, strict rework, reference override는 실행하지 않았다.
- 최신 템플릿 원격 기준을 확인했다.
  - `create-kr-patch-template`: 로컬 v0.3.0, 최신 `origin/main` **v0.4.0 (`7e93a5c`)**
  - `create-retro-game-kr-patch`: 로컬 v3.0.2, 최신 `origin/main` **v3.1.0 (`6c30063`)**
  - 최신 기준의 핵심인 **현재 입력 재현성, 전체 모집단의 resolved/excluded/unresolved 완결성, storage→lookup→load/transform→residency→consumption 소비 경로 귀속**을 감사 판정에 반영했다.
- 원본 ISO를 다시 SHA-256 계산했고 기존 기준과 일치했다.
  - 크기: `3,565,256,704 bytes`
  - SHA-256: `990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe`
- 기존 `KO_candidate_final.iso`도 다시 SHA-256 계산했고 기존 통합 검증 기록과 일치했다.
  - 크기: `3,599,321,088 bytes`
  - SHA-256: `af5540041fc81d86b9c9c40eddca798244924175568ef25840af78a8a855589e`
  - 따라서 **이 과거 후보 ISO 자체와 그 ISO에 귀속된 정적 통합 검증 증거는 그대로 유효**하다.
  - 다만 이후 작업 입력이 바뀌었으므로 이것이 **현재 작업공간 입력으로 동일 후보를 재현할 수 있다는 뜻은 아니다.**
- 현재 `translated_png` 실제 상태와 SHA-256 기준선을 새로 고정했다.
  - GADAT030: **73장**, aggregate `bb5c4e21fe51024c8d412f773143d783bd3cf6dc1e29acc5d920baa9a9a9485b`
  - GADAT031: **5장**, aggregate `9d9c16ce68095f86dbc68b67c604d0eeb886d238e2f5d5199660b4d3aa45203d`
  - GADAT032: **395장**, aggregate `804165076dae18bab3046a7bf17ebf864b0aad854e3aaa844e6194238a061d87`
  - 전체 파일명 목록과 집계 방식: `build/translated_png_baseline_20260903.json`
- **GADAT032은 현재 원본 후보 396장 중 번역본이 395장**이며 누락은 `block_009fd800.png` 1장이다. 이번 감사에서는 자동 복원하거나 생성하지 않았다.
- 현재 선택 집합과 빌드 입력표 교차검사 결과:
  - GADAT030: 현재 후보 12/12가 입력표에 있으나 **2장은 `translated_png`가 아니라 과거 `build/image_quality_fixes`를 사용**한다.
  - GADAT031: 현재 후보 0장, 입력 0장. 과거 `translated_png` 5장은 현재 후보 집합 밖에 남아 있다.
  - GADAT032: 후보 이름 396/396이 입력표에 있으나 **32장은 과거 `build/image_quality_fixes`를 사용**하고, `block_009fd800.png` 입력 경로는 현재 존재하지 않는다.
  - 따라서 현재의 “기존 수동 `translated_png` 우선 / 자동 재가공 금지” 정책과 과거 빌드 입력표가 일치하지 않는다.
- `assets/full_extraction`의 이미지 모집단 구조 검증은 PASS했다. manifest의 리소스/이미지 참조와 실제 raw/PNG 파일이 전부 일치하고 누락/추가 파일은 0이다.
  - ADV: 2,395 resources / **1,737 images**
  - GADAT030: 508 / **508**
  - GADAT031: 577 / **1,452**
  - GADAT032: 1,930 / **1,395**
  - SLG: 4,102 / **1,297**
  - SLGEFF: 594 / **103**
  - SLGRES: 2,677 / **1,578**
  - SLGSTAGE: 9,993 / **3,808**
  - 총 **11,878 image items**, 기존 contact sheet **123장**.
- **전체 이미지 수동 시각 분류를 완료했다.**
  - `assets/translation/images/image_units.json`의 전체 **11,878 image occurrences → 4,182 unique pixel images** 모집단을 사용했다.
  - `sheet_index.json`의 **131개 audit sheet를 131/131 직접 눈으로 재검수**했다. 기존 `vision_audit.json`의 로컬 모델 결과는 권위 판정에 사용하지 않았다.
  - 일본어가 실제로 보이는 unique image: **606개**
  - 일본어가 보이지 않는 unique image: **3,576개**
  - 일본어 이미지의 중복 런타임 occurrence 확장: **2,156곳**
  - occurrence 기준 분포: ADV 457 / GADAT032 377 / SLG 166 / SLGRES 295 / GADAT030 136 / SLGSTAGE 720 / GADAT031 5.
  - 상세 시트별 수동 판정: `build/manual_visual_audit_20260903.md`
  - 기계 판독 요약: `build/manual_visual_audit_20260903.json`
- 전수 결과를 현재 번역/선택/빌드 입력과 교차검사했다.
  - 현재 후보 집합에 포함되고 `translated_png`도 존재: **312 unique images**
  - `translated_png`는 존재하지만 현재 후보 집합/빌드 입력에서 제외된 고아 번역본: **66 unique images**
  - 현재 번역 매핑 자체가 없는 일본어 이미지: **228 unique images**
  - 따라서 현재 빌드 입력이 실제 소비하는 일본어 unique image는 **312/606**, 소비하지 않는 것은 **294/606**이다.
  - 미소비 294개 = **미번역 228 + 기존 번역본 고아 66**.
  - 특히 기존 GADAT030/GADAT032 중심 분류만으로는 SLG·ADV 및 그 런타임 중복 경로의 일본어 자산을 충분히 포괄하지 못했던 것이 확인됐다.
- **현재 입력 기준 릴리스 재현성/한글화 완결성: BLOCKED.** 차단 사유는 다음과 같다.
  1. 수동 전수감사에서 확인된 일본어 unique image 606개 중 **294개가 현재 빌드 입력에서 소비되지 않음**.
  2. 이 중 **228개는 현재 번역 매핑이 없고**, **66개는 번역본이 있으나 후보/빌드 입력에서 빠져 있음**.
  3. `block_009fd800.png` 현재 번역본 누락과 stale 빌드 입력 경로가 별도로 남아 있음.
  4. GADAT030 2장 + GADAT032 32장의 과거 quality-fix 입력이 현재 수동본 권위 정책과 충돌.
- 상세 감사 보고서: `build/current_state_audit_20260903.json`
- 아래의 `GADAT032 백업 복원 / alpha 복구본 유지` 절은 **복원 직후 396장이 존재하던 시점의 과거 기록**이다. 현재 상태 판정은 이 절보다 위의 재감사 결과를 우선한다.

## 2026-09-03 GADAT032 백업 복원 / alpha 복구본 유지

- 사용자 최종 지시에 따라 기준을 단순화했다: **배경 투명도(alpha)를 복구한 48장은 현재 파일을 그대로 유지하고, 그 외 파일은 `translated_png_백업.zip`의 PNG를 그대로 사용한다.**
- 재렌더, quality fix, strict rework, reference override는 이 복원 과정에 사용하지 않았다.
- 현재 `translated_png`: **396장**
- 백업 ZIP의 PNG: **394장**
- `manual_alpha_recovery.json`에서 실제 `status=recovered`였던 **48장**은 SHA-256을 고정한 뒤 그대로 보존했고, 복원 전후 변경 **0장**을 확인했다.
- 백업 ZIP에 존재하면서 alpha 복구 48장에 포함되지 않는 **347장**을 백업 바이트 그대로 복원했다.
  - 복원 후 **347/347 byte-for-byte 동일** 검증 완료.
- 백업 ZIP에 없는 파일은 2장이다:
  - `block_009fd800.png`: alpha 복구 48장에 포함되므로 현재 복구본 유지.
  - `block_011e2800.png`: 백업에 없으므로 현재 파일 유지. 다른 자동/reference 결과로 대체하지 않았다.
- 복원 직전 347장은 롤백용으로 `build/image_compare/gadat032_before_backup_restore.zip`에 보관했다.
- 복원 보고서: `build/image_compare/gadat032_backup_restore_except_alpha.json`
- 복원 스크립트: `tools/restore_gadat032_backup_except_alpha.py`
- `japanese_images/render_report.json`의 SHA-256도 실제 복원된 347장 기준으로 갱신했다.
- 이후 GADAT032에서 이미 존재하는 `translated_png`는 자동 재렌더/quality-fix/strict-rework/reference-override보다 우선한다.
- transparency repair가 다시 필요할 때는 **현재 RGB를 유지하고 원본 PNG의 alpha만 복사**하며 RGB를 다른 백업/렌더 결과로 교체하지 않는다.


## 2026-09-02 재분류·이미지 품질 수정 통합 최종 후보

- 현재 최종 후보 ISO: `build/Galaxy_Angel_Moonlit_Lovers_KO_candidate_final.iso`
- 크기: **3,599,321,088 bytes**
- MD5: `f337af601229cad20659e33c704b07f8`
- SHA-1: `68786a6b1ac032c981f69af98a204dc44734bdb1`
- SHA-256: `af5540041fc81d86b9c9c40eddca798244924175568ef25840af78a8a855589e`
- 최종 통합 검증: `build/integrated_verify_candidate_final.json` → **INTEGRATED VERIFY OK**
- 원본 ISO SHA-256 재검증: `990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe`
- 본편 SCENARIO: **25,510 대사 + 286 선택지**, 선택지 overflow **0**
- ADV SCENARIO 런타임 사본: **36/36 PASS**, 고정 슬롯 유지, 재배치 0
- 현재 이미지 권위본은 `japanese_images/png`만 사용한다.
  - GADAT030: **12장**
  - GADAT031: **0장**
  - GADAT032: **396장**
  - 합계: **408장**
- 이미지 최종 readback: **408/408 primary PASS**, ADV runtime copies **416/416 PASS**
- 이미지 품질 재작업: **25장**을 `build/image_quality_fixes/`에서 별도 생성해 빌드에만 사용하며,
  허용된 일본어 텍스트 영역 밖 변경 픽셀은 **0**이다.
- Eternal Lovers와 일본어 원본 픽셀이 완전히 동일한 공통 UI **14장**은 mutable한
  `translated_png`를 직접 복사하지 않고, Eternal Lovers의 검증된 최종 ISO에서 TEX를
  다시 읽어 `expected_pixel_sha256` 검증 후 복원한 PNG만 참조한다.
- GADAT032 대량 패치의 두 구조 문제를 수정했다.
  - Windows 명령줄 길이 제한을 피하도록 `--png-list` 입력 지원 추가.
  - ADV FSTS에서 경로 문자열 순서와 레코드 순서가 1:1 대응함을 확인하고, 동일 압축
    바이트 검색 대신 **리소스 경로 기반 정확한 런타임 슬롯 매핑**을 사용한다.
    이로써 `gybtn00.tex` / `gybtn00f.tex`처럼 원본 압축 바이트가 동일하지만 서로 다른
    런타임 슬롯을 쓰는 자산의 충돌을 제거했다.
- `gxeff21.tex`은 안전 LZ 기준 8색에서 504 bytes로 496-byte 슬롯을 8 bytes 초과했으나,
  최소 추가 양자화인 **7색 476 bytes**로 들어가도록 압축 후보 탐색을 보강했다.
- ADV 이미지 FSTS 메타데이터: **416/416 동기화**, ADV FSTS 전체 **2,395/2,395 strict decompress PASS**.
- 중앙 IDX 검증 PASS:
  - SCENARIO **177/177**
  - SLG **4102/4102**
  - GADAT030 **508/508**
  - GADAT031 **577/577**
  - GADAT032 **1930/1930**
- 전체 strict resource 검증 PASS:
  - ADV 2395/2395, GADAT000 36/36, GADAT030 508/508, GADAT031 577/577,
    GADAT032 1930/1930, SCENARIO 177/177, SLG 4102/4102,
    SLGRES 2677/2677, SLGSTAGE 9993/9993
- FSTS 리소스 수는 원본과 최종 후보가 동일하다: ADV **2395**, SLGSTAGE **9993**.
- 한글 폰트 ELF SHA-256: `c71129d0e3f897daf7c9dee26b3fbf8046bcfbd6d3346d73090e2ca4d0ed8668`
  - custom glyphs: **1205**
- 이 후보는 위 정적/통합 readback 검증을 모두 통과했다.
- 2026-09-02 후보 ISO 자체로 헤드리스 PCSX2/emucap 스모크 테스트도 재시도했다.
  `tools/emucap_probe_moonlit_candidate.py` / `build/emucap_candidate_final_smoke.json`을
  사용했으나, ISO 실행 전에 emucap의 PCSX2 adapter precondition에서 중단됐다.
  - 원인: 현재 `D:\e2\pcsx2\bin\pcsx2-qt.exe`의 build sidecar가
    `emucap-repo/adapters/pcsx2/upstream.lock`과 불일치 (`pcsx2-patch-required`).
  - BIOS/bridge는 확인됐고, **후보 ISO 부팅 후 발생한 실패가 아니라 에뮬레이터 검증 환경의
    사전조건 실패**이므로 현재 후보의 정적/통합 PASS 판정에는 영향을 주지 않는다.
  - 이 정확한 후보 ISO의 동적 스모크 PASS는 호환 PCSX2 fork 환경이 복구된 뒤 별도 확인이 필요하다.
- 이전 `KO_complete_final.iso`, `KO_reclass_final.iso` 등은 이전 체크포인트로 유지하며,
  현재 정적 검증 기준 최종 후보는 `KO_candidate_final.iso`이다.

## 2026-09-01 완전 통합 최종본

- 최종 ISO: `build/Galaxy_Angel_Moonlit_Lovers_KO_complete_final.iso`
- 크기: **3,599,321,088 bytes**
- MD5: `204aceea4ee334e92986ed61381dab0d`
- SHA-1: `5eaeb0a94f47867a50c43a3c4b4ef416937370c9`
- SHA-256: `a7f5050b9c09e4bdf192ce969d56f30592237c068e480503c8212c8bd3548b62`
- 최종 통합 검증: `build/integrated_verify_complete_final.json` → **INTEGRATED VERIFY OK**
- 본편 SCENARIO: **25,510 대사 + 286 선택지**, 선택지 overflow **0**
- 비시나리오 remaining 유효 미번역: **0개 / 0회**
  - ADV: 1 resource / 13 occurrences
  - GADAT000: 2 / 26
  - SLG: 281 / 81,223
  - SLGRES: 81 / 1,994
  - SLGSTAGE: 715 / 192,782
  - 위 대상 전부 최종 ISO readback PASS
- ADV SCENARIO 런타임 사본: **36/36 동기화 및 검증 PASS**, 재배치 0
- 이미지: **344/344 primary PASS**, ADV runtime copies **427/427 PASS**
- 중앙 IDX 검증 PASS:
  - SCENARIO 177/177
  - SLG 4102/4102
  - GADAT030 508/508
  - GADAT031 577/577
  - GADAT032 1930/1930
- FSTS 리소스 수 원본/최종 동일:
  - ADV 2395
  - SLGSTAGE 9993
- 한글 폰트 ELF SHA-256: `c71129d0e3f897daf7c9dee26b3fbf8046bcfbd6d3346d73090e2ca4d0ed8668`
  - custom glyphs: 1205
- 기존 `KO_reaudit.iso`, `KO_final.iso`, 중간 `KO_complete.iso`는 체크포인트/부분 산출물이며,
  **완성본 기준은 `KO_complete_final.iso`**이다.

## 원본 검증

- ISO: `D:\game\pcsx2-v2.6.3-windows-x64-Qt\roms\Galaxy Angel - Moonlit Lovers (Japan).iso`
- SHA-256: `990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe`
- SLPM_654.29 (실행 파일), 총 126개 ISO9660 파일.

## 2026-09-01 이미지 재감사 및 통합 빌드

- 로컬 AI를 사용하지 않고 이미지 번역본을 원본 기준으로 다시 검토/렌더링.
- 최초 이미지 번역 후보: **357장**
  - GADAT030: 61장
  - GADAT031: 5장
  - GADAT032: 291장
- `gmblk_btn*` 12장은 리소스 이름만 보고 일본어 버튼으로 오판한 **번역 대상 오탐**으로 확인되어
  `japanese_images/png`와 `japanese_images/translated_png` 양쪽에서 제거하고 렌더 규칙에서도 제외.
  - `block_00e4a800.png` ~ `block_00e55800.png`의 해당 12개 리소스
- `gxbgm01.tex` / `Eternal Love 2003`은 영어-only이므로 번역/삽입 대상에서 제외.
- 최종 이미지 삽입 대상: **344장**
  - GADAT030: 61
  - GADAT031: 5
  - GADAT032: 278
- 문제 후보 및 재작업: **188장**
  - GADAT030 61장: 원문 bbox 중심/높이 기준 재배치. 중심 오차 중앙값 0.5px, 최대 1.5px.
  - GADAT031 5장: 원문 줄 위치/높이에 맞춰 재렌더. 카드 문자 영역 밖 변경 0px.
  - GADAT032 122장: 대화문 줄 수/높이, 앨범/캐릭터 제목, 장 제목, 설정 라벨 등 재작업.
- compare sheet:
  - `build/image_compare/GADAT030_sheet_001.png` ~ `_011.png`
  - `build/image_compare/GADAT031_sheet_001.png`
  - `build/image_compare/GADAT032_sheet_001.png` ~ `_047.png`
  - `build/image_compare/summary_sheet_001.png`
  - 상세: `build/image_compare/summary.json`
- 선택지 8개 34바이트 초과도 수동 축약하여 **286/286 선택지 overflow 0**으로 정리.
- 새 통합 ISO:
  - `build/Galaxy_Angel_Moonlit_Lovers_KO_reaudit.iso`
  - 크기: **3,599,312,896 bytes**
  - SHA-256: `611b210a840c03d87c5c4f2aa51331f6850dbc490f5be314204b3229b6b04b6a`
- 통합 검증: `build/integrated_verify_reaudit.json`
  - SCENARIO: 25,510 대사 + 286 선택지, overflow 0
  - remaining: ADV 1/1, SLG 110 resources / 11,106 occurrences, SLGSTAGE 323 / 28,756 전부 PASS
  - 이미지: **344/344 primary PASS**, ADV runtime copies **427/427 PASS**
  - SCENARIO / SLG / GADAT030 / GADAT031 / GADAT032 중앙 IDX 전부 PASS
  - FSTS resource count: ADV 2395, SLGSTAGE 9993 — 원본과 최종 동일
- 오탐 12개 `gmblk_btn*`와 영어-only `gxbgm01.tex`은 최종 ISO에서 원본 decompressed raw와
  **13/13 byte-for-byte 동일**함을 별도 확인.

## 결론: `galaxy_angel` 프로젝트 도구를 그대로 재사용 가능

Moonlit Lovers는 1편 Galaxy Angel과 같은 엔진을 쓴다. 확인한 사실:

- 컨테이너 헤더가 1편과 동일한 `PIDX0\0\0\0` 매직으로 시작한다.
- 압축 블록 매직도 동일한 `" 3;1"` (Ikusa LZSS)이며, `tools/ikusa_lz.py`로 그대로
  압축 해제된다.
- 스크립트 문법이 1편과 동일하다 — `IDSxxxx:{`, `\SaveLabel(...)`, `\Movie(...)`,
  `\Wait(...)`, `\gFade(...)`, `<IDSxxxx`, `>xxxx->IDSxxxx`, `@N(...@@)` 대사
  블록, `\Speaker/\Face/\Voice` 컨텍스트 명령까지 1편 파서(`galaxy_angel_translation.py`)
  가 별도 수정 없이 인식했다.
- **`IDX.DAT` 중앙 인덱스 구조도 1편과 완전히 동일함을 정적으로 확인했다** (아래
  "IDX.DAT 중앙 인덱스" 항목).
- **실기(PCSX2/emucap)에서 정상 부팅하고, 추출한 대사와 일치하는 텍스트가 실제
  화면에 렌더링됨을 확인했다** (아래 "실기 검증" 항목).

## 컨테이너 이름 대응 (1편 → Moonlit Lovers)

| 1편 | Moonlit Lovers | 크기 | 역할 |
|---|---|---:|---|
| `GADAT001.DAT` | `SCENARIO.DAT` | 1,284,096 B | 본편 시나리오 스크립트 (확인, 추출 완료) |
| `GADAT002.DAT` | `SLG.DAT` + `SLGSTAGE.DAT` | 32.6MB + 42.2MB | 전투 메시지 — `[MESSAGE201]`처럼 1편과 동일한
  `#NNN=` 필드 포맷 확인, 추출 완료 |
| `GADAT000.DAT` | `GADAT000.DAT` | 104,448 B | 세이브/로드, 폰트 설정(`FONT_TYPE`/`[FONT_EX]`) 등 공용 UI |
| (해당 없음) | `GAML.DAT` | 447,504 B | 전역 설정(`[BASE]`, 리소스 경로 테이블) |
| (해당 없음) | `ADV.DAT` | 28,838,240 B | 시나리오 스크립트의 **런타임 사본**(1편의 SLGINIT처럼 원본과
  동일 내용 미러) + 텍스처. 고유 텍스트 없음, 번역 대상 아님 (아래 확인) |
| `GADAT032.DAT`(확장 아이콘만) | `GADAT032.DAT` | 19,058,688 B | 폰트/아이콘 관련으로 추정되나 미검증 —
  1편에서도 이 컨테이너는 본문 폰트가 아니라 확장 아이콘(`pjfont00.tex` 등)이었고 실제 대사 폰트는
  ELF 내장 테이블이었다. 이 게임도 같은 패턴일 가능성이 높다 (아래 "폰트" 항목) |
| (해당 없음) | `GADAT030.DAT`, `GADAT031.DAT` | 149MB, 19.7MB | 대부분 `binary` 판정 — 텍스처/모델 리소스로 추정,
  텍스트 없음 |
| (해당 없음) | `SLGRES.DAT`, `SLGEFF.DAT` | 22.9MB, 1.8MB | 전투 리소스 설정(파츠 경로, 이펙트 정의). 일부 UI
  문구 포함 (`remaining` 후보로 추출됨) |
| (해당 없음) | `SE.DAT`, `SVOICE.DAT` | 8.7MB, 97.6MB | 효과음/보이스 데이터, 텍스트 없음 |

## 오늘 완료한 작업

### 1. 시나리오 대사 추출
- 새 도구 `tools/moonlit_lovers_dump_pidx.py` — 지정한 컨테이너의 PIDX0 리프
  레코드를 전부 찾아 압축 해제한 원본 바이트를 `<컨테이너>_DAT_<오프셋:08x>.txt`로
  저장한다 (1편 `source/scenario/*.txt`와 동일한 명명 규칙).
- `SCENARIO.DAT` 173개 블록 전부 해제 → `source/scenario/`.
- 1편의 `galaxy_angel_translation.py export`를 그대로 실행:
  - **25,510개 대사 유닛, 139개 세그먼트 파일**
  - `assets/translation/index.json`, `assets/translation/segments/*.json`
  - 화자(speaker)/표정(face)/보이스(voice) 컨텍스트 정상 추출 확인.

### 2. 전체 컨테이너 텍스트 커버리지 감사
- 새 도구 `tools/moonlit_lovers_audit_containers.py` — 미디어(BGM/MOVIE/VOICE)를
  뺀 모든 ISO 파일에서 Ikusa LZ 블록을 전부 찾아 스크립트/ini/binary로 분류.
  결과: `analysis/container_audit.json`.
- 확인된 텍스트 위치:
  - `SCENARIO.DAT`: 시나리오 스크립트 (추출 완료)
  - `SLG.DAT`, `SLGSTAGE.DAT`: `[MESSAGE201]`류 전투 메시지 섹션. 1편의
    `GADAT002.DAT` `[MESSAGE...]`와 동일하게 `#001~#006`은 메타데이터(우선순위/
    빈도/색상), `#011`, `#012`, `#021`...처럼 10의 배수가 아닌 필드에 실제 대사가
    들어 있다.
  - `GADAT000.DAT`, `GAML.DAT`, `SLGRES.DAT`, `ADV.DAT`: 발췌 UI/설정 문구.
- `ADV.DAT`의 "script"류 블록(`IDSxxxx:{` 포함)은 전부 `SCENARIO.DAT`와 **SHA-256이
  동일한 런타임 사본**임을 확인했다 — 고유 콘텐츠 없음. 1편의 SLGINIT.DAT가
  GADAT002를 미러하던 것과 같은 구조다.

### 3. 잔여 텍스트(전투/UI) 추출
- 새 도구 `tools/moonlit_lovers_extract_remaining_text.py` — 1편
  `galaxy_angel_audit_text_coverage.py`의 `text_blob`/`candidate_lines`(ini
  `#NNN=값` 필드 파서, `//`/`;` 주석 제거, 10의 배수 필드 제외)를 그대로 재사용해
  `SCENARIO.DAT`를 제외한 모든 컨테이너에서 추출.
  - **4,826개 고유 문자열, 278,418회 출현**
  - `SLGSTAGE.DAT` 193,124회, `SLG.DAT` 81,439회 (전투 메시지 — 스테이지마다 같은
    문구가 반복 정의되어 출현 수가 크다), `SLGRES.DAT` 2,138회, `ADV.DAT` 1,618회,
    `GADAT000.DAT` 89회, `GAML.DAT` 10회.
  - 결과: `assets/translation/remaining/remaining_candidates.json`
  - 표본 확인 결과 실제 전투 대사(`"ああ、わかってる。"` 등)와 화자 라벨
    (`"　　　タクト："` 등)이 정상 추출됐다. 일부는 폰트명(`"ＭＳ ゴシック"`)이나
    리소스 경로(`dat\gadat032\...`)처럼 번역 대상이 아닌 개발용 값도 섞여 있다 —
    1편의 `remaining_direct_review.json`처럼 표본 검토 후 `use_translation: false`
    처리가 필요하다.

### 4. IDX.DAT 중앙 인덱스
- `SCENARIO.DAT`의 PIDX 리프 튜플(오프셋, 원본 크기, 압축 크기) 173개 전부가
  `IDX.DAT`의 평면 테이블에서 **단일 file_id(61)로 정확히 173/173 일치**함을
  확인했다. 1편과 동일한 `(file_id, offset, raw_size, compressed_size)` 16바이트
  레코드 구조다.
- 따라서 `galaxy_angel_build.py`의 `mirror_index`류 로직(재배치된 PIDX 레코드를
  IDX.DAT에도 동기화하는 부분)은 컨테이너 이름만 `SCENARIO`로 바꾸면 그대로
  재사용 가능해 보인다. **다만** `GADAT001_INDEX_OFFSET = 0x14E000`(1편의 `[9999]`
  관리 스크립트/IDS 라벨 위치 인덱스)에 대응하는 블록은 `SCENARIO.DAT`에서 아직
  못 찾았다 — 마지막 몇 블록은 관내 이동 시간표(`TBI_5_02.TBL`)였고 `[9999]`나
  `IDSxxxx=오프셋` 형태의 라벨 인덱스는 나타나지 않았다. 이 게임이 분기 오프셋을
  다른 방식으로 관리할 가능성이 있으며, **번역으로 대사 길이가 바뀌었을 때 분기가
  깨지는지는 실제 번역 전까지는 확인할 수 없다** (1편에서 가장 오래 걸렸던 부분).

### 5. 실기 검증 (emucap + PCSX2)
- `emucap-control`로 원본 미번역 ISO를 PCSX2에 실제로 부팅했다.
- 메모리 카드 체크 화면 → 타이틀(`GALAXY ANGEL Moonlit Lovers`, はじめから/つづき
  から/設定) → 오프닝 연출 → **실제 시나리오 대사 화면**까지 정상 진행을 캡처로
  확인했다.
- 화면에 표시된 화자 `タクト`와 대사 `トランスバール皇国暦４１２`는
  `SCENARIO_DAT_00003000` 블록의 `IDS0100:{` 이후 내용과 일치한다 — 추출한
  텍스트가 실제 게임이 읽는 텍스트와 같다는 것을 실기로 확인했다.
- 세션은 검증 후 정상 종료(`stop`)했다. 이번 실행은 미번역 원본 ISO였으므로
  빌드 파이프라인(재삽입) 자체는 아직 시도하지 않았다.

### 6. 이미지(텍스처) 추출 — 이전 패스에서 누락됐던 작업

이전 패스는 압축 블록을 "script/ini/binary"로만 분류하고 `binary`(대부분 텍스처)는
전부 건너뛰었다. 비주얼노벨 특성상 지명판·UI 라벨처럼 **그림에 직접 그려 넣은
일본어**가 많은데, 이걸 완전히 빼먹은 채로 "추출 완료"라고 보고한 것은 잘못이었다.
1편의 `galaxy_angel_extract_gadat032.py`/`galaxy_angel_make_texture_contact_sheets.py`를
재사용해 텍스처 추출까지 마쳤다.

- 새 도구 `tools/moonlit_lovers_extract_textures.py` — 1편 GADAT032 추출기를
  일반화(컨테이너 이름을 인자로 받음, PIDX0 이름 테이블이 레코드 수와 안 맞으면
  `block_<오프셋>.bin`으로 대체 저장, TEX 판별을 파일명이 아니라 실제 `TEX ` 매직으로
  변경)했다.
- 결과:
  | 컨테이너 | 압축 블록 | 이름 매칭 | PNG 변환 | 내용 |
  |---|---:|---|---:|---|
  | `GADAT030.DAT` | 508 | 508/508 정상 (`gaplc_NNNi.tex` 등) | 237 | **함내/행성
    지명판 텍스처.** 예: `エルシオール Ａブロック`, `司令官室`, `ブリッジ`,
    `銀河展望公園・入り口`, `ミルフィーユの部屋` 등 거의 전부 번역 대상 |
  | `GADAT031.DAT` | 577 | 320/577 이름 확인, 나머지는 오프셋 이름으로 저장 | 320 |
    캐릭터 얼굴 아이콘. 대부분 그림만 있고, 일부는 `タクト／私服Ａ※部屋着／苦しみ`처럼
    캡션이 그림에 박힌 카드형 — 소수지만 번역 대상 |
  | `GADAT032.DAT` | 1,926 | 1,930/1,926 (거의 일치, 미세 오차) | 1,391 | UI 크롬
    (버튼·프레임·화살표). 1번 시트 확인 결과 `AUTO`/`Back`/`Sys` 등 **이미 영문**이고
    일본어가 안 보였다 — 18장 시트 중 1장만 검토한 상태라 전수 확인은 아님 |
  | `ADV.DAT` | 2,384 (텍스처류만 2,269) | — | — | **전량 GADAT030/031/032와 SHA-256
    동일한 런타임 사본.** 별도 추출 불필요 (스크립트 블록과 같은 패턴) |
- 컨택트시트(파일명 라벨 붙인 썸네일 그리드)를 세 컨테이너 모두에 대해 생성:
  `assets/image_extraction/{GADAT030,GADAT031,GADAT032}/contact_sheets/sheet_NN.jpg`
  (각 3장/4장/18장) — **총 25장, 1,948개 텍스처 전부를 직접 육안으로 확인 완료**.
- `raw/`(원본 압축 해제 바이트, 나중에 재인코딩 시 필요)와 `png/`(시각 검수·번역용)를
  둘 다 저장했다.

### 7. 이미지 전수 육안 검수 결과 — 텍스트 포함 텍스처 카탈로그

25장 컨택트시트 전부를 확인해 일본어가 그림에 박힌 텍스처를 카테고리별로 정리했다.
(OCR 엔진이 환경에 없어 — `pytesseract`/`tesseract` 바이너리 미설치 — 자동 문자
인식 대신 컨택트시트를 직접 눈으로 전수 확인하는 방식을 썼다. 1편도 이 방식이었다.)

- **GADAT030 (237개, 지명판)**: 스캔한 거의 전부가 번역 대상. `エルシオール
  Ａブロック`, `司令官室`, `ブリッジ`, `銀河展望公園・入り口`, `ミルフィーユの部屋`,
  `喫茶店`, `雑貨屋` 등 함내/시설 지명이 그림 하나당 하나씩 박혀 있다.
- **GADAT031 (320개, 캐릭터 아이콘)**: 대부분 얼굴 그림만 있고 텍스트 없음. 일부
  캡션 카드(`タクト／私服Ａ※部屋着／苦しみ` 류, 4~8장)만 번역 대상.
- **GADAT032 (1,391개, UI/시스템)**: 18장 전부 확인. 카테고리별 발견:
  - **타이틀 메뉴**: `はじめから`/`つづきから`/`設定`/`おまけ`/`終了`
  - **설정 메뉴 라벨**: `遅い`/`普通`/`速い`, `ON`/`OFF`, `ノーマル`/`リバース`,
    `カメラ`/`マップ`, `16bit`/`32bit`, `Low`/`Mid`/`High`(이미 영문), `消音`,
    `決定`/`キャンセル`, `Ultra`(영문) — 각각 파랑/분홍/노랑 등 색상별로 텍스처가
    중복 존재 (포커스 상태 표현)
  - **시스템 확인 대화상자 — 완전한 문장**: `ゲームを終了します。よろしいですか？`,
    `ゲームデータを削除します。※以前のデータは失われます`, `メモリーカード
    （ＰＳ２）の空き容量が不足しています` 등 세이브/로드/메모리카드 에러 메시지
    수십 개
  - **BGM 목록(주크박스)**: `天使たちの休息`, `ミルフィーユのテーマ`, `シヴァ皇子`,
    `巨大戦艦` 등 트랙명 다수
  - **캐릭터/루트 이름표**: `ミルフィーユ`/`ランファ`/`ミント`/`フォルテ`/
    `ヴァニラ`/`ちとせ`
  - **스코어/랭킹**: `スコア表示`, `スコアランキング`
  - **방 아이콘 라벨**(GADAT030과 일부 중복): `ホール`, `謁見の間`, `ミルフィーユの
    部屋`, `クジラルーム`, `格納庫`, `機関室`, `射撃訓練場`, `シミュレーションルーム` 등
  - **CG 갤러리 에피소드 제목** 16개: `司令官はタクト`, `ミルフィーの想い`,
    `ハニーとダーリン`, `愛のビッグバン`, `おかしなミント`, `フローラルピンク`,
    `育てるもの`, `ふたりの花`, `兄と妹？`, `ラブラブ大作戦`, `エンジェル隊集合！`,
    `大いなる災い`, `白と黒の真実`, `エンジェル・スラップ`, `黒髪の少女`,
    `悩める新入隊員`
  - **전투 스테이지/챕터 이름** 10개: `エンジェル隊集結`, `黒き月決戦`, `ヴァル・
    ファスク前衛艦隊`, `トランスバール本星決戦`, `軌道ステーション防衛`, `レゾム
    艦隊`, `テオ宙域突破`, `トランスバール本星最終戦`, `強奪船団遭遇`, `商船救出`
  - **기타 버튼**: `戻る`, `閉じる`, `次へ`, `ギブアップ`, `タイトルへ戻る`
  - **이미 영문이라 번역 불필요**: `AUTO`/`Back`/`Sys`, `GAME OVER`, `Movie`,
    `GALAXY ANGEL`, `Score Attack`, `Other Scenes`, `APPENDIX`, `BGM`,
    `KUJIRA-REPORT`, 3D 미니게임 방 라벨 일부(`Forte's room`, `Shooting range` 등),
    `ROUND 1-9`, 함선명(`Val-Fasc Battleship`, `Dark Angel`)
- **`ADV.DAT`의 텍스처 2,269개는 전량 위 세 컨테이너와 SHA-256 동일** — 별도 검수
  불필요함을 재확인.
- 결론: **이미지 기반 번역 대상이 최소 수백 개(지명판 237 + UI/시스템 문구
  카테고리별 수십~수백) 규모로 확정**됐다. 다음 단계는 이 텍스트를 문자열로
  옮겨 적어(번역 세그먼트화) 번역 승인을 받는 것과, 번역 확정 후 이미지를
  다시 그려 넣는 재인코딩 파이프라인이다.

## 아직 확인하지 못한 것

1. **폰트 실체** — `GADAT032.DAT`가 1편처럼 확장 아이콘 전용이고 실제 대사 폰트는
   ELF(`SLPM_654.29`) 내장 비트맵 테이블일 가능성이 높다(`GADAT000.DAT`/`GAML.DAT`의
   `FONT_TYPE="ＭＳ ゴシック"`, `[FONT_EX]`가 1편과 완전히 같은 red-herring
   패턴이다). ELF를 정적으로 훑어 글리프 테이블 후보를 찾아봤지만 신뢰할 만한
   위치를 특정하지 못했다 — 1편에서도 이건 정적 분석이 아니라 emucap으로 실행 중
   메모리를 추적해서(대사 문자열 → 텍스트 객체 → 렌더 호출 경로) 찾아냈다. 같은
   방식의 런타임 추적이 필요하며, 한 세션 안에 끝날 작업이 아니다.
2. **선택지(`@(ss...@)ss`) 블록** — `export()`는 `@N(...@@)` 대사만 뽑는다.
   `SCENARIO.DAT`에 선택지 블록이 있는지, 있다면 몇 개인지 별도로 세지 않았다.
3. **분기/라벨 오프셋 보존 메커니즘** — 위 "IDX.DAT" 항목 참고. 1편의
   `[9999]` 관리 스크립트+`0x14E000` ID 인덱스에 대응하는 것을 SCENARIO.DAT에서
   아직 못 찾았다. 번역 문자열 길이가 원문과 달라졌을 때 분기가 깨지는지는 실제
   번역·빌드·실기 검증 사이클을 돌기 전까지는 알 수 없다.
4. **빌드(재삽입) 파이프라인** — 오늘은 추출과 실기 부팅 확인만 했다. 번역문을
   ISO에 되돌려 넣는 `galaxy_angel_build.py` 상당 작업은 시작하지 않았다.
5. **글상자 실측·용어집·번역 승인** — 스킬 절차상 번역 전에 반드시 사용자와
   확정해야 하는 단계이며 아직 손대지 않았다.

## 빌드 파이프라인 (오늘 세션)

목표: 번역 텍스트가 아직 없으므로 **원문을 그대로 되삽입하는 파이프라인 자체가 동작하는지**
검증. 만든 스크립트는 전부 `D:\trans\translation-assistant\tools\moonlit_lovers_*.py`.

### 1. `moonlit_lovers_verify_structure.py` — 고정 오프셋 구조 보존 검증

1편의 `galaxy_angel_audit_build.py`/`galaxy_angel_repair_central_idx.py`/
`galaxy_angel_audit_runtime_indexes.py`의 "(file_id, offset, raw_size,
compressed_size) 16바이트 레코드" 로직을 이식. `verify_container()`가 컨테이너의
PIDX0 리프 튜플과 IDX.DAT 평면 테이블을 대조해 `file_id`를 스스로 찾아내고(가장 많이
일치하는 후보 채택, ambiguous 검사 포함) 전수 일치 여부를 판정한다.

**정적 검증 결과** (원본 ISO 대상):
- `SCENARIO.DAT`: OK — pidx_leaves=173, file_id=61, idx_matches=173/173
- `SLG.DAT`: OK — pidx_leaves=2650, file_id=116, idx_matches=2650/2650
- `SLGSTAGE.DAT`: **실패** — PIDX0 매직은 있지만(`PIDX0\0\0\0`) 리프 레코드를 못 찾음.
  실제 첫 압축 블록(` 3;1` 매직)이 `0x2a90`처럼 **0x800 정렬이 아닌 오프셋**에 있음을
  확인했다 — SCENARIO/SLG와 달리 SLGSTAGE는 블록을 더 촘촘하게(비섹터 정렬로) 채우는
  것으로 보인다. `galaxy_angel_build.records()`의 `data_offset % 0x800` 가정이 이
  컨테이너에는 안 맞는다. **다음에 시도할 것**: 정렬 가정을 빼고 4바이트 단위로만
  스캔하거나, 실제 정렬 단위(16? 4?)를 SLGSTAGE 헤더 근처 몇 개 튜플을 손으로 뽑아
  역산해서 확인.

**더미 왕복 테스트** (`--dummy-roundtrip`): `SCENARIO.DAT`에서 임의로 고른 3개 블록의
대사 안에 "テスト"×40 더미 일본어(번역 아님)를 삽입 → `moonlit_lovers_build.py`로
재빌드 → 3개 블록 전부 압축 크기가 실제로 늘어남을 확인(674→715, 726→767, 700→740
바이트, 전부 원래 슬롯 안에 여유가 있어 오프셋은 안 바뀜) → 재빌드된 ISO에서
`verify_container`가 다시 173/173 OK로 통과 → **건드리지 않은 나머지 123개 ISO
파일(SCENARIO.DAT/IDX.DAT 제외)의 SHA-256이 원본과 완전히 동일**함을 확인.
**PASSED.**

### 2. `moonlit_lovers_build.py` — 빌드(재삽입) 파이프라인

1편 `galaxy_angel_build.py`의 컨테이너 재배치/IDX.DAT 미러링 로직을 컨테이너 이름에
안 묶이게 일반화(`--container` 반복 인자). 1편과 달리 이 게임은 `GADAT001_INDEX_OFFSET`류
분기 라벨 인덱스의 존재를 아직 못 찾았으므로 `rebuild_scenario_index`는 이식하지
않았다(대신 코드 주석에 이유와 이식 방법을 남겨 둠) — 대사 길이가 실제로 바뀌는
번역이 들어오기 전까지는 이게 필요한지 알 수 없다.

**실행 결과**: `SCENARIO.DAT` 173블록 전부를 원문 그대로 압축 해제→압축(패스스루,
`--force-recompress`)→재삽입.
- Ikusa LZ 압축기가 원본 디스크와 바이트 단위로 똑같은 압축 스트림을 만들지 않으므로
  **번역 없이도 59/173 블록의 압축 크기가 실제로 달라졌다** — 이것만으로도 파이프라인이
  진짜로 왕복하고 있다는 증거. 전부 원래 슬롯 안에 들어가 재배치는 0건.
- 빌드 후 ISO 전체 크기: 원본과 **완전히 동일**(3,565,256,704 B, 재배치가 없었으므로).
- `SCENARIO.DAT`/`IDX.DAT` 크기도 원본과 동일(재배치가 안 일어났으므로 컨테이너
  파일 크기는 안 바뀜; 안의 바이트는 바뀜).
- **건드리지 않은 나머지 124개 ISO9660 파일 전부 SHA-256이 원본과 동일**함을 확인
  (source-fidelity 철칙 대로 빌드에 안 쓰인 파일은 원본 그대로).
- `moonlit_lovers_verify_structure.py`로 재빌드된 ISO의 SCENARIO 구조를 재검증 →
  `OK pidx_leaves=173 idx_matches=173`.
- 결과 ISO: `build/moonlit_lovers_passthrough.iso` (약 3.3GB, 빌드 시간 약 5분,
  이후 캐시 재사용 시 23초).

### 3. 이미지 재인코딩(encode_tex) 왕복 테스트

1편의 `galaxy_angel_gadat032.py`(`decode_tex`/`encode_tex`)는 raw TEX 바이트만 받는
범용 함수라 이 게임 코드 수정 없이 그대로 적용된다.

`assets/image_extraction/GADAT030/raw/gaplc_000i.tex` (indexed4, 208×28, 팔레트
16색)로 왕복 테스트: decode → 더미 빨간 사각형 그리기 → `encode_tex(..., colours=16)`
→ 재인코딩 결과 바이트 길이가 원본과 **정확히 일치** → 다시 decode해서 빨간 픽셀이
실제로 들어갔음을 확인. **PASSED** (1개 텍스처로 성공, 나머지 507개는 안 돌려봄).

주의: `colours` 인자 없이(원본 팔레트 유지 모드) 호출하면 원본 팔레트에 없는 색(빨강)은
최근접 색으로 매핑돼 안 보인다 — 이건 코덱 버그가 아니라 팔레트 보존 모드의 정상 동작.
실제 번역 이미지 작업 때는 원문 팔레트에 없는 색(자모 안티에일리어싱 등)이 필요하면
`colours=` 인자로 강제 재양자화해야 한다는 걸 기억해 둘 것.

### 4. `moonlit_lovers_translate_all.py` — 단일 진입점

스킬의 "빌드는 한 진입점으로" 규칙대로 만듦. 1/3 원본 SHA-256 검증(불일치 시 빌드
**중단**, `--allow-unverified-original`로만 우회 가능) → 2/3 SCENARIO.DAT 재삽입
(현재는 패스스루) → 3/3 재빌드 ISO 구조 검증. 아직 안 붙은 단계(SLG/SLGSTAGE 전투
메시지, GADAT000/GAML/SLGRES UI 문구, GADAT030/031/032 텍스처, ELF)는 **경고 메시지로
증상까지 명시**해서 출력한다(스킬 "경고에 증상을 적어라" 규칙). 실행해서 성공 확인함
(빌드 OK, 구조 검증 OK, 캐시 재사용 시 23초).

### 막힌 지점과 다음 시도

1. **SLGSTAGE.DAT PIDX 리프를 못 찾음** — 0x800 정렬 가정이 안 맞는다. 첫 블록이
   `0x2a90`(비정렬)에 있음을 확인했으니, 다음엔 정렬 가정 없이 4바이트 스캔하고
   후보를 `raw_size`/`compressed_size` 합리성으로만 걸러 실제 정렬 단위를 역산할 것.
2. **분기/라벨 오프셋 인덱스(1편의 `[9999]`+`0x14E000`류) 미발견** — 대사 길이가 실제로
   달라지는 진짜 번역이 들어오기 전에는 이게 필요한지 알 수 없음. 번역 승인이 나면
   가장 먼저 확인해야 할 항목.
3. **build/ 폴더가 원본 ISO 통짜 복사본을 매번 만들어 3~10GB씩 씀** — 반복 실험 시
   디스크 관리 필요. `scenario_compressed_cache/`는 재사용 가능하니 유지하되, 완료된
   테스트 ISO는 정리했다.

## 다음 단계 제안

1. `GADAT032.DAT`/ELF 폰트 실체 확인은 emucap으로 실제 대사 화면에서 렌더 경로를
   추적해야 한다 — 1편의 "추가 추적: 실제 텍스트 객체 경계" 절차(`work/galaxy_angel/STATUS.md`)를
   그대로 재현하는 별도 세션이 필요하다.
2. `remaining_candidates.json`의 4,826개 중 실제 번역 대상(전투 대사·UI 문구)과
   비대상(폰트명·리소스 경로)을 분리하는 검토 규칙을 정한다 (1편의
   `remaining_direct_review.json` 방식).
3. ~~`GADAT032.DAT` 컨택트시트 17장 마저 검토~~ — 완료, 위 "이미지 전수 육안 검수
   결과" 참고.
4. 이미지 번역 파이프라인 — 검수로 번역 대상 텍스처를 추리면, 1편의
   `japanese_images` 워크플로(번역 이미지 그리기 → 같은 TEX 포맷/팔레트로 재인코딩
   → 원본 압축 블록 자리에 재삽입)를 이 게임의 `encode_tex`(`galaxy_angel_gadat032.py`)
   로 재현해야 한다. 아직 시작 전.
5. 번역을 시작하기 전에 글상자 실측(스킬 절차 4단계)과 용어집 확정(5단계)을
   사용자와 진행한다.

## emucap 폰트/글상자 실측 (2026-08-25 세션)

### 세션 절차
- ISO SHA-256을 STATUS.md 상단 값과 대조 후 emucap-control로 부팅
  (`launch-01m0wcddc9edr2g8rbq83jyc61`, 포트 47801). ROM 식별
  `SLPM-65429`, `game_version 1.02`, `disc_crc ddade609` — 위 원본 검증
  섹션의 SHA-256과 일치.
- 타이틀 → `circle`로 はじめから → 오프닝(별/성운 컷신, 프레임 ~900→~6300) →
  실제 시나리오 대사 화면까지 재현했다. 화자 `タクト`, 대사
  `トランスバール皇国暦４１２年。元皇子エオニアは、皇国に対してクーデターを
  起こした。`가 표시됨을 확인 — 1편과 동일한 절차(“실기 검증” 섹션)가 그대로
  재현된다.
- 이 지점에서 `dialogue_font_trace.p2s`로 저장 상태를 남겼다 (재개용, `stop` 전
  마지막 프리즈 시점). 세션은 검증 후 `stop`으로 정상 종료했다 (bridge/emulator
  프로세스 모두 `exited` 확인).

### 폰트 실체 — 부분 확인, 정확한 오프셋은 미확정
- **엔진 동일성 재확인**: `SLPM_654.29`에 `CGMan::CreateTextObj`(파일 오프셋
  `0x1D5F00`), `CGMan::ResetText`(`0x1D5F20`), `m_hFont`(`0x1D0070`),
  `m_nFontH`(`0x1D0082`) 문자열이 1편과 동일하게 존재함을 정적으로 확인했다.
  같은 CGMan 텍스트 오브젝트 엔진을 쓴다는 근거.
- **런타임 문자열 추적**: 화면 대사의 Shift-JIS 바이트열을 EE 전체(32MB)에서
  검색해 4곳을 찾았다.
  - `0x0087CE8A` — 압축 해제된 원본 시나리오 사본 1개 (1편의 `0x0109xxxx`류에 대응)
  - `0x00EA1D70`, `0x00EA2ED0`, `0x00EA7C60` — 런타임 미러/텍스트 슬롯 군집
    (1편의 `0x00A6FC30`/`0x00A72A1C`류에 대응). `0x00EA1D70` 슬롯을 직접
    `read_memory`로 읽어 문자열 뒤에 이어지는 필드까지 확인했다 — NUL 종료 뒤
    포인터로 보이는 4바이트 값 4개(`0x00EABA90`, `0x00EAC910`, `0x00EAE610`,
    `0x00EAE7B0`)가 있는데 전부 같은 `0x00EAxxxx` 힙 풀 안이라 폰트 테이블
    포인터는 아니다.
  - 쓰기(write) 중단점을 `0x00EA1D70..0x00EA7C60`(23,040바이트) 범위 전체에 걸어
    다음 페이지로 넘어갈 때 적중시켰다. 읽기(read) 중단점은 1편과 마찬가지로
    이 접근 형태에서 적중하지 않았다(브리지가 이 read 패턴을 못 잡는 것으로
    재확인).
- **적중한 호출 경로**를 `call_stack`/`disassemble`로 역추적했다:
  `0x0015D368`(텍스트 버퍼에서 2바이트 읽기, 캐릭터 코드로 추정) ← 반환 주소
  `0x00157B2C`(해당 함수 말미) ← `0x0015CC58`(텍스트 오브젝트 구조체
  `+0x14`/`+0x38`/`+0x40` 플래그 조작 — 1편의 `0x001488xx` 객체 갱신 루틴과
  같은 패턴) ← `0x0016F038`/`0x0016F178`/`0x0016F198`/`0x001698D8`(범용
  링크드리스트/오브젝트 순회 헬퍼). 이 범위의 디스어셈블에서는 ELF 정적 영역
  (`0x00100000~0x00400000`대)을 가리키는 `lui`+`ori`/`addiu` 상수 쌍을
  찾지 못했다 — 즉 이 구간 안에는 폰트 테이블 자체가 없고, 더 깊은
  글리프 인덱스/텍스처 조회 leaf 함수까지 추적이 더 필요하다.
- **정적 지문 대조(실패, 유의미한 부정 증거)**: 1편에서 확정된 폰트 테이블
  (ELF VA `0x0033D710`, 24×24·4bpp·글리프당 288바이트)에서 밀도가 높은 글리프
  2개(원형 글리프, 상자형 글리프)의 원본 바이트열을 그대로 이 게임 ELF
  전체에서 바이트 단위로 검색했으나 **0건 일치**. 반복되는 12바이트/행 패턴
  (상자 글리프의 `f0ffffffffffffffff0f`)도 이 ELF에는 1회만 나타나 표 형태로
  존재하지 않는다. 즉 **1편과 완전히 동일한 폰트 원본 데이터를 그대로 재사용한
  것은 아니다** — 같은 셀 포맷(24×24/4bpp/288B)일 가능성은 남아있지만 실제
  픽셀 데이터·오프셋은 다시 찾아야 한다.
- `GADAT032.DAT`는 이전 세션에서 이미 25장 컨택트시트 전수 육안 검수를 마쳤고
  1,391개 텍스처가 전부 UI 크롬/아이콘/메뉴 문구였다 — 본문 대사에 쓰이는
  CJK 글리프 표 형태(격자형 저엔트로피 비트맵)는 없었다. 이는 1편에서
  `GADAT032`가 확장 아이콘 전용이고 본문 폰트가 ELF 내장이었던 패턴과
  일치하며, 이번 런타임 추적 결과(대사 텍스트 소비 경로가 시나리오 버퍼→
  런타임 슬롯→CGMan 텍스트 오브젝트로만 이어지고 GADAT032 관련 파일 I/O나
  포인터가 전혀 관측되지 않음)와도 모순되지 않는다.
- **결론**: "ELF 내장 비트맵 테이블" 가설은 기각되지 않았고 오히려 더
  뒷받침됐지만(엔진 동일, GADAT032 무관), **이 게임의 정확한 글리프 테이블
  VA·셀 포맷·SJIS→인덱스 변환 함수는 이번 세션에서 확정하지 못했다.** 1편도
  이 단계에 여러 세션이 필요했던 것과 같은 수준의 작업이 더 필요하다. 다음
  세션은 `0x0016F038` 계열 헬퍼를 넘어 실제 텍스처/비트맵을 참조하는 leaf
  함수까지 조사하거나(그 함수들의 하위 `jal` 대상을 순차 디스어셈블), 또는
  `0x0015CC58` 안에서 `+0x38`/`+0x40` 필드가 가리키는 진짜 렌더 핸들 구조체를
  더 깊이 따라가야 한다. 저장 상태 `dialogue_font_trace.p2s`에서 이어서 하면
  같은 화면을 다시 부팅하지 않아도 된다.
- 한글 대체 셀 실기 검증(더미 글리프 이식)은 정확한 테이블 위치를 못 찾아
  **시도하지 못했다.**

### 글상자 실측 — 부분 실측 (정식 눈금 프로브는 빌드 파이프라인 부재로 미실행)
- Moonlit Lovers는 아직 재삽입(빌드) 파이프라인이 없어(“아직 확인하지 못한 것”
  4번), 스킬의 `make_wrap_probe.py` 눈금 문자열을 실제로 주입해 빌드·재부팅하는
  정식 절차는 이번 세션에서 수행하지 못했다.
- 대신 **원본 그대로의 첫 대사 화면**을 실측 근거로 썼다. 캡처: 위
  `dialogue_font_trace.p2s`와 동일 시점 스크린샷(640×480). 시나리오 대사창은
  화면 좌하단, 대략 x=10~628, y=330~470 (가로 618px, 세로 140px)에 그려지고
  안쪽 텍스트 영역은 대략 x=115~615(가로 500px), 3줄 표시.
  - 1행 `トランスバール皇国暦４１２年。` — 15자
  - 2행 `元皇子エオニアは、皇国に対してクーデター` — 20자, 박스 안쪽 폭을
    거의 끝까지 채움(육안 확인)
  - 3행 `を起こした。` — 6자(짧게 끝남, 문장이 끝나 줄바꿈된 것으로 보임 —
    자동 줄바꿈 강제 여부는 미확인)
  - 이 정도로는 **글자수 기반인지 폭 기반인지, 정확한 최대 열 수(20인지 21인지
    22인지)를 확정할 수 없다.** 2행이 20자에서 끝난 것이 "정확히 20자 제한"
    때문인지 "마침 문장이 거기서 끝나서"인지 이 데이터만으로는 구분 불가 —
    스킬 SKILL.md의 "글자수 기반 vs 폭 기반" 판정은 한글 눈금과 반각 눈금을
    나란히 넣어 봐야 하며, 이는 빌드 파이프라인이 있어야 가능하다.
  - 전투 메시지창(`SLG.DAT`/`SLGSTAGE.DAT` `[MESSAGE...]`)은 이번 세션에서
    전투 화면까지 진행하지 못해 **미실측**이다.
- **결론**: 정식 실측(스킬 4단계, `make_wrap_probe.py` 눈금 주입)은 빌드
  파이프라인이 생긴 뒤 다시 수행해야 한다. 이번 세션의 관찰은 "대략 20자
  내외·3줄" 이라는 근사치일 뿐 확정값이 아니다.

### emucap 세션 정리
- `run_start`/`log_finding`/`run_finish`(status=done)로 emucap-track에 기록
  완료 (run_id `01M0WCDX30FG610375N4AG7WYX`, finding_id
  `01M0WD0S7SFXP4P12AV6KTQ5NX`).
- `emucap-control stop`으로 launch `launch-01m0wcddc9edr2g8rbq83jyc61`
  정상 종료 확인 (bridge/emulator 프로세스 모두 `exited`).

## 번역 착수 (2026-08-28 세션)

이전 세션까지는 추출·감사·빌드 파이프라인만 있었고 번역은 0건이었다. 이번 세션에
번역 전제조건(글상자 실측·용어집)을 확정하고 시나리오 번역을 시작했다.

### 스킬 템플릿 갱신
`D:\trans\translation-assistant\create-retro-game-kr-patch\create-retro-game-kr-patch`를
`git pull` 해 **2.0.1 → 3.0.2**로 갱신했다.

### 글상자 실측 — 원문 코퍼스에서 역산 (40열 / 3줄)

폰트 이식이 아직 안 끝나 실기에 한글을 띄울 수 없으므로, 스킬의 `make_wrap_probe.py`
눈금 주입 대신 **원문 대사 44,466줄의 표시 폭 분포**에서 역산했다.

- 일반 글자로 끝나는 줄은 **40열이 최대**이고 40열에 8,800줄이 몰려 있다 (자동
  줄바꿈 경계).
- 42열인 줄이 1,725개 있지만 끝 글자가 전부 `。`(922) `、`(229) `っ`(168) `？`(139)
  `！`(77) `ー` `ゃ` `」` 같은 **금칙문자**다 — 20자 경계 밖으로 매달린 것이지 칸이
  더 있는 게 아니다. 40열 줄의 끝 글자는 아무 글자나 온다(`い` `て` `た` `の` `な`…).
- `channel: 1`(대화창)은 원문에서도 1~3줄뿐이고, `channel: 0`(나레이션)은 6~11줄이다.

**확정: 본문 폭 40열(ASCII 1열/전각 2열 → 한글 20자), 대화창 3줄, 나레이션 줄 수 제한 없음.**
폰트 이식이 끝나면 실기 눈금으로 재확인하고, 값이 달라지면 재번역 없이
`moonlit_lovers_reflow_translations.py --max-columns`만 다시 돌리면 된다.

### 용어집 확정

- `tools/moonlit_lovers_build_glossary.py` — 1편 `work/galaxy_angel`의 **사용자 확정
  표기를 승계**하고, 이 게임 코퍼스에 안 나오는 항목은 빼고, 빈도·붙는 호칭은 이
  게임에서 다시 센다. 결과 `assets/translation/glossary.tsv` 61행.
- 본작 신규 표기는 사용자가 확정했다: `烏丸ちとせ`→`카라스마 치토세`,
  `ヴァル・ファスク`→`발・파스크`, `ネフューリア`→`네퓨리아`, `レゾム`→`레좀`,
  `オ・ガウブ`→`오・가우브`, `クレータ`→`크레타`, `クールダラス`→`쿨다라스`,
  `ラーク`→`라크`, `リッキー`→`리키`, `レナ星系`→`레나 성계`, `カフカフ`→`카프카프`,
  `ムギムギ`→`무기무기`, `クジラルーム`→`쿠지라 룸`.
  `シャープシューター`(샤프 슈터)는 1편에서 미등장이었으나 본작에서 치토세 전용
  문장기로 33회 등장한다.
- 근거와 규칙은 `assets/translation/GLOSSARY.md`.
- **주의**: 확정본을 만들면서 이전 세션의 후보 추출본(525행 raw glossary.tsv)을
  덮어썼다. 필요하면 `glossary_source_texts.json`에서 다시 뽑을 수 있다.

### 번역 파이프라인

1편 `tools/galaxy_angel_ai_translate.py`를 그대로 쓰되 이 게임에 맞게 인자를 추가했다
(기본값은 1편 동작 그대로라 1편 빌드에는 영향이 없다):
`--prompt`, `--max-columns`(0이면 줄바꿈을 뒤 단계로 미룸), `--dialogue-max-lines`.

**시범 배치로 세 번 실패하고 나서야 지금 구조가 나왔다. 기록해 둔다.**

1. **1차(44열 그대로, limit 24)** — 22/46 거부. 모델이 원문 줄바꿈을 그대로 유지해
   한국어 길이에 안 맞았다. 게다가 원문 `５人`을 `5명`으로 바꿔 놓았다(철칙 6 위반).
2. **2차(줄바꿈을 뒤로 미루고 40열 reflow 도구 추가, limit 60)** — 80/140 거부.
   전부 "모델이 만든 줄바꿈". 모델에게 "줄바꿈 넣지 마라"라고 지시해도, **줄바꿈된
   원문을 그대로 보여주면 모델은 그 구조를 따라한다.** reflow가 그 줄을 공백으로
   이으면 `순식간에 트 랜스벌`처럼 단어가 쪼개졌다.
3. **3차(모델에 보내는 원문을 한 줄로 펴서 전달)** — **거부 0/60.** 일본어는
   띄어쓰기가 없어 줄을 빈 문자열로 이으면 원문 문장이 정확히 복원된다.
   `original` 필드 자체는 건드리지 않고 전송용으로만 편다(`flatten_source`).

### 원본 보존 검사 (번역기 내장)

번역 시점에 걸러야 나중에 수천 건을 되돌리지 않는다 — 스킬의 "문자 단위 전수 대조를
처음부터 돌려라".

- **전각→반각 자동 복원**: 원문이 쓴 전각 문자(`！？（）～`, `０-９`, `Ａ-Ｚ`, `～`)를
  모델이 반각으로 바꾸면 되돌린다. 복원 후에도 남으면 거부.
  전각 공백 `　`는 제외했다 — 한국어는 ASCII 공백으로 띄어쓰므로 오탐이 된다.
- **`「」`/`『』` 자동 복원**: 모델이 `"`/`'`로 바꾼 것을 등장 순서대로 여닫이로
  되돌린다. 개수가 원문과 다르면 거부. 시범 표본에서 「」 포함 2건 중 1건이
  `""`로 바뀌어 있었고, 코퍼스 전체로는 409단위가 해당된다.
- **`・` 개수 일치**: 이 게임에서 가운뎃점은 전부 고유명사 안에 있으므로 개수가
  달라지면 치환이다. 거부.
- **모델이 만든 줄바꿈 거부**: 보내는 원문이 한 줄이므로 출력의 줄바꿈은 전부
  모델이 지어낸 것이다.

### `moonlit_lovers_reflow_translations.py` — 줄바꿈 전담

모델은 한 줄로만 번역하고, 화면 줄바꿈은 이 도구가 실측 폭에 맞춰 기계적으로 넣는다.

- 40열 기준으로 공백 우선 줄바꿈, 공백 없는 긴 덩어리는 강제 분할.
- 원문의 전각 공백 들여쓰기를 복원한다. 이 게임에는 두 가지가 있다 —
  **둘째 줄부터 들여쓰는 것 210단위**, **첫 줄만 들여쓰는 것 13단위**. 각 줄의
  들여쓰기만큼 그 줄의 폭 예산이 줄어든다.
- 줄바꿈 후 `channel: 1`이 3줄을 넘으면 `use_translation: false` + `needs_human`으로
  내리고 `analysis/reflow_overflow.json`에 남긴다 — 화면 밖으로 나가는 대사가
  빌드에 들어가지 않게 한다.
- 폰트 실측값이 바뀌면 `--max-columns`만 바꿔 다시 돌리면 되고 재번역은 필요 없다.

### 빌드 연결

`galaxy_angel_translation.py`의 `apply()`가 세그먼트 JSON → `*_DAT_<offset>.txt`
재생성과 `preserve_ids_anchor_offsets()`(철칙 12, 구조 앵커 바이트 위치 보존)까지
이미 처리한다. `moonlit_lovers_translate_all.py`의 `--built-scenario`에 그 산출물을
넣으면 되며, 이 배선은 아직 안 붙였다.

### 여전히 남은 제약

- **폰트 글리프 테이블 미확정** — 번역문이 있어도 실기에 한글이 안 그려진다.
  emucap 런타임 추적을 이어서 해야 하며(`dialogue_font_trace.p2s`에서 재개),
  이것이 끝나기 전에는 실기 검증을 할 수 없다.
- SLGSTAGE.DAT PIDX 리프 미발견 → 전투 메시지 재삽입 불가.
- 이미지(텍스처) 번역 미착수.

### 빌드 배선 전에 확인할 것 — 압축 해제 크기 제약

1편 `galaxy_angel_translation.py`의 `apply()`는 번역 후 블록의 **압축 해제 크기가
원본보다 커지면 빌드를 중단**시킨다("this engine requires the original decompressed
block size"). 그런데 이 게임의 빌더는 재배치할 때 PIDX 레코드에 **새 raw_size를 다시
써 넣는다**(`moonlit_lovers_build.py:150`, `struct.pack_into("<III", ..., raw_size,
len(compressed))`). 즉 1편의 제약이 이 게임에도 그대로 적용되는지는 확인되지 않았고,
그 답에 따라 번역문의 바이트 예산이 완전히 달라진다.

- 커져도 되면: 번역문 축약이 불필요하다 (철칙 8).
- 커지면 안 되면: 파일 단위 바이트 예산 안에서 축약해야 한다.

STATUS의 더미 왕복 테스트(`テスト`×40 삽입)에서는 압축 해제 내용이 늘어난 채로
재빌드와 구조 검증이 통과했으므로 **커져도 될 가능성이 높지만**, 그때는 IDX/PIDX
구조 검증만 했고 실기로 분기·선택지까지 확인한 것은 아니다. 폰트가 끝나 실기 검증이
가능해지면 이것부터 확인한다.

## 시나리오 번역 완료 (2026-08-29)

25,510 대사 유닛 전부를 처리했다. 총 소요 약 30시간(중간에 두 번 정지·재개).

### 최종 상태

| 상태 | 단위 | 비고 |
|---|---:|---|
| `draft` + `use_translation: true` | **25,510 (100%)** | 빌드에 반영됨 |
| `needs_human` | **0** | 2026-09-01 전량 문맥 재검토·회수 완료 |
| 미번역 | **0** | |

기존 `needs_human` 286건은 2026-09-01에 로컬 `gemma-4-26b-a4b-it-qat`의 문맥 포함 재번역을 보조로 사용하고 사람이 원문·전후 문맥·용어집을 대조해 전량 회수했다. `センパール`은 사용자 확정 표기인 **`센퍼르`**로 용어집과 기존 번역 7곳을 통일했다. 선택지 `selection_units.json`도 286/286 `draft + use_translation:true`이며 실제 occurrence 401곳을 유지한다.

### 최종 기계 검사 — 위반 0건

빌드에 반영되는 25,510건 전수 대상:
`galaxy_angel_translation.py validate` 통과, 40열 초과 0, 대화 3줄 초과 0, 끝 개행 누락 0, CR 0,
`「」`/`『』` 개수 불일치 0, `・` 개수 불일치 0, 반각 문장부호 0, 전각→반각 치환 0.

### 마무리 단계에서 한 일

1. **실패 배치 회수** — 본 실행 마지막에 미번역 80건이 남았다. 전부 배치 8회가
   통째로 실패한 것(`Expecting ',' delimiter` 6, `id mismatch` 2)이었고, 재시도를
   아무리 해도 같은 자리에서 같은 오류가 재현됐다. **`--batch-size 2`로 낮춰
   조합을 바꾸니 80건 전부 실패 0으로 통과했다.** 무작위 사고가 아니라 특정 배치
   내용에서 모델이 결정론적으로 깨진 JSON을 내놓는 문제였다.
2. **반각 문장부호 정규화** (`moonlit_lovers_normalize_punctuation.py`) — 원문이 `。`로
   끝나는데 번역이 `?`를 쓰는 식으로, 원문에 없던 ASCII 부호가 들어온 117건을
   전각으로 바꿨다. 한국어 마침표·쉼표(`.` `,`)는 올바른 한국어 표기이므로 건드리지
   않는다.
3. **이름 통일** (`moonlit_lovers_unify_names.py`) — 213건. 대부분 `ミルフィー`(밀피)를
   `밀피유`로 쓴 것이다. 짧은 표기가 긴 표기의 접두사라 부분문자열 검사로는 안 잡히는
   유형(스킬의 `キャス ⊂ キャスティ` 함정)이다. 대상 쌍은 짐작이 아니라 용어집의
   `겹치는 표기` 열에서 유도했고, **원문에 짧은 표기만 있는 자리에서만** 치환한다.
   조사가 어긋나는 쌍(`포르테・슈토렌`→`포르테` 등)은 자동 보류하며, 그런 쌍에 실제
   위반이 있으면 조사 규칙 없이는 실행을 거부한다.
4. **줄바꿈** (`moonlit_lovers_reflow_translations.py`) — 14,765건을 40열로 재배치.
5. **3줄 초과 축약** — 줄바꿈 후 91건이 4줄이 됐다(전부 딱 한 줄 초과).
   `moonlit_lovers_shorten_overflow.py`가 3라운드에 걸쳐 점점 빡빡한 목표치로
   재요청해 74건을 해결했고, 남은 10건은 `moonlit_lovers_manual_shortenings.py`에
   손으로 쓴 축약문을 넣었다. 최종 3줄 초과 0건.

### 이번에 밟은 함정 (같은 실수를 반복하지 않기 위해)

- **모델에 줄바꿈된 원문을 보여주면 그 줄바꿈 위치를 따라한다.** 프롬프트로 "줄바꿈
  넣지 마라"라고 해도 소용없었다(거부율 57%). 전송용 원문을 한 줄로 펴서 보내니
  거부율이 0이 됐다. 일본어는 띄어쓰기가 없어 빈 문자열로 이으면 원문이 정확히
  복원된다(`flatten_source`).
- **전각 복원을 무차별로 걸면 한국어 문장부호를 망친다.** 원문에 `Ｈ．Ａ．Ｌ．Ｏ．`가
  있다는 이유로 한국어 문장 끝 마침표까지 전부 `．`로 바뀌어 20단위가 오염됐다.
  `．`와 `，`는 전각 복원 대상에서 제외했다(한국어의 올바른 표기가 ASCII 쪽이다).
  기존 오염분은 "전각 라틴 문자 뒤가 아닌 `．`"만 되돌려 복구했다 — 약어는 유지된다.
- **긴 작업의 저장은 마지막에 한 번만 하면 안 된다.** 축약 도구가 파일 저장을 맨
  끝에서만 하는 바람에 `timeout`에 걸려 죽으면서 이미 통과한 24건이 통째로 날아갔다.
  배치마다 저장하도록 고쳤다.
- **`python -u`를 쓰지 않으면 백그라운드 실행 로그가 통째로 사라진다.** 버퍼에 남은
  출력이 프로세스와 함께 없어져, 무엇을 했는지 알 수 없는 채로 끝났다.
- **줄바꿈은 글자 수가 아니라 포장(packing) 문제다.** 총 99열짜리 문장이 4줄이 되는
  일이 있었다 — `크로노・스트링・엔진에서`(24열)처럼 공백 없는 긴 덩어리가 줄을
  일찍 끊기 때문이다. 축약할 때는 총 길이만 보지 말고 실제 줄바꿈 결과를 봐야 한다.

### 다음 단계

폰트 이식이 끝나면 **재번역 없이** 다음만 다시 돌리면 된다.

```
python tools/moonlit_lovers_reflow_translations.py --assets <assets> --max-columns <실측값>
python tools/moonlit_lovers_shorten_overflow.py   --assets <assets>
```

그 밖에 남은 일은 이전 절의 "여전히 남은 제약"과 같다 — 폰트 글리프 테이블 확정,
압축 해제 크기 제약 확인, 빌드 배선(`galaxy_angel_translation.py apply()`),
전투 메시지(SLG/SLGSTAGE), 잔여 UI/시스템 문자열, 이미지 텍스처 재삽입 및 실기 검증.
