# 자동 생성

공용 명세 `scripts/data/widgets_manifest.json` 하나로 C++ 과 React 양쪽을 생성한다.
`cppBinding` 은 C++ 생성기가, `props` 는 React 생성기가 읽는다.
`bridgeMethod` 는 양쪽이 함께 읽으므로 JS 에 노출되는 이름이 두 층에서 어긋날 수 없다.

## C++

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


## React 자동 생성

공용 명세의 `props` 로 React 컴포넌트와 host config 를 생성.
대상은 `generate.ts` 가 true 인 **20개**. `index.ts` 가 등록하는 컴포넌트 전부다.

C++ 쪽과 같은 층으로 나눠 두었다.

| 파일 | 역할 |
| --- | --- |
| `widget_ts_emitter.py` | 명세에서 위젯 하나를 읽고, 쓸 수 없는 명세를 거부한다 |
| `component_ts_rules.py` | `behavior.kind` 별 세터 본문 |
| `component_ts_emitter.py` | `comp.ts` · `config.ts` 렌더링 |
| `ts_emitter.py` | 진입점 |

양식은 `templates/comp.ts.in` 과 `templates/config.ts.in`.

```sh
python3 autogen/ts_emitter.py                  # 대상 전부
python3 autogen/ts_emitter.py --widget Arc     # 하나만
python3 autogen/ts_emitter.py --check          # 저장된 것이 최신인지
```

결과는 `src/render/react/components/<ReactName>/` 의 `comp.ts` · `config.ts` 다.
**이 두 파일이 생성물이다** — 손으로 고치면 `gen:all:check` 가 걸러낸다. 같은
디렉터리의 `manual.ts` 는 수작업이고 생성 대상이 아니다.

`--dest generated` 를 주면 `autogen/generated/react/` 로 빠진다. 수작업 코드와
대조할 때만 쓴다.

C++ 쪽은 자리를 덮지 않고 설정 시점에 바꿔 끼운다. `GENERATED_CPP_COMPONENTS` 가
기본으로 19개 전부라 보통 빌드는 생성 코드를 쓰고, 수작업 `.cpp` 는 비교 기준으로
트리에 남는다. `""` 로 주면 수작업 쪽이 빌드된다.

### 생성 규칙

prop 마다 `behavior.kind` 가 세터 모양을 정한다.

| kind | 생성되는 세터 |
| --- | --- |
| `stateToggle` | `value` 와 같은 코드가 나온다. C++ 쪽이 `behavior.state` 를 읽어 구분한다 |
| `styleState` | `setStyle({ comp, styleSheet, compName, styleType, oldStyleSheet })` |
| `event` | `handleEvent(comp, fn, EVENTTYPE_MAP.*)` |
| `value` | `guard` 가 있으면 조기 반환, 없으면 블록. `compare` 가 연산자를 정한다 |
| `tuple` | `callStyle: array` 는 분해 후 배열 전달, `spread` 는 원소별 인자 |
| `options` | `Array.isArray` 검사 후 `comp.set*(arr, arr.length, …)` |
| `enumMap` | `mapValues` 로 조회표를 만들고 `typeof map[val]` 검사 후 호출 |

`compare` 와 `guard` 는 `value` · `stateToggle` 이, `compare` 는 `enumMap` 도 읽는다.
읽지 않는 kind 에 적으면 조용히 무시되므로 거부한다. `enumMap` 의 `compare: "none"`
은 이전 값을 아예 보지 않는 자리에 쓴다 (Chart 의 `type`).

### manual 탈출구

규칙으로 표현되지 않는 prop 은 `manual` 에 근거와 함께 적고, 세터는 같은
디렉터리의 수작업 `manual.ts` 에 둔다.

```ts
export function manualSetters({ comp, newProps, oldProps }) {
  return { src(url) { /* 손으로 쓴다 */ } };
}
```

**세터 표의 순서가 네이티브 호출 순서다.** 그래서 manual 항목은 `after` 로 어느
세터 뒤에 오는지를 적는다. `after` 가 없으면 생성 세터들보다 앞이다. `after` 는
생성 세터나 앞에 적힌 manual 만 가리킬 수 있어, 자리가 하나로 정해진다.

```json
{ "name": "scatterData", "tsType": "number[]", "after": "pointNum",
  "reason": "축 데이터 변환" }
```

이게 중요한 이유: Chart 는 수작업 코드에서 `type` · `pointNum` 다음에 축 데이터를
보낸다. manual 을 표 앞에 몰아 넣으면 차트 종류와 점 개수를 정하기 전에 데이터가
먼저 가고, 예외가 아니라 그림이 틀어진다.

`manual.ts` 는 생성 대상이 아니다. 위젯 10개의 prop 21건이 여기에 있다.
`children: "manual"` 인 위젯은 `manualChildren` 도 함께 내보낸다 (Tabs).
근거 없는 `manual` 항목과 생성자에서 소비되는 prop 은 거부한다.

### reactClass

