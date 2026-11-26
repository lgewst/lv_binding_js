// Compare the hand-written React component with the generated one by running both.
//
//   node test/autogen/react_parity.js            # every widget marked ts
//   node test/autogen/react_parity.js Switch Arc # only these
//
// Exit status is 1 when any difference is not listed in EXPECTED.

const fs = require("fs");
const path = require("path");
const os = require("os");
const vm = require("vm");
const { execFileSync } = require("child_process");
const esbuild = require("esbuild");

const REPO = path.join(__dirname, "../..");
const MANIFEST = path.join(REPO, "scripts/data/widgets_manifest.json");
const COMPONENTS = path.join(REPO, "src/render/react/components");

// 컴포넌트가 생성 코드로 바뀐 뒤로, 비교 기준은 바뀌기 직전 커밋이다. 거기서
// 수작업 파일을 꺼내 쓰므로 기준이 낡지도, 누가 고칠 수도 없다.
const BASELINE_REV = "b2705e6d51621c149b546a12ed6bfd2acaca2ebb";
const BASELINE_DIR = path.join(os.tmpdir(), `lvgljs-baseline-${BASELINE_REV.slice(0, 12)}`);

// 기준 커밋의 수작업 comp.ts · config.ts 를 한 번 꺼내 둔다. 그 시점의 수작업
// 컴포넌트는 manual.ts 를 불러오지 않으므로 함께 꺼낼 것이 없다.
function materializeBaseline(names) {
  for (const name of names) {
    for (const file of ["comp.ts", "config.ts"]) {
      const out = path.join(BASELINE_DIR, name, file);
      if (fs.existsSync(out)) continue;
      fs.mkdirSync(path.dirname(out), { recursive: true });
      const rel = `src/render/react/components/${name}/${file}`;
      fs.writeFileSync(out, execFileSync("git", ["show", `${BASELINE_REV}:${rel}`],
        { cwd: REPO, maxBuffer: 1 << 24 }));
    }
  }
}

// Only the leaves are stubbed. CommonComponentApi is loaded for real, so a
// widget that drops its own override of a common prop is compared against the
// implementation that then takes over.
const STUBS = {
  react: "export default {};",
  "react-reconciler": "export default {};",
  "../../core/style": "export const StyleProps = {};",
  "../../core/style/color": "export const colorTransform = (c) => \"color:\" + c;",
  "../../core/style/symbol": "export const BUILT_IN_SYMBOL = { ok: \"SYM:ok\" };",
  "../../utils/helpers": "export const isValidUrl = (u) => String(u).startsWith(\"http\");",
  "../../utils/assets": `
    export const fetchAssetBinary = (url) => {
      globalThis.__record("fetchAssetBinary", url);
      return Promise.resolve(new ArrayBuffer(4));
    };
    export const loadLocalAsset = (src, label, onSuccess) => {
      globalThis.__record("loadLocalAsset", src);
      onSuccess(new ArrayBuffer(4));
    };
  `,
  "../config": `
    export const EAlignType = new Proxy({}, { get: (t, k) => "ALIGN:" + String(k) });
    export const EVENTTYPE_MAP = new Proxy({}, { get: (t, k) => "EVENT:" + String(k) });
    export const STYLE_TYPE = new Proxy({}, { get: (t, k) => "STYLE:" + String(k) });
    export const handleEvent = (comp, fn, type) =>
      globalThis.__record("handleEvent", type, typeof fn);
    export const setStyle = (a) => globalThis.__record("setStyle", a.compName, a.styleType,
      a.styleSheet, a.oldStyleSheet === null ? "null" : a.oldStyleSheet, a.isInit);
    export const styleGetterProp = [];
    export const applyDataPropsToDataset = () => globalThis.__record("applyDataProps");
    export const LvgljsComponentConfig = {};
  `,
  "../../core/bridge": `
    class NativeBase {
      constructor({ uid }) {
        this.uid = uid;
        this._style = {};
        // 생성자 안에서 부르는 네이티브 메서드도 기록되어야 하므로,
        // 기반 클래스가 스스로를 감싼 Proxy 를 돌려준다.
        return new Proxy(this, {
          get(target, prop) {
            if (prop in target) {
              const value = target[prop];
              return typeof value === "function" ? value.bind(target) : value;
            }
            return (...args) => globalThis.__record(String(prop), ...args);
          },
        });
      }
      get style() { return this._style; }
      set style(v) { this._style = v; }
      close() { globalThis.__record("super.close"); }
      // pause·resume 을 여기서 정의해 둬야 "메서드 없음" 과 "super 위임" 이
      // 서로 다른 기록으로 남는다. 안 그러면 두 경우를 구분할 수 없다.
      pause() { globalThis.__record("super.pause"); }
      resume() { globalThis.__record("super.resume"); }
      appendChild(c) { globalThis.__record("super.appendChild", c && c.uid); }
      moveToFront() { globalThis.__record("super.moveToFront"); }
      moveToBackground() { globalThis.__record("super.moveToBackground"); }
      scrollIntoView() { globalThis.__record("super.scrollIntoView"); }
    }
    // super.X() 는 Proxy 를 지나치지 않고 프로토타입을 바로 타므로,
    // 체인 끝에 기록기를 달아 둔다.
    Object.setPrototypeOf(NativeBase.prototype, new Proxy({}, {
      get: (t, p) => (...args) => globalThis.__record(String(p), ...args),
    }));
    const widget = new Proxy({}, { get: () => NativeBase });
    export const GetBridge = () => ({ NativeRender: { NativeComponents: widget } });
  `,
};

