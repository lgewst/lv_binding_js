// JS 호출, 잘못된 입력과 반복 생성 및 정리 경로를 검사.
const render = globalThis[Symbol.for('lvgljs')].NativeRender;
const native = render.NativeComponents;
const iterations = Number(tjs.env.AUTOGEN_ITERATIONS || '40');

// 조건이 맞지 않으면 사례 이름과 함께 검사 중단.
function check(ok, label) {
  if (!ok) throw new Error('AssertionError: ' + label);
}

// 예외가 필요한 호출에서 실제 예외 발생 여부를 검사.
function mustThrow(fn, label) {
  let thrown = false;
  try { fn(); } catch (_) { thrown = true; }
  check(thrown, label);
}

// JS 참조가 사라진 객체를 정리해 등록 객체 수를 검사.
function collect() {
  tjs.engine.gc.run();
  tjs.engine.gc.run();
}

// 파일에서 읽은 실제 범위를 ArrayBuffer로 변환.
function bufferOf(bytes) {
  return bytes instanceof ArrayBuffer ? bytes
    : bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}
const png = bufferOf(await tjs.readFile('test/assets/icons/01n.png'));
const gif = bufferOf(await tjs.readFile('test/gif/1/sample.gif'));
check(Number.isInteger(iterations) && iterations > 0, 'positive iterations');


// 숫자 변환, 범위, 혼합 인자와 Arc 이미지 호출 검사.
async function checkNumeric() {
  const slider = new native.Slider({ uid: 'numeric-api-slider' });
  check(slider.setRange([-50, 100]) === undefined, 'Slider range');
  check(slider.setValue(-20) === undefined, 'Slider negative value');
  check(slider.setValue(55.9) === undefined, 'Slider fractional value');
  check(slider.setValue('invalid') === undefined, 'Slider argument guard');

  const bar = new native.ProgressBar({ uid: 'numeric-api-bar' });
  check(bar.setRange(-100, 200) === undefined, 'ProgressBar separate arguments');
  check(bar.setValue(30, false) === undefined, 'ProgressBar no animation');
  check(bar.setValue(80, true) === undefined, 'ProgressBar animation');
  check(bar.setValue(70) === undefined, 'ProgressBar missing boolean');

  const arc = new native.Arc({ uid: 'numeric-api-arc' });
  arc.setRange([-50, 100]);
  arc.setValue(40);
  for (const [method, value] of Object.entries({
    setStartAngle: 20, setEndAngle: 270, setBackgroundStartAngle: 0,
    setBackgroundEndAngle: 300, setRotation: 45, setMode: 1, setChangeRate: 100,
  })) {
    check(arc[method](value) === undefined, 'Arc ' + method);
  }
  check(arc.setArcImage(null, 0, '\uf00c') === true, 'Arc symbol');
  // 기존 수작업 wrapper와 동일하게 인자가 세 개인 호출을 요구.
  check(arc.setArcImage(null, 0) === false, 'Arc missing third argument');
  check(arc.setArcImage(null, 0, '') === true, 'Arc clear symbol');
  const buffer = png;
  check(arc.setArcImage(buffer, 0, '') === true, 'Arc image data');
  slider.close();
  bar.close();
  arc.close();
}

// 목록, 선택 인덱스와 Textarea 및 Input 속성 검사.
async function checkSelection() {
  const roller = new native.Roller({ uid: 'api-roller' });
  check(roller.setOptions(['Apple', 9, 'Banana'], 3, false) === undefined, 'Roller filtered options');
  roller.setSelectIndex(1);
  roller.setVisibleRowCount(3);
  roller.setOptions(['Spring', 'Summer', 'Winter'], 3, true);

  const dropdown = new native.Dropdownlist({ uid: 'api-dropdown' });
  dropdown.setItems(['Apple', 'Banana', 'Cherry'], 3);
  check(typeof dropdown.setSelectIndex === 'function', 'correct selection method');
  check(dropdown.setSelectIndex(2) === undefined, 'Dropdownlist select');
  dropdown.setDir(8); // 아래쪽 방향을 나타내는 LV_DIR_BOTTOM 값.
  dropdown.setArrowDir(2);
  dropdown.setHighLightSelect(true);
  dropdown.setText('Selected fruit');

  const textarea = new native.Textarea({ uid: 'api-textarea' });
  textarea.setAutoKeyboard(false);
  textarea.setOneLine(false);
  textarea.setPlaceHolder('Placeholder');
  textarea.setText('Line 1\nLine 2');
  textarea.setPasswordMode(true);
  textarea.setPasswordMode(false);
  textarea.setMaxLength(12);
  check(textarea.setAutoKeyboard(true) === undefined, 'boolean to int32');
  textarea.setAutoKeyboard(false);

  // Input은 Textarea 클래스를 단일 줄 모드로 사용.
  const input = new native.Textarea({ uid: 'api-input' });
  input.setAutoKeyboard(false);
  input.setOneLine(true);
  input.setMaxLength(6);
  input.setText('abcdefghi');
  input.setPasswordMode(true);
  input.setPasswordMode(false);
  for (const comp of [input, textarea, dropdown, roller]) comp.close();
}

