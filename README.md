# 갤럭시 엔젤 문릿 러버즈 한국어 번역 패치

> 🙏 이 패치는 **완벽한 번역을 기대하시는 분보다는, AI 번역 기반이라 발생할 수 있는 사소한 오역이나 어색한 표현이 있어도 크게 개의치 않고 플레이하실 수 있는 분들을 위한 패치**입니다.

> ⚠️ **완역 패치가 아닙니다.** 본편 대사·선택지·시스템 문구·대부분의 UI 이미지는 번역되어 있지만, 아직 찾지 못했거나 처리가 어려운 일부 그래픽 문구는 원문으로 남아 있을 수 있습니다.

PlayStation 2용 『ギャラクシーエンジェル ムーンリットラヴァーズ』 일본판(시리즈 2편)의 비공식 팬 한국어 번역 패치입니다.

- 본편 시나리오 대사 **25,510개**, 선택지 286개, 그 밖의 화면 문구 4,121개를 다룹니다.
- 완성형 한글을 게임 실행 파일 `SLPM_654.29`의 폰트 테이블에 새로 그려 넣는 방식으로 표시합니다.
- UI·함내 명판 이미지의 일본어도 원본 팔레트·픽셀 포맷 그대로 다시 그려 넣습니다.

> 💬 오역, 미번역 문구, 버그를 발견하시면 [Issues 탭](../../issues)에 제보해 주세요.

### 프로젝트 담당자

| 역할 | 담당 |
|---|---|
| 번역 | gemma-4-26b-a4b-it-qat |
| 검수 | Claude Opus 5, 나 |

## 1. 원본 확인

아래 **일본판 ISO와 정확히 일치하는 원본**에만 적용됩니다. 다른 리전·리비전이나 이미 수정된 ISO에는 적용하지 마세요.

| 항목 | 값 |
| --- | --- |
| ISO 크기 | `3,565,256,704 bytes` |
| MD5 | `d62a13914e76ea1770df65a652b0101c` |
| SHA-1 | `7d49242ace85088bd596e75e4b5440c3639e0bd8` |
| SHA-256 | `990be804914335df22223c0070ec677ace4b5684f367dd9b04fa8ab55263a3fe` |

패치 적용 결과는 아래와 같아야 합니다.

| 항목 | 값 |
| --- | --- |
| ISO 크기 | `3,606,837,248 bytes` |
| SHA-256 | `467f53bf8ac2e3cd71aca4754f1871fccfe225e445acd1be11148365782b45c3` |

## 2. 패치 적용

1. [Releases](../../releases)에서 `galaxy_angel_moonlit_lovers_ps2_kr_v0.1.xdelta`를 받습니다.
2. xdelta3 또는 xdelta 패치를 지원하는 프로그램(예: Delta Patcher)에서 **원본 ISO를 Source로** 지정해 적용합니다.

   ```bash
   xdelta3 -d -s "Galaxy Angel - Moonlit Lovers (Japan).iso" \
       galaxy_angel_moonlit_lovers_ps2_kr_v0.1.xdelta \
       "Galaxy_Angel_Moonlit_Lovers_KO_v0.1.iso"
   ```

3. 결과 ISO의 SHA-256이 위 값과 같은지 확인하세요.

패치 파일 자체의 SHA-256은 `f8f5d06b719655ece915cdeaae8ddd9d3ed6360740ebe73bd63038274d54ef9f` 입니다.

원본 게임 파일(ISO, BIOS 등)은 이 저장소에 포함되어 있지 않습니다. 정당하게 소유한 정품 이미지에만 적용하세요.

## 3. 패치 내용

| 영역 | 분량 |
|---|---|
| 본편 시나리오 (SCENARIO) | 대사 25,510개 |
| 선택지 | 286개 |
| 그 밖의 화면 문구 (SLG / SLGSTAGE / SLGRES / ADV / GADAT000 / GAML) | 4,121개 |
| UI·함내 이미지 (GADAT030 / GADAT031 / GADAT032 / SLG / ADV) | 일본어 고유 592종 중 신규 223종 + 기존 369종 |
| 이미지 런타임 사본 (SLGRES / SLGSTAGE / ADV) | 1,205곳 |
| 게임 내 영상 자막 | PSS 27편 한국어 자막 번인 |