// Differences that are expected because the generated code is correct and the
// hand-written code is not. Keyed by scenario id; anything unlisted fails, and
// so does a listed entry that no longer differs.
const EXPECTED = {
  Chart: {
    "divLineCount#*": "수작업 Chart 의 tuple 세터는 배열·NaN 검사가 없다",
    "leftAxisRange#*": "위와 같음",
    "rightAxisRange#*": "위와 같음",
    "topAxisRange#*": "위와 같음",
    "bottomAxisRange#*": "위와 같음",
  },
  ProgressBar: {
    'range#4 "nope"': "수작업은 배열이 아닌 값을 그대로 setRange 로 넘긴다",
  },
  Line: {
    "common#0 style": 'Line 이 CommonComponentApi 에 compName: "Keyboard" 를 넘긴다',
    "common#7 onPressedStyle": "위와 같은 compName 오류",
    "common#8 scrollbarStyle": "위와 같은 compName 오류",
    "common#9 onScrollbarPressedStyle": "위와 같은 compName 오류",
    "common#10 onScrollbarScrollingStyle": "위와 같은 compName 오류",
    "points#3 undefined": "수작업은 배열 검사 전에 .length 를 읽어 예외가 난다",
    'points#4 "nope"': "수작업은 배열이 아닌 값을 그대로 setPoints 에 넘긴다",
  },
};

// 수작업 config 는 위젯마다 native = null 과 commitUnmount 를 들쭉날쭉 선언한다.
// 둘 다 읽는 곳이 없으므로 비교에서 뺀다. 나머지 멤버는 그대로 비교한다.
const DEAD_CONFIG_MEMBERS = ["native", "commitUnmount"];

const COMMON_PROPS = [
  ["style", { color: "#fff" }],
  ["onClick", () => {}],
  ["onPressed", () => {}],
  ["onLongPressed", () => {}],
  ["onLongPressRepeat", () => {}],
  ["onPressLost", () => {}],
  ["onReleased", () => {}],
  ["onPressedStyle", { color: "#eee" }],
  ["scrollbarStyle", { color: "#ddd" }],
  ["onScrollbarPressedStyle", { color: "#ccc" }],
  ["onScrollbarScrollingStyle", { color: "#bbb" }],
  ["align", { type: 1, pos: [0, 0] }],
  ["alignTo", { type: 1, pos: [1, 2], parent: { uid: "p" } }],
];