클래스 본문은 위젯마다 다르고 규칙으로 유도되지 않아, 수작업 코드에서 읽어
명세에 적었다.

| 필드 | 값 |
| --- | --- |
| `children` | `full` 전부 위임 / `append` appendChild 만 / `none` 모두 빈 메서드 / `manual` manual.ts 의 manualChildren 에 위임 |
| `movement` | `delegate` / `block` |
| `close` | `delegate` / `block` |
| `styleResetOldSheet` | `null` 또는 `{}` |
| `constructorCalls` | 생성자에서 부르는 네이티브 메서드 (Input · Textarea) |
| `nativeKey` | NativeComponents 의 키 (Input → Textarea) |
| `propsType` | Props 타입 이름 (Dropdownlist → DropdownListProps) |
| `constructorProps` | 생성자 인자로 받아 super 로 넘기는 prop. 조회표와 기본값을 함께 적는다 (Tabs) |
| `instanceFields` | 생성자에서 세우는 인스턴스 필드. 값은 리터럴만 (Tabs 의 `currentAppendIndex`) |
| `stashProps` | 세터 표를 거치지 않고 `setProps` 진입 시 인스턴스에 얹는 prop (Tabs 의 `tabs`) |

`stashProps` 가 따로 있는 이유: 세터 표는 그 prop 이 들어왔을 때만 돈다. 자식 훅이
읽는 값은 prop 이 빠진 재렌더에서도 같이 비워져야 하므로 표 밖에서 덮는다.

### 테스트

```sh
python3 -m unittest discover -s autogen/tests -p '*_test.py'
python3 test/autogen/run.py --suite react
```

`--suite react` 는 빌드가 필요 없다. `test/autogen/react_parity.js` 가 지금
컴포넌트 자리에 있는 생성 코드와, 전환 직전 커밋에서 꺼낸 수작업 코드를 같은
입력으로 실행해 네이티브 호출을 비교한다. 기준 커밋은 해시로 박아 두었으므로
(`BASELINE_REV`) 낡거나 누가 고칠 수 없다.
비교 대상은 공통 prop 13종, prop 별 값 순서(manual prop 포함), 전체 prop 동시
설정, 클래스 메서드 10종, host config 의 모양과 createInstance · commitUpdate 다.

manual prop 의 값은 `MANUAL_VALUES` 에 모양을 적어 둔다. 일반적인 값을 넣으면
수작업 세터의 분기 앞에서 양쪽이 똑같이 끝나 버려 세터가 틀려도 차이가 드러나지
않는다. 빠진 항목이 있으면 실패한다. 실제로 수작업 세터의 네이티브 호출 26곳을
하나씩 망가뜨려 보면 26곳 모두 실패로 잡힌다.
위젯 20개 1011경우.

스텁으로 바꾸는 것은 `react`, `react-reconciler`, `../config`, `../../core/bridge`,
`../../core/style` 과 그 `color` · `symbol`, `../../utils/helpers`,
`../../utils/assets`, 그리고 명세에서 만든 `../../core/lv_conf` · `../../core/lv_types`
다. `../common/index` 의 `CommonComponentApi` 와 각 위젯의 `manual.ts` 는 실제
구현을 불러온다 — 수작업 세터가 부르는 `colorTransform` · `BUILT_IN_SYMBOL` ·
`isValidUrl` · `loadLocalAsset` 이 비교 대상이기 때문이다.

전체 prop 동시 설정이 세터 순서를 드러내는 유일한 경우다. 클래스 메서드는 그
시나리오를 흘려 보낸 인스턴스에서 부른다 — 빈 인스턴스에서는 `setProps` 가 심어
둔 값을 읽는 훅이 양쪽 모두 우연히 같아진다 (Tabs 의 자식 배정).

`Image` · `GIF` 의 원격 asset 분기는 `then` 안에서 네이티브를 부르므로, 기록은
마이크로태스크를 비운 뒤에 찍는다.

근거를 적어 둔 차이는 `react_parity.js` 의 `EXPECTED` 에 모아 두었다.
`prop#*` 로 적으면 그 prop 의 모든 경우를 한 근거로 덮는다.
목록에 없는 차이가 생기면 실패하고, 더 이상 발생하지 않는 항목이 남아 있어도 실패한다.

TypeScript 타입은 실행 시점에 사라지므로 이 비교로는 확인되지 않는다. 그래서
`--suite react` 가 생성 파일을 컴포넌트 옆(`_generated_<위젯>/`)에 잠깐 놓고
`tsc --noEmit` 을 돌린다. 상대 import 가 풀리는 깊이에 둬야 하기 때문이고,
돌린 뒤에는 지운다. 저장소의 `tsconfig.json` 은 `src/` 만 보므로 생성물이
그냥은 타입체크되지 않는다.

### 생성 제외

| 위젯 | 이유 |
| --- | --- |
| Canvas | `index.ts` 에 등록되지 않는다. 세터를 접근자로 선언하고 Object.assign 으로 적용해 구조가 다르다 |
| Window | `index.ts` 에서 주석 처리되어 등록되지 않는다 |
