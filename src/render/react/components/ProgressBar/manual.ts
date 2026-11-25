// 규칙으로 쓸 수 없어 수작업으로 남긴 세터. 생성된 comp.ts 가 끼워 쓴다.
// 근거는 명세의 해당 prop 에 있다.
import { STYLE_TYPE, setStyle } from "../config";

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    style(styleSheet) {
      if (newProps.animationTime) {
        styleSheet["style-transition-time"] = newProps.animationTime;
      }
      setStyle({
        comp,
        styleSheet,
        compName: "ProgressBar",
        styleType: STYLE_TYPE.PART_MAIN,
        oldStyleSheet: oldProps.style,
      });
    },
  };
}
