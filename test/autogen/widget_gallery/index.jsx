import React from 'react';
import path from 'tjs:path';
import {
  Arc, Button, Checkbox, Dimensions, EAlignType, GIF, Image, Line, Mask,
  ProgressBar, Render, Slider, Switch, Text, View, Roller, Dropdownlist, Textarea, Input,
  EDropdownlistDirection, EDropdownListArrowDirection,
  Calendar, Keyboard, Tabs, Chart,
} from 'lvgljs-ui';

// 수작업 wrapper와 생성 wrapper의 비교 화면에서 표시할 위젯을 선택.
// 아래 위젯별 분기는 화면 구성용이며 C++ 생성기의 처리 규칙과 별개.
const name = tjs.env.AUTOGEN_WIDGET || 'Switch';
const { width, height } = Dimensions.window;
const label = { 'text-color': '#334155' };
const row = {
  width: 360, height: 60, display: 'flex', 'justify-content': 'space-between',
  'align-items': 'center', 'border-width': 0, padding: 8,
};

// 선택한 위젯의 초기 상태 또는 변경된 속성을 화면에 표시.
function Preview({ phase = 0 }) {
  const [keyboardInput, setKeyboardInput] = React.useState(null);
  switch (name) {
    case 'Switch':
      return <View style={{ ...row, height: 260, 'flex-direction': 'column' }}>
        <Switch checked={false} /><Switch checked={true} />
        <Switch checked={false} disabled={true} /><Switch checked={true} disabled={true} />
      </View>;
    case 'Text':
      return <View style={{ width: 540, height: 200, 'border-width': 0,
        display: 'flex', 'flex-direction': 'column', 'justify-content': 'space-around' }}>
        <Text style={label}>Text: JavaScript string to C++ string</Text>
        <Text style={{ 'text-color': 'blue' }}>{['Array', ' + ', 123]}</Text>
        <Text>{456}</Text>
      </View>;
    case 'View':
      return <View style={{ width: 560, height: 230, display: 'flex',
        'justify-content': 'space-around', 'align-items': 'center', 'background-color': '#e8f1ff' }}>
        {['Child A', 'Child B', 'Child C'].map((text) =>
          <View key={text} style={{ width: 150, height: 140, display: 'flex',
            'justify-content': 'center', 'align-items': 'center', 'background-color': 'white' }}>
            <Text>{text}</Text>
          </View>)}
      </View>;
    case 'Image':
      return <Image src={path.resolve(import.meta.dirname, '../../image/2/2.png')}
        style={{ width: 175, height: 120, transform: 'scale(2)' }} />;
    case 'GIF':
      return <GIF src={path.resolve(import.meta.dirname, '../../gif/1/sample.gif')}
        paused={true} style={{ width: 60, height: 80, transform: 'scale(2)' }} />;
    case 'Line':
      return <Line points={[[0, 130], [90, 15], [180, 100], [270, 35], [360, 120]]}
        style={{ 'line-width': 8, 'line-color': 'blue', 'line-rounded': true }} />;
    case 'Button':
      return <Button style={{ width: 250, height: 90, display: 'flex',
        'justify-content': 'center', 'align-items': 'center', 'background-color': '#1976d2' }}>
        <Text style={{ 'text-color': 'white' }}>Button child text</Text>
      </Button>;
    case 'Checkbox':
      return <View style={{ ...row, width: 400, height: 240, 'flex-direction': 'column',
        'align-items': 'flex-start' }}>
        <Checkbox text="Unchecked" checked={false} />
        <Checkbox text="Checked" checked={true} />
        <Checkbox text="Disabled" disabled={true} />
        <Checkbox text="Checked + disabled" checked={true} disabled={true} />
      </View>;
    case 'Slider':
      return <Slider range={[-50, 100]} value={55}
        style={{ width: 500, height: 22 }}
        indicatorStyle={{ 'background-color': '#1976d2' }}
        knobStyle={{ 'background-color': '#ef4444' }} />;
    case 'ProgressBar':
      return <ProgressBar range={[0, 100]} value={70} useAnimation={false}
        style={{ width: 500, height: 38 }}
        indicatorStyle={{ 'background-color': '#22a06b' }} />;
    case 'Arc':
      return <Arc range={[0, 100]} value={65} mode="normal" changeRate={100}
        startAngle={20} endAngle={285} backgroundStartAngle={20}
        backgroundEndAngle={285} rotation={0}
        style={{ width: 230, height: 230 }}
        indicatorStyle={{ 'arc-color': '#1976d2', 'arc-width': 18 }}
        knobStyle={{ 'background-color': '#ef4444' }} />;
    case 'Roller':
      return <Roller options={phase ? ['Spring', 'Summer', 'Autumn', 'Winter'] : ['Apple', 'Banana', 'Cherry', 'Orange']}
        selectIndex={phase ? 2 : 1} visibleRowCount={phase ? 5 : 3} infinity={phase > 0}
        style={{ width: 300 }} selectedStyle={{ 'background-color': '#1976d2' }}
        onChange={() => {}} />;
    case 'Dropdownlist':
      return <Dropdownlist items={phase ? ['Red', 'Green', 'Blue', 'White'] : ['Apple', 'Banana', 'Cherry']}
        selectIndex={phase ? 2 : 1} style={{ width: 330, height: 60 }}
        direction={phase ? EDropdownlistDirection.top : EDropdownlistDirection.bottom}
        arrow={phase ? EDropdownListArrowDirection.up : EDropdownListArrowDirection.down}
        highlightSelect={phase > 0} onChange={() => {}} />;
    case 'Textarea':
      return <View style={{ width: 600, height: 300, 'border-width': 0,
        display: 'flex', 'flex-direction': 'column', 'justify-content': 'space-around' }}>
        <Textarea style={{ width: 560, height: 120 }} autoKeyBoard={false}
          placeholder="Multiline placeholder" value={phase ? 'Updated text\nSecond line' : 'Textarea first line\nSecond line'}
          onChange={() => {}} />
        <Textarea style={{ width: 560, height: 80 }} autoKeyBoard={false}
          placeholder={phase ? 'Updated placeholder' : 'Empty textarea placeholder'} value="" />
      </View>;
    case 'Input':
      return <View style={{ width: 600, height: 300, 'border-width': 0,
        display: 'flex', 'flex-direction': 'column', 'justify-content': 'space-around' }}>
        <Input style={{ width: 560, height: 60 }} autoKeyBoard={false} maxlength={30}
          value={phase ? 'Updated input' : 'Single line input'} placeholder="Input placeholder" />
        <Input style={{ width: 560, height: 60 }} autoKeyBoard={false} maxlength={12}
          value="secret123" mode={phase ? 'text' : 'password'} />
        <Input style={{ width: 560, height: 60 }} autoKeyBoard={false} maxlength={30}
          value="" placeholder={phase ? 'Updated input placeholder' : 'Empty input placeholder'} />
      </View>;
    case 'Calendar':
      return <Calendar style={{ width: 340, height: 340 }}
        today="2026-11-16" shownMonth={phase ? '2026-12' : '2026-11'}
        highLightDates={phase ? ['2026-12-10', '2026-12-25'] : ['2026-11-16', '2026-11-20']}
        onChange={() => {}} />;
    case 'Keyboard':
      return <View style={{ width: 700, height: 340, 'border-width': 0,
        display: 'flex', 'flex-direction': 'column', 'justify-content': 'space-around' }}>
        <Input ref={setKeyboardInput} style={{ width: 660, height: 45 }}
          autoKeyBoard={false} value={phase ? '12345' : 'Keyboard reference'} />
        <Keyboard style={{ width: 660, height: 240 }} textarea={keyboardInput}
          mode={phase ? 'number' : 'lower'} />
      </View>;
    case 'Tabs':
      return <Tabs key={phase} tabs={['Overview', 'Details']}
        tabPosition={phase ? 'bottom' : 'top'} tabSize={48}
        style={{ width: 680, height: 300 }}>
        <View style={{ width: 600, height: 180 }}><Text>{phase ? 'Recreated with bottom tabs' : 'First tab content'}</Text></View>
        <View style={{ width: 600, height: 180 }}><Text>Second tab content</Text></View>
      </Tabs>;
    case 'Chart':
      return <Chart style={{ width: 620, height: 280 }} type={phase ? 'bar' : 'line'}
        pointNum={6} divLineCount={[5, 6]} leftAxisRange={[0, 100]} rightAxisRange={[0, 100]}
        bottomAxisLabels={['A', 'B', 'C', 'D', 'E', 'F']}
        leftAxisOption={{ majorLen: 6, minorLen: 3, majorNum: 6, minorNum: 2, drawSize: 40 }}
        bottomAxisOption={{ majorLen: 6, minorLen: 3, majorNum: 6, minorNum: 2, drawSize: 30 }}
        leftAxisData={[{ color: 'blue', data: phase ? [65, 25, 80, 40, 90, 55] : [10, 45, 30, 75, 50, 90] }]}
        rightAxisData={[{ color: 'red', data: [80, 60, 70, 30, 45, 20] }]} />;
    default:
      throw new Error('Unknown gallery widget: ' + name);
  }
}