- 시나리오 스크립트는 `ADV.DAT`에도 런타임 사본이 있어 36개 블록을 함께 반영합니다.

### 아직 번역 안 된 것 (알려진 미해결 항목)

- `remaining_candidates`와의 차이 705개는 ADV 런타임 사본, SLG 내부 HEADER/STAGE 식별자, 리소스 경로·폰트명입니다. ADV 사본은 시나리오 쪽 번역이 그대로 복사되므로 화면에는 한국어로 나옵니다.
- 그 외 아직 찾지 못한 그래픽 문구가 있을 수 있습니다.

이 목록만으로 "화면에 남은 일본어가 없다"고 판단하면 안 된다는 걸 실제로 겪었습니다. **색인에 아예
없어서 그 차이에도 잡히지 않던 문구가 두 종류 있었습니다.**

- 스테이지 목표 문구 — `dat/slg/table/stage/*.tbl`의 `#030~#035`. 전투 중 목표 확인 화면에 나오는데
  6종 144곳이 일본어였습니다. 같은 화면의 패배 조건만 한국어였던 건 그쪽 문구만 색인에 있었기 때문입니다.
- 전투 조작 안내 — `dat/slg/table/unit/spaparam.tbl`의 ON·열기 계열 8종, 각 49곳.

둘 다 번역했고, 완성된 ISO에서 스테이지 테이블 48개와 `spaparam.tbl`을 다시 디코드해 화면 문구에
일본어가 남지 않았음을 확인했습니다. 남은 `#015`(`GA1.5:ステージ…`)는 개발용 내부 라벨이라 화면에
나오지 않습니다. **점검은 번역 원본이 아니라 완성된 ISO에서 해야 합니다** — 색인에 있어도 사본 일부만
등록돼 실제로는 남아 있는 경우가 있었습니다.

## 4. 직접 빌드하기

**요구 사항**: Python 3, `pip install pillow numpy opencv-python pyxdelta`

`assets/translation/`과 `tools/`만으로는 바로 빌드되지 않습니다. 원본 ISO에서 추출한 데이터가 함께 필요하며, 저작권이 있는 원본 데이터라 저장소에 포함되어 있지 않습니다.

| 항목 | 출처 |
| --- | --- |
| `tools/`, `assets/translation/` | 이 저장소 |
| `source/`, 추출 이미지 | **직접 준비** — 정품 ISO에서 추출 |
| 원본 일본판 ISO | **직접 준비** |

```bash
python tools/moonlit_lovers_build.py \
    --original-iso "Galaxy Angel - Moonlit Lovers (Japan).iso" \
    --output-iso build/Galaxy_Angel_Moonlit_Lovers_KO.iso \
    --original-scenario source/scenario --built-scenario build/scenario \
    --lz-script tools/ikusa_lz.py --container SCENARIO
```

배포용 패치 생성과, **그 패치를 적용해 최종 ISO를 만드는 것**은 아래와 같이 합니다.

```bash
python tools/eternal_lovers_make_release.py \
    --original-iso "Galaxy Angel - Moonlit Lovers (Japan).iso" \
    --patched-iso build/Galaxy_Angel_Moonlit_Lovers_KO.iso \
    --release-dir release --version v0.1 \
    --title "Galaxy Angel - Moonlit Lovers" --slug galaxy_angel_moonlit_lovers

python tools/galaxy_angel_apply_release_patch.py \
    --original-iso "Galaxy Angel - Moonlit Lovers (Japan).iso" \
    --release-dir release \
    --output-iso release/Galaxy_Angel_Moonlit_Lovers_KO_v0.1.iso
```

`galaxy_angel_apply_release_patch.py`는 원본 ISO 해시를 `release.json`과 대조하고, 적용 결과의 해시·크기까지 다시 확인합니다.

