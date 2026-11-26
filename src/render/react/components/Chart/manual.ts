// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.
import { colorTransform } from "../../core/style/color";

const CHART_COLOR_USE_THEME = -1;

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    scatterData(data) {
      if (data !== oldProps?.scatterData) {
        data = data.map((item) => {
          const arr = [];
          item.data.forEach((item1) => {
            arr.push(item1[0]);
            arr.push(item1[1]);
          });
          return {
            color: item.color === void 0 ? CHART_COLOR_USE_THEME : colorTransform(item.color),
            data: arr,
          };
        });

        comp.setScatterData(data);
      }
    },
    leftAxisOption(options) {
      if (
        options.majorLen == void 0 ||
        options.minorLen == void 0 ||
        options.majorNum == void 0 ||
        options.minorNum == void 0 ||
        !options.drawSize
      ) {
        return;
      }
      if (options != oldProps?.leftAxisOption) {
        comp.setLeftAxisOption(options);
      }
    },
    leftAxisData(data) {
      if (data !== oldProps?.leftAxisData) {
        data = data.map((item) => ({
          ...item,
          color: item.color === void 0 ? CHART_COLOR_USE_THEME : colorTransform(item.color),
        }));
        comp.setLeftAxisData(data);
      }
    },
    bottomAxisOption(options) {
      if (
        options.majorLen == void 0 ||
        options.minorLen == void 0 ||
        options.majorNum == void 0 ||
        options.minorNum == void 0 ||
        !options.drawSize
      ) {
        return;
      }

      if (options != oldProps?.bottomAxisOption) {
        comp.setBottomAxisOption(options);
      }
    },
    bottomAxisData(data) {
      if (data !== oldProps?.bottomAxisData) {
        data = data.map((item) => ({
          ...item,
          color: item.color === void 0 ? CHART_COLOR_USE_THEME : colorTransform(item.color),
        }));
        comp.setBottomAxisData(data);
      }
    },
    rightAxisOption(options) {
      if (
        options.majorLen == void 0 ||
        options.minorLen == void 0 ||
        options.majorNum == void 0 ||
        options.minorNum == void 0 ||
        !options.drawSize
      ) {
        return;
      }

      if (options != oldProps?.rightAxisOption) {
        comp.setRightAxisOption(options);
      }
    },
    rightAxisData(data) {
      if (data !== oldProps?.rightAxisData) {
        data = data.map((item) => ({
          ...item,
          color: item.color === void 0 ? CHART_COLOR_USE_THEME : colorTransform(item.color),
        }));
        comp.setRightAxisData(data);
      }
    },
    topAxisOption(options) {
      if (
        options.majorLen == void 0 ||
        options.minorLen == void 0 ||
        options.majorNum == void 0 ||
        options.minorNum == void 0 ||
        !options.drawSize
      ) {
        return;
      }

      if (options != oldProps?.topAxisOption) {
        comp.setTopAxisOption(options);
      }
    },
    topAxisData(data) {
      if (data !== oldProps?.topAxisData) {
        data = data.map((item) => ({
          ...item,
          color: item.color === void 0 ? CHART_COLOR_USE_THEME : colorTransform(item.color),
        }));
        comp.setTopAxisData(data);
      }
    },
  };
}