const windowStyle = { width, height, padding: 0, 'border-width': 0,
  'border-radius': 0, 'background-color': '#f4f7fb' };
const panelStyle = { left: 90, top: 110, width: width - 180, height: height - 180,
  display: 'flex', 'flex-direction': 'column', 'justify-content': 'center',
  'align-items': 'center', 'background-color': 'white', 'border-color': '#dae2ed' };

// 비교 화면의 공통 배경을 구성하고 환경 변수에 따라 상태 변경.
function Gallery() {
  const [phase, setPhase] = React.useState(0);
  React.useEffect(() => {
    const target = Number(tjs.env.AUTOGEN_PHASE || '0');
    if (!target) return;
    const timer = setTimeout(() => setPhase(target), 200);
    return () => clearTimeout(timer);
  }, []);
  // 기존 화면 조합을 같은 gallery 진입점에서 선택.
  if (name === 'ButtonMask') return (
  <View style={{ width, height }}>
    <Mask onClick={() => {}}>
      <Button
        align={{ type: EAlignType.ALIGN_CENTER }}
        style={{
          width: 190,
          height: 70,
          'background-color': 'white',
          'display': 'flex',
          'justify-content': 'center',
          'align-items': 'center',
        }}
        onPressedStyle={{ 'background-color': 'blue' }}
        onClick={() => {}}
      />
    </Mask>
  </View>
  );
  if (name === 'TextView') return (
    <View style={{ width, height, 'background-color': 'white' }}>
      <View style={{ width: 240, height: 100, display: 'flex', 'flex-direction': 'column' }}>
        <Text>Text wrapper</Text>
        <Text>{['A', 1, 'B']}</Text>
      </View>
    </View>
  );
  if (name === 'Numeric') {
    const ranges = [[-50, 100], [0, 200], [-100, 100]];
    const values = [-20, 150, 60];
    return (
    <View style={{ width, height, 'background-color': 'white' }}>
      <Text style={{ left: 30, top: 20 }}>Slider / ProgressBar / Arc: phase {phase}</Text>
      <Slider
        style={{ left: 50, top: 85, width: 260, height: 18 }}
        range={ranges[phase]} value={values[phase]}
        indicatorStyle={{ 'background-color': 'blue' }}
        knobStyle={{ 'background-color': 'red' }}
        onChange={() => {}}
      />
      <ProgressBar
        style={{ left: 50, top: 150, width: 260, height: 24 }}
        range={ranges[phase]} value={values[phase]} useAnimation={false}
        indicatorStyle={{ 'background-color': 'green' }}
      />
      <Arc
        style={{ left: 370, top: 65, width: 170, height: 170 }}
        range={ranges[phase]} value={values[phase]}
        startAngle={[20, 40, 60][phase]} endAngle={[290, 270, 250][phase]}
        backgroundStartAngle={[10, 30, 50][phase]}
        backgroundEndAngle={[300, 280, 260][phase]}
        rotation={[0, 45, 90][phase]}
        mode={['normal', 'symmetrical', 'reverse'][phase]}
        changeRate={[50, 100, 200][phase]}
        indicatorStyle={{ 'arc-color': 'blue', 'arc-width': 14 }}
        knobStyle={{ 'background-color': 'red' }} onChange={() => {}}
      />
    </View>
    );
  }
  return (
  <View style={windowStyle}>
    {name === 'Mask' ?
      <Mask>
        <View align={{ type: EAlignType.ALIGN_CENTER }} style={{ width: 440, height: 240,
          display: 'flex', 'flex-direction': 'column', 'justify-content': 'space-around',
          'align-items': 'center', 'background-color': 'white' }}>
          <Text>Mask: top layer overlay</Text>
          <Button style={{ width: 220, height: 65, display: 'flex',
            'justify-content': 'center', 'align-items': 'center' }}><Text>Child button</Text></Button>
        </View>
      </Mask>
      : <React.Fragment>
        <Text style={{ left: 90, top: 45, 'text-color': '#17324d' }}>{name}</Text>
        <View style={panelStyle}><Preview phase={phase} /></View>
      </React.Fragment>}
  </View>
  );
}
Render.render(<Gallery />);