## 5. 개발 내역

- **1편 빌더의 일반화**: `moonlit_lovers_build.py`는 1편 `galaxy_angel_build.py`의 컨테이너 재배치·중앙 `IDX.DAT` 미러링 로직을 이 게임의 컨테이너 이름(`SCENARIO.DAT` / `SLG.DAT` / `SLGSTAGE.DAT`)에 맞춘 것입니다.

- **컨테이너 고정 베이스**: 스크립트 엔진이 컨테이너의 원래 LBA를 고정 베이스로 쓰기 때문에, 컨테이너는 원래 extent에 두고 원래 할당을 넘는 블록만 backing 사본으로 우회시킵니다. 이 디스크는 3.5GB라 PIDX의 32비트 컨테이너 상대 오프셋이 디스크 끝까지 닿습니다(4.7GB인 3편은 닿지 않아 별도 처리가 필요합니다).

- **줄바꿈 재배치**: 번역 모델은 줄바꿈을 결정하지 않고 한 줄로 뽑기 때문에, 실측한 대사창 폭에 맞춰 다시 줄을 나눕니다. 원문이 266개 유닛의 이어지는 줄에 넣어 둔 **전각 공백 들여쓰기**는 서식이므로 재배치 후 다시 적용합니다(`tools/moonlit_lovers_reflow_translations.py`).

- **줄 시작 공백 금지**: 원문은 줄을 반각 공백(`0xA0`)으로 시작하는 일이 없습니다. 3편에서 이런 줄이 렌더러를 멈추게 하는 것이 확인되어, 공용 인코더가 전각 공백을 전각 그대로 유지하고 줄 앞 반각 공백은 버리도록 했습니다. 이 게임의 출시본에는 해당 줄이 0건이지만 재빌드 시 재발하지 않도록 막아둡니다.

- **`ADV.DAT` 런타임 사본**: 시나리오 스크립트의 바이트 동일 사본이 들어 있어 `SCENARIO.DAT`만 패치하면 해당 장면이 일본어로 남습니다(`tools/moonlit_lovers_patch_adv_scenario_copies.py`).

자세한 시간순 기록은 [STATUS.md](STATUS.md)에 있습니다.

## 6. 저장소 구성

- `tools/` — 추출·번역 반영·폰트 생성·검증용 파이썬 스크립트
- `assets/translation/` — 번역 텍스트 (이 폴더를 편집하는 것이 번역 작업의 전부입니다)
- `STATUS.md` — 개발 기록

저장소에 포함되지 않는 것 (`.gitignore` 참고, 직접 빌드 시 원본 디스크에서 재추출):

- `source/`, `original/`, `assets/full_extraction/` — 원본 게임에서 추출한 바이너리
- 추출·번역 이미지
- `build/`, `release/` — 빌드 결과물 (패치는 Releases에 올립니다)

## 7. 라이선스 / 권리

**누구나 자유롭게 사용하셔도 됩니다.** 별도의 허락을 구할 필요 없이, 아래 조건(비영리 팬 번역 목적, 정품 게임 소유)만 지켜주시면 내려받아 적용하거나 포크해서 참고·수정하실 수 있습니다.

- **도구 소스코드** (`tools/*.py`): [MIT 라이선스](LICENSE)
- **번역 텍스트** (`assets/translation/`): 비영리 팬 번역 목적으로 자유롭게 공유·수정하실 수 있으나, 게임을 판매하거나 상업적으로 이용하는 용도로는 사용하지 말아주세요.
- **게임 원본 데이터**: 『갤럭시 엔젤』의 저작권은 BROCCOLI에 있습니다. 이 저장소는 원본 게임 파일(디스크 이미지, 실행 파일, 폰트, 대사 바이너리 등)을 포함하거나 배포하지 않으며, 패치는 반드시 정식 발매된 게임을 정당하게 소유한 상태에서 개인적으로 적용하는 용도로만 사용해주세요.