// Every lv_conf constant the manifest names, each with a distinct value so a
// wrong constant in a lookup table cannot compare equal to the right one.
// core/lv_types 는 불러오는 순간 브리지를 읽으므로 스텁으로 둔다. 표의 값은
// 명세에서 만들어 상수마다 서로 다르다.
function lvTypesStub(manifest) {
  const tables = {};
  for (const widget of manifest.widgets) {
    for (const entry of (widget.reactClass || {}).constructorProps || []) {
      if (!entry.map) continue;
      const rows = Object.values(entry.mapValues || {})
        .map((v) => `  ${v}: "${entry.mapSource}:${v}",`).join("\n");
      tables[entry.mapSource] = `export const ${entry.mapSource} = {\n${rows}\n};`;
    }
  }
  return Object.values(tables).join("\n");
}

function lvConfStub(manifest) {
  const names = new Set();
  for (const widget of manifest.widgets) {
    for (const prop of widget.props || []) {
      for (const value of Object.values(prop.behavior.mapValues || {})) names.add(value);
    }
  }
  return [...names].map((n) => `export const ${n} = "lv_conf:${n}";`).join("\n");
}

function stubPlugin(manifest, widgetName) {
  const filter = new RegExp("^(" + Object.keys(STUBS).concat("../../core/lv_conf", "../../core/lv_types")
    .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")$");
  // 기준 쪽 파일은 임시 폴더에 있어서 상대 import 가 풀리지 않는다. 실제로
  // 불러오는 두 모듈은 저장소 안의 자리를 직접 가리킨다.
  const common = path.join(COMPONENTS, "common/index.ts");
  const manual = path.join(COMPONENTS, widgetName, "manual.ts");
  return {
    name: "stubs",
    setup(build) {
      build.onResolve({ filter: /^\.\.\/common\/index$/ }, () => ({ path: common }));
      build.onResolve({ filter: /^\.\/manual$/ }, () => ({ path: manual }));
      build.onResolve({ filter }, (args) => ({ path: args.path, namespace: "stub" }));
      build.onLoad({ filter: /.*/, namespace: "stub" },
        (args) => ({
          contents: args.path === "../../core/lv_conf" ? lvConfStub(manifest)
            : args.path === "../../core/lv_types" ? lvTypesStub(manifest)
            : STUBS[args.path],
          loader: "ts",
        }));
    },
  };
}

async function loadModule(manifest, widgetName, file, record) {
  const built = await esbuild.build({
    entryPoints: [file],
    bundle: true,
    write: false,
    format: "cjs",
    platform: "neutral",
    plugins: [stubPlugin(manifest, widgetName)],
  });
  const sandbox = { module: { exports: {} }, console, __record: record };
  sandbox.exports = sandbox.module.exports;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  new vm.Script(built.outputFiles[0].text, { filename: file }).runInContext(sandbox);
  return sandbox.module.exports;
}

// Anything asked of `comp` that the instance does not define is a native call.
function instrument(Comp, calls) {
  const instance = new Comp({ uid: "u1" });
  const proxy = new Proxy(instance, {
    get(target, prop) {
      if (prop in target) {
        const value = target[prop];
        return typeof value === "function" ? value.bind(proxy) : value;
      }
      return (...args) => calls.push([String(prop), ...args]);
    },
  });
  return proxy;
}