// 날짜, 탭과 Chart 축 및 scatter 호출 검사.
async function checkComplex() {
  const calendar = new native.Calendar({ uid: 'complex-calendar' });
  calendar.setToday(2026, 11, 16);
  calendar.setShownMonth(2026, 12);
  calendar.setHighlightDates([[2026, 12, 10], [2026, 12, 25]], 2);

  const textarea = new native.Textarea({ uid: 'complex-textarea' });
  textarea.setAutoKeyboard(false);
  const keyboard = new native.Keyboard({ uid: 'complex-keyboard' });
  keyboard.setTextarea(textarea);
  // Keyboard의 모드별 호출은 공통 반복 검사에서 확인.

  const tabs = new native.TabView({ uid: 'complex-tabs', tabPosition: 4, tabSize: 48 });
  const content = new native.View({ uid: 'complex-content' });
  tabs.setTab('Content', content);

  const chart = new native.Chart({ uid: 'complex-chart' });
  chart.setType(1);
  chart.setPointNum(3);
  chart.setDivLineCount([4, 4]);
  for (const side of ['Left', 'Right', 'Top', 'Bottom']) {
    chart['set' + side + 'AxisRange']([0, 100]);
    chart['set' + side + 'AxisLabels'](['A', 'B', 'C']);
    chart['set' + side + 'AxisOption']({ majorLen: 6, minorLen: 3, majorNum: 3, minorNum: 2, drawSize: 30 });
    chart['set' + side + 'AxisData']([{ color: 255, data: [10, 40, 80] }]);
  }
  chart.setType(3);
  chart.setScatterData([{ color: 16711680, data: [10, 20, 30, 40, 50, 60] }]);
  check(chart.refresh() === undefined, 'refresh');
  keyboard.close(); // 연결된 Textarea보다 먼저 Keyboard를 해제.
  // 부모가 자식 LVGL 객체를 관리하므로 이 실행 검사에서는 중복 종료 생략.
  calendar.close();
  chart.close();
}

// 생성 wrapper의 타입 거부와 생성자 기본값 검사.
async function checkContracts() {
  const tabs = new native.TabView({ uid: 'default-size-tabs' }); // tabSize의 기본값은 0.
  mustThrow(() => new native.TabView({ uid: 'bad-tabs', tabSize: 'bad' }), 'constructor type');
  mustThrow(() => new native.TabView({ uid: 'throwing-tabs', get tabPosition() { throw Error('getter'); } }), 'constructor getter');
  const keyboard = new native.Keyboard({ uid: 'guard-keyboard' });
  mustThrow(() => keyboard.setTextarea({}), 'plain object');
  const view = new native.View({ uid: 'guard-view' });
  mustThrow(() => keyboard.setTextarea(view), 'wrong component class');
  const textarea = new native.Textarea({ uid: 'guard-textarea' });
  textarea.setAutoKeyboard(false);
  keyboard.setTextarea(textarea);
  keyboard.close();
  textarea.close();
  view.close();
  mustThrow(() => tabs.setTab('closed', view), 'closed child');
  tabs.close();
  const chart = new native.Chart({ uid: 'guard-chart' });
  mustThrow(() => chart.setLeftAxisData([{ color: 1, data: Symbol('bad') }]), 'invalid nested array');
  mustThrow(() => chart.setLeftAxisOption({ get majorLen() { throw Error('getter'); } }), 'object getter');
  chart.close();
  check(chart.refresh() === undefined, 'closed refresh');
  check(native.Window === undefined && native.Canvas === undefined, 'unsupported native components');
}

