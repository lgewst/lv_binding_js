# C++ 자동 생성

공용 명세로 wrapper와 위젯 구현
React 이름 20개, C++ 클래스 19개 지원. (Input은 Textarea와 공유)
Window와 Canvas는 미지원.

공통 생성기는 `component_cpp_emitter.py`, 복합 처리법은 `component_cpp_rules.py`와 `templates/features/`.
위젯별 주문표는 `scripts/data/widgets_manifest.json`의 `cppBinding.component`.

## 생성

```sh
python3 autogen/cpp_emitter.py --widget Chart --target all
python3 autogen/cpp_emitter.py --widget Chart --target all --check
```

기본 실행은 wrapper만 생성. `--target component`는 구현 두 파일, `--target all`은 세 파일 생성.
wrapper는 `autogen/generated/`, 구현은 `autogen/generated/components/`에 저장.
`--check`는 파일 수정 없이 최신 여부만 검사.

`generated/`는 Git에서 제외. 빌드할 때 필요한 파일을 다시 생성.
생성 파일은 맨 위 안내 주석만 유지. 설명 주석은 생성기와 템플릿에서 관리.

## 비교 빌드

기본 빌드는 수작업 코드 사용. 아래 옵션은 지원 클래스 전체를 생성 코드로 교체.

```sh
cmake -S . -B build-generated-switch -DBUILD_LVGL_SIMULATOR=ON -DGENERATED_CPP_COMPONENTS="Switch;Arc;Chart;Checkbox;Slider;Dropdownlist;Textarea;Roller;Keyboard;ProgressBar;Calendar;Line;Button;GIF;Image;Mask;Tabs;Text;View"
cmake --build build-generated-switch -j 4
```

## 테스트

생성기 테스트는 빈 임시 폴더에 생성한 뒤 검사. 기존 `generated/` 파일 불필요.
실제 LVGL 검사는 위 비교 빌드를 먼저 실행.

```sh
python3 -m unittest discover -s autogen/tests -p '*_test.py'
python3 test/autogen/run.py --suite native
python3 test/autogen/run.py --suite api
python3 test/autogen/run.py --suite screenshots --compare-build-dir build
```

`test/autogen/`은 실행기 `run.py`, JS 검사 `api.js`, C++ 검사 `native.cpp`, 화면 앱 `widget_gallery/index.jsx`로 구성.
기본 `--suite all`은 위 검사를 모두 실행. 원본 빌드는 `--build-dir build`, 생성 빌드는 `--build-dir build-generated-switch`로 선택.
화면은 20개 위젯, 변경 상태 8개와 `Numeric`, `TextView`, `ButtonMask` 조합으로 총 33쌍 비교.