// 수작업 세터는 값의 모양을 보고 갈라진다. 일반적인 값을 넣으면 분기 앞에서 양쪽이
// 똑같이 끝나 버려서, 세터가 틀려도 차이가 드러나지 않는다. 그래서 manual prop 은
// 실제 모양을 적어 둔다. 빠진 항목이 있으면 아래에서 실패한다.
const SERIES = [{ color: "#f00", data: [[1, 2], [3, 4]] }];
const AXIS_OPTION = { majorLen: 5, minorLen: 2, majorNum: 4, minorNum: 2, drawSize: 10 };
const AXIS_DATA = [{ color: "#0f0", data: [1, 2, 3] }];
const DATE = new Date(2024, 4, 17);

const MANUAL_VALUES = {
  "Chart.scatterData": [SERIES, SERIES, [{ data: [[5, 6]] }], undefined],
  "Chart.leftAxisOption": [AXIS_OPTION, AXIS_OPTION, { ...AXIS_OPTION, majorLen: 9 }, {}],
  "Chart.leftAxisData": [AXIS_DATA, AXIS_DATA, [{ data: [4] }], undefined],
  "Chart.rightAxisOption": "Chart.leftAxisOption",
  "Chart.rightAxisData": "Chart.leftAxisData",
  "Chart.topAxisOption": "Chart.leftAxisOption",
  "Chart.topAxisData": "Chart.leftAxisData",
  "Chart.bottomAxisOption": "Chart.leftAxisOption",
  "Chart.bottomAxisData": "Chart.leftAxisData",
  // ok 는 BUILT_IN_SYMBOL 의 키라 심볼 분기로, http 는 원격, ./a.png 는 로컬로 간다.
  "Image.src": ["ok", "ok", "https://example.com/a.png", "./a.png", undefined],
  "GIF.src": "Image.src",
  "GIF.paused": [true, true, false, undefined],
  "Text.children": ["a", "a", ["a", "b"], 1, undefined],
  "Calendar.today": [DATE, DATE, new Date(2025, 0, 1), undefined],
  "Calendar.shownMonth": "Calendar.today",
  "Calendar.highLightDates": [[DATE], [DATE], [new Date(2025, 0, 1)], undefined],
  "Keyboard.textarea": [{ uid: "t1" }, { uid: "t1" }, { uid: "t2" }, undefined],
  "Dropdownlist.arrow": [1, 1, 2, "nope", undefined],
  "Input.mode": ["password", "password", "text", undefined],
  "Textarea.mode": "Input.mode",
  "ProgressBar.style": [{ color: "#fff" }, { color: "#fff" }, { color: "#000" }],
};

function manualValues(widget, prop) {
  const key = `${widget.reactName}.${prop.name}`;
  let values = MANUAL_VALUES[key];
  if (typeof values === "string") values = MANUAL_VALUES[values];
  if (values === undefined) {
    throw new Error(`MANUAL_VALUES 에 ${key} 가 없다. 실제 모양을 적을 것`);
  }
  return values;
}

// manual 이면 위 표에서, 아니면 kind 와 선언된 타입에서 고른다.
// passive 도 behavior 가 없으므로 manual 목록에 있는지로 가른다.
function valuesFor(prop, widget) {
  if ((widget.manual || []).includes(prop)) return manualValues(widget, prop);
  const kind = (prop.behavior || {}).kind;
  const type = prop.tsType || "";
  if (kind === "styleState") return [{ c: 1 }, { c: 1 }, { c: 2 }];
  if (kind === "event") return [() => {}, () => {}];
  if (kind === "tuple") return [[0, 100], [0, 100], [10, 90], [NaN, 5], "nope", [1]];
  if (kind === "options") return [["a", "b"], ["a", "b"], ["c"], undefined, "nope"];
  if (kind === "enumMap") {
    // 조회표의 실제 키를 전부 써야 한다. 엉뚱한 키는 양쪽 모두 아무 일도 하지 않는다.
    const keys = Object.keys(prop.behavior.mapValues || {});
    return [keys[0], ...keys, "bogus", undefined];
  }
  if (type.startsWith("(")) return [() => {}, () => {}];
  if (type.includes("Date")) {
    const d = new Date(2024, 4, 17);
    return [d, d, new Date(2025, 0, 1), [d], undefined];
  }
  if (type.includes("[]")) return [["a", "b"], ["a", "b"], ["c"], undefined, null, "nope"];
  if (type.includes("boolean")) return [true, true, false, 1, null, undefined];
  if (type.includes("string")) return ["a", "a", "b", "", null, undefined];
  // "5" right after 5 separates a strict comparison from a loose one, and
  // null from undefined: isNaN(null) is false where isNaN(undefined) is true.
  return [0, 0, 5, "5", NaN, null, undefined];
}

