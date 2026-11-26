// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.
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
