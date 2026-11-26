// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import * as lv_conf from "../../core/lv_conf";
import { StyleProps } from "../../core/style";
import { CommonComponentApi, CommonProps } from "../common/index";
import {
  EVENTTYPE_MAP,
  STYLE_TYPE,
  handleEvent,
  setStyle,
  styleGetterProp,
  applyDataPropsToDataset,
} from "../config";

import { GetBridge } from "../../core/bridge";
import { manualSetters } from "./manual";

const bridge = GetBridge();
const NativeComp = bridge.NativeRender.NativeComponents.Chart;

const chartType = {
  none: lv_conf.LV_CHART_TYPE_NONE,
  line: lv_conf.LV_CHART_TYPE_LINE,
  bar: lv_conf.LV_CHART_TYPE_BAR,
  scatter: lv_conf.LV_CHART_TYPE_SCATTER,
};

export type ChartProps = CommonProps & {
  indicatorStyle?: StyleProps;
  itemStyle?: StyleProps;
  type?: string;
  divLineCount?: [number, number];
  pointNum?: number;
  leftAxisLabels?: any[];
  rightAxisLabels?: any[];
  topAxisLabels?: any[];
  bottomAxisLabels?: any[];
  leftAxisRange?: [number, number];
  rightAxisRange?: [number, number];
  topAxisRange?: [number, number];
  bottomAxisRange?: [number, number];
  scatterData?: any[];
  leftAxisOption?: any;
  leftAxisData?: any[];
  bottomAxisOption?: any;
  bottomAxisData?: any[];
  rightAxisOption?: any;
  rightAxisData?: any[];
  topAxisOption?: any;
  topAxisData?: any[];
  pointStyle?: StyleProps;
};

function setChartProps(comp, newProps: ChartProps, oldProps: Partial<ChartProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "Chart", comp, newProps, oldProps }),
    indicatorStyle(styleSheet) {
      setStyle({
        comp,
        styleSheet,
        compName: "Chart",
        styleType: STYLE_TYPE.PART_INDICATOR,
        oldStyleSheet: oldProps.pointStyle,
      });
    },
    itemStyle(styleSheet) {
      setStyle({
        comp,
        styleSheet,
        compName: "Chart",
        styleType: STYLE_TYPE.PART_ITEMS,
        oldStyleSheet: oldProps.pointStyle,
      });
    },
    type(val) {
      if (typeof chartType[val] !== "undefined") {
        comp.setType(chartType[val]);
      }
    },
    divLineCount(arr) {
      if (!Array.isArray(arr)) return;
      const [min, max] = arr;
      if (min === oldProps.divLineCount?.[0] && max === oldProps.divLineCount?.[1]) return;
      if (isNaN(min) || isNaN(max)) return;
      comp.setDivLineCount([min, max]);
    },
    pointNum(val) {
      if (val !== oldProps.pointNum) {
        comp.setPointNum(val);
      }
    },
    scatterData: manual.scatterData,
    leftAxisOption: manual.leftAxisOption,
    leftAxisData: manual.leftAxisData,
    bottomAxisOption: manual.bottomAxisOption,
    bottomAxisData: manual.bottomAxisData,
    rightAxisOption: manual.rightAxisOption,
    rightAxisData: manual.rightAxisData,
    topAxisOption: manual.topAxisOption,
    topAxisData: manual.topAxisData,
    leftAxisLabels(val) {
      if (val !== oldProps.leftAxisLabels) {
        comp.setLeftAxisLabels(val);
      }
    },
    rightAxisLabels(val) {
      if (val !== oldProps.rightAxisLabels) {
        comp.setRightAxisLabels(val);
      }
    },
    topAxisLabels(val) {
      if (val !== oldProps.topAxisLabels) {
        comp.setTopAxisLabels(val);
      }
    },
    bottomAxisLabels(val) {
      if (val !== oldProps.bottomAxisLabels) {
        comp.setBottomAxisLabels(val);
      }
    },
    leftAxisRange(arr) {
      if (!Array.isArray(arr)) return;
      const [min, max] = arr;
      if (min === oldProps.leftAxisRange?.[0] && max === oldProps.leftAxisRange?.[1]) return;
      if (isNaN(min) || isNaN(max)) return;
      comp.setLeftAxisRange([min, max]);
    },
    rightAxisRange(arr) {
      if (!Array.isArray(arr)) return;
      const [min, max] = arr;
      if (min === oldProps.rightAxisRange?.[0] && max === oldProps.rightAxisRange?.[1]) return;
      if (isNaN(min) || isNaN(max)) return;
      comp.setRightAxisRange([min, max]);
    },
    topAxisRange(arr) {
      if (!Array.isArray(arr)) return;
      const [min, max] = arr;
      if (min === oldProps.topAxisRange?.[0] && max === oldProps.topAxisRange?.[1]) return;
      if (isNaN(min) || isNaN(max)) return;
      comp.setTopAxisRange([min, max]);
    },
    bottomAxisRange(arr) {
      if (!Array.isArray(arr)) return;
      const [min, max] = arr;
      if (min === oldProps.bottomAxisRange?.[0] && max === oldProps.bottomAxisRange?.[1]) return;
      if (isNaN(min) || isNaN(max)) return;
      comp.setBottomAxisRange([min, max]);
    },
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class ChartComp extends NativeComp {
  constructor({ uid }) {
    super({ uid });
    this.uid = uid;

    const style = super.style;
    const that = this;
    this.style = new Proxy(this, {
      get(obj, prop) {
        if (styleGetterProp.includes(prop)) {
          return style[prop].call(that);
        }
      },
    });
  }
  setProps(newProps: ChartProps, oldProps: Partial<ChartProps>) {
    setChartProps(this, newProps, oldProps);
  }
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
  close() {
    super.close();
  }
  setStyle(style, type = STYLE_TYPE.PART_MAIN) {
    setStyle({
      comp: this,
      styleSheet: style,
      compName: "Chart",
      styleType: type,
      oldStyleSheet: null,
      isInit: false,
    });
  }
  moveToFront() {
    super.moveToFront();
  }
  moveToBackground() {
    super.moveToBackground();
  }
  scrollIntoView() {
    super.scrollIntoView();
  }
}