// 함수와 Date 는 structuredClone 이 못 다루므로 한 겹만 베낀다.
function clone(source) {
  const out = {};
  for (const [key, value] of Object.entries(source)) {
    if (Array.isArray(value)) out[key] = value.slice();
    else if (value instanceof Date) out[key] = new Date(value.getTime());
    else if (value && typeof value === "object") out[key] = { ...value };
    else out[key] = value;
  }
  return out;
}

function label(value) {
  if (typeof value === "function") return "fn";
  if (typeof value === "number" && Number.isNaN(value)) return "NaN";
  const text = JSON.stringify(value);
  return text === undefined ? "undefined" : text;
}

function scenarios(widget) {
  const out = COMMON_PROPS.map(([name, value], i) => ({
    id: `common#${i} ${name}`, props: { [name]: value }, old: {},
  }));
  // manual prop 도 똑같이 돌린다. 이게 빠지면 수작업 세터를 하나도 비교하지 않는다.
  for (const prop of widget.props.concat(widget.manual || [])) {
    let previous = {};
    valuesFor(prop, widget).forEach((value, i) => {
      const props = { [prop.name]: value };
      out.push({ id: `${prop.name}#${i} ${label(value)}`, props, old: previous });
      previous = props;
    });
  }
  for (const passive of widget.passive || []) {
    const reader = readerOf(widget, passive);
    if (!reader) continue;
    for (const value of valuesFor(passive, widget).slice(0, 3)) {
      out.push({
        id: `${reader.name} with ${passive.name}=${label(value)}`,
        props: { [reader.name]: valuesFor(reader, widget)[0], [passive.name]: value }, old: {},
      });
    }
  }
  // Setting everything at once is the only way the setter table's order shows.
  const everything = {};
  for (const prop of widget.props.concat(widget.manual || [], widget.passive || [])) {
    const first = valuesFor(prop, widget)[0];
    if (first !== undefined && first !== null) everything[prop.name] = first;
  }
  out.push({ id: "all props at once", props: everything, old: {} });
  return out;
}

// passive prop 을 읽는 쪽. 명세의 readBy 가 이름을 적어 두므로 그걸 먼저 쓰고,
// 없으면 extraArgs 와 oldStyleSheetProp 에서 찾는다.
function readerOf(widget, passive) {
  const all = widget.props.concat(widget.manual || []);
  if (passive.readBy) {
    const named = all.find((p) => p.name === passive.readBy);
    if (named) return named;
  }
  const byArgs = widget.props.find((p) => (p.behavior.extraArgs || [])
    .some((a) => a.fromProp === passive.name));
  if (byArgs) return byArgs;
  return widget.props.find((p) => p.behavior.oldStyleSheetProp === passive.name);
}

function replacer(key, value) {
  if (typeof value === "function") return "[fn]";
  if (typeof value === "number" && Number.isNaN(value)) return "[NaN]";
  return value;
}

// Image·GIF 의 원격 asset 분기는 then 안에서 네이티브를 부른다. 동기로 기록하면
// 그 호출이 아예 안 보이므로, 마이크로태스크를 비운 뒤에 찍는다.
async function record(id, shared, run) {
  shared.length = 0;
  let error = null;
  try {
    run();
    for (let i = 0; i < 4; i += 1) await Promise.resolve();
  } catch (e) {
    error = String((e && e.message) || e);
  }
  return { id, calls: JSON.stringify(shared, replacer), error };
}