// Switch와 단순 위젯의 고유 호출을 한 묶음으로 준비.
function createWidgetBatch(index) {
  const component = new native.Switch({ uid: 'switch-api-' + index });
  for (const value of [true, false, true, false]) {
    check(component.setChecked(value) === undefined, 'checked call');
    check(component.setDisabled(value) === undefined, 'disabled call');
  }
  component.setChecked('invalid');
  component.setDisabled(1);
  const view = new native.View({ uid: 'simple-view-' + index });
  const button = new native.Button({ uid: 'simple-button-' + index });
  const text = new native.Text({ uid: 'simple-text-' + index });
  const checkbox = new native.Checkbox({ uid: 'simple-checkbox-' + index });
  const slider = new native.Slider({ uid: 'simple-slider-' + index });
  const bar = new native.ProgressBar({ uid: 'simple-bar-' + index });
  const keyboard = new native.Keyboard({ uid: 'simple-keyboard-' + index });
  const textarea = new native.Textarea({ uid: 'simple-target-' + index });
  textarea.setAutoKeyboard(false);
  const child = new native.View({ uid: 'simple-child-' + index });
  check(text.setText('한글 Text ' + index) === undefined, 'Text string');
  check(text.setText('') === undefined, 'Text empty string');
  check(checkbox.setText('Checkbox ' + index) === undefined, 'Checkbox text');
  for (const value of [true, false, true, false]) {
    check(checkbox.setChecked(value) === undefined, 'Checkbox checked');
    check(checkbox.setDisabled(value) === undefined, 'Checkbox disabled');
  }
  check(slider.setRange([-50, 100]) === undefined, 'Slider range array');
  check(bar.setRange(-50, 100) === undefined, 'ProgressBar separate arguments');
  for (const value of [-100, -50, -7, 0, 77, 100, 140]) {
    check(slider.setValue(value) === undefined, 'Slider value');
    check(bar.setValue(value, false) === undefined, 'ProgressBar value');
  }
  check(bar.setValue(80, true) === undefined, 'ProgressBar animation');
  check(bar.setValue(20, false) === undefined, 'ProgressBar stop animation');
  keyboard.setTextarea(textarea);
  for (const mode of [0, 1, 2, 3, 0]) keyboard.setMode(mode);
  button.appendChild(child);
  view.appendChild(child);
  return [component, keyboard, textarea, child, view, button, text, checkbox, slider, bar];
}


// 이미지 자원과 네 방향 축이 있는 위젯을 준비.
function createResourceBatch(index) {
  const image = new native.Image({ uid: 'lifetime-image-' + index });
  image.setImageBinary(png);
  const animation = new native.GIF({ uid: 'lifetime-gif-' + index });
  animation.setGIFBinary(gif);
  animation.pause();
  const chart = new native.Chart({ uid: 'lifetime-chart-' + index });
  chart.setPointNum(3);
  for (const side of ['Left', 'Right', 'Top', 'Bottom']) {
    chart['set' + side + 'AxisLabels'](['A', 'B', 'C']);
    chart['set' + side + 'AxisOption']({
      majorLen: 6, minorLen: 3, majorNum: 3, minorNum: 1, drawSize: 30,
    });
    chart['set' + side + 'AxisData']([{ color: 255, data: [10, 30, 20] }]);
  }
  return [image, animation, chart];
}

// 중복 close, GC와 부모 우선 삭제를 같은 절차로 반복 검사.
function exerciseLifecycle(createBatch, expectedCount, label, mode) {
  const baseline = render.RenderUtil.getCompMapSize();
  for (let index = 0; index < iterations; ++index) {
    let widgets = createBatch(index);
    check(render.RenderUtil.getCompMapSize() === baseline + expectedCount, label + ' live');
    if (mode === 'parent-first') {
      const parent = new native.View({ uid: label + '-parent-' + index });
      for (const widget of widgets) parent.appendChild(widget);
      parent.close();
    }
    if (mode !== 'gc') {
      for (const widget of widgets) { widget.close(); widget.close(); }
    }
    widgets = null;
    collect();
    check(render.RenderUtil.getCompMapSize() === baseline, label + ' cleanup ' + mode);
  }
}

for (const run of [checkNumeric, checkSelection, checkComplex]) {
  const baseline = render.RenderUtil.getCompMapSize();
  await run();
  collect();
  check(render.RenderUtil.getCompMapSize() === baseline, run.name + ' cleanup');
  console.log('API_PASS', run.name);
}
if (tjs.env.AUTOGEN_CONTRACTS !== '0') {
  const baseline = render.RenderUtil.getCompMapSize();
  await checkContracts();
  collect();
  check(render.RenderUtil.getCompMapSize() === baseline, 'contracts cleanup');
  console.log('API_PASS contracts');
} else {
  console.log('API_SKIP generated-only contracts');
}
for (const mode of ['close', 'gc', 'parent-first']) {
  exerciseLifecycle(createWidgetBatch, 10, 'components', mode);
  exerciseLifecycle(createResourceBatch, 3, 'resources', mode);
  console.log('API_PASS lifecycle', mode, iterations);
}
console.log('API_PASS all');
tjs.exit(0);