// setProps, then the methods the reconciler calls outside it.
async function runWidget(Comp, cases, shared) {
  // ProgressBar 의 수작업 style 세터처럼 인자를 고치는 세터가 있어, 실행마다 복제한다.
  const results = [];
  for (const scenario of cases) {
    const props = clone(scenario.props);
    const old = clone(scenario.old);
    results.push(await record(scenario.id, shared, () =>
      instrument(Comp, shared).setProps(props, old)));
  }
  const surface = [
    ["class setStyle", (c) => c.setStyle({ color: "#abc" })],
    ["class appendChild", (c) => {
      c.appendChild({ uid: "child1" });
      c.appendChild({ uid: "child2" });
    }],
    ["class appendInitialChild", (c) => c.appendInitialChild({ uid: "child" })],
    ["class insertBefore", (c) => c.insertBefore({ uid: "a" }, { uid: "b" })],
    ["class moveToFront", (c) => c.moveToFront && c.moveToFront()],
    ["class moveToBackground", (c) => c.moveToBackground && c.moveToBackground()],
    ["class scrollIntoView", (c) => c.scrollIntoView && c.scrollIntoView()],
    ["class close", (c) => c.close()],
    ["class pause", (c) => c.pause && c.pause()],
    ["class resume", (c) => c.resume && c.resume()],
  ];
  // 전체 prop 을 넣은 인스턴스에서 부른다. Tabs 의 자식 배정처럼 setProps 가 심어
  // 둔 값을 읽는 훅은 빈 인스턴스에서는 양쪽이 우연히 같아진다.
  const seeded = cases.length ? clone(cases[cases.length - 1].props) : {};
  for (const [id, run] of surface) {
    results.push(await record(id, shared, () => {
      const comp = instrument(Comp, shared);
      comp.setProps(seeded, {});
      shared.length = 0;
      run(comp);
    }));
  }
  return results;
}

// The host config is mostly shape, but createInstance and commitUpdate reach
// the component, so drive those too.
function configShape(Config) {
  const instance = new Config();
  const members = new Set([
    ...Object.getOwnPropertyNames(instance),
    ...Object.getOwnPropertyNames(Object.getPrototypeOf(instance)),
  ]);
  members.delete("constructor");
  for (const dead of DEAD_CONFIG_MEMBERS) members.delete(dead);
  return JSON.stringify({
    tagName: instance.tagName,
    shouldSetTextContent: instance.shouldSetTextContent(),
    members: [...members].sort(),
  });
}

function runConfig(Config, props, shared) {
  const instance = new Config();
  return [
    record("config createInstance", shared,
      () => instance.createInstance(props, null, null, null, "u1")),
    record("config commitUpdate", shared,
      () => instance.commitUpdate(instance.createInstance(props, null, null, null, "u1"),
        null, {}, props, null)),
  ];
}

function show(entry) {
  return entry.error ? `throw ${entry.error}` : entry.calls;
}

async function main() {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST, "utf8"));
  const wanted = process.argv.slice(2);
  const widgets = manifest.widgets.filter(
    (w) => (w.generate || {}).ts && (wanted.length === 0 || wanted.includes(w.reactName))
  );
  if (widgets.length === 0) {
    console.error("대조할 위젯이 없다");
    return 1;
  }

  materializeBaseline(widgets.map((w) => w.reactName));

  let failures = 0;
  let accountedTotal = 0;
  let caseTotal = 0;

  for (const widget of widgets) {
    const name = widget.reactName;
    const genFile = path.join(COMPONENTS, name, "comp.ts");
    if (!fs.existsSync(genFile)) {
      console.log(`${name}: 컴포넌트가 없다 — python3 autogen/ts_emitter.py`);
      failures += 1;
      continue;
    }

    const handLog = [];
    const genLog = [];
    const handModule = await loadModule(manifest, name, path.join(BASELINE_DIR, name, "comp.ts"),
      (...a) => handLog.push(a));
    const genModule = await loadModule(manifest, name, genFile, (...a) => genLog.push(a));
    const cases = scenarios(widget);
    const hand = await runWidget(handModule[`${name}Comp`], cases, handLog);
    const gen = await runWidget(genModule[`${name}Comp`], cases, genLog);

    const handConfig = await loadModule(manifest, name, path.join(BASELINE_DIR, name, "config.ts"), () => {});
    const genConfig = await loadModule(manifest, name, path.join(COMPONENTS, name, "config.ts"), () => {});
    const first = {};
    for (const prop of widget.props) {
      const value = valuesFor(prop, widget)[0];
      if (value !== undefined) first[prop.name] = value;
    }
    hand.push({ id: "config", calls: configShape(handConfig.default), error: null },
      ...runConfig(handConfig.default, first, handLog));
    gen.push({ id: "config", calls: configShape(genConfig.default), error: null },
      ...runConfig(genConfig.default, first, genLog));

    const expected = EXPECTED[name] || {};

    const differences = [];
    const accounted = [];
    hand.forEach((entry, i) => {
      if (entry.calls === gen[i].calls && entry.error === gen[i].error) return;
      // "prop#*" 는 그 prop 의 모든 경우를 한 근거로 덮는다. 세터 전체가
      // 수작업과 다른 계통일 때 같은 줄을 수십 번 적지 않기 위한 것이다.
      const wildcard = entry.id.includes("#")
        ? `${entry.id.slice(0, entry.id.indexOf("#"))}#*` : null;
      const why = expected[entry.id] || (wildcard ? expected[wildcard] : undefined);
      (why ? accounted : differences).push({ id: entry.id, hand: entry, gen: gen[i], why });
    });
    for (const id of Object.keys(expected)) {
      const matches = (d) => d.id === id ||
        (id.endsWith("#*") && d.id.startsWith(id.slice(0, -1)));
      if (!accounted.some(matches)) {
        console.log(`${name}: [${id}] 는 더 이상 차이가 없다. EXPECTED 에서 지울 것`);
        failures += 1;
      }
    }

    caseTotal += hand.length;
    accountedTotal += accounted.length;
    if (differences.length === 0) {
      console.log(`${name}: ${hand.length - accounted.length}/${hand.length} 동일` +
        (accounted.length ? `, ${accounted.length} 의도된 차이` : ""));
      for (const d of accounted) {
        console.log(`    [${d.id}] ${d.why}`);
      }
    } else {
      failures += 1;
      console.log(`${name}: ${differences.length}/${hand.length} 설명되지 않은 불일치`);
      for (const d of differences) {
        console.log(`    [${d.id}]`);
        console.log(`      수작업: ${show(d.hand)}`);
        console.log(`      생성  : ${show(d.gen)}`);
      }
    }
  }

  // 생성 대상에서 빠진 위젯의 EXPECTED 블록은 위 루프가 보지 않는다.
  // 인자로 위젯을 골라 돌린 경우에는 비교 대상이 아닌 게 당연하므로 건너뛴다.
  for (const name of wanted.length ? [] : Object.keys(EXPECTED)) {
    if (!widgets.some((w) => w.reactName === name)) {
      console.log(`EXPECTED 에 [${name}] 가 있는데 비교 대상이 아니다. 지울 것`);
      failures += 1;
    }
  }

  console.log();
  if (failures) {
    console.log(`${failures}건이 해결되지 않았다`);
    return 1;
  }
  console.log(`위젯 ${widgets.length}개, ${caseTotal}경우 중 ` +
    `근거를 적어 둔 차이 ${accountedTotal}건을 제외하면 모두 같다`);
  return 0;
}

main().then(process.exit).catch((error) => {
  console.error(error);
  process.exit(1);
});
