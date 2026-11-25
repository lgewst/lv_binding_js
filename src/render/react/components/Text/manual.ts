// 규칙으로 쓸 수 없어 수작업으로 남긴 세터. 생성된 comp.ts 가 끼워 쓴다.
// 근거는 명세의 해당 prop 에 있다.

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    children(str) {
      const type = typeof str;
      if ((type == "string" || type == "number") && oldProps.children !== str) {
        comp.setText(String(str));
      } else if (Array.isArray(str)) {
        const isStringArr = str.every(
          (item) => typeof item === "string" || typeof item === "number",
        );
        if (isStringArr) {
          comp.setText(str.join(""));
        }
      }
    },
  };
}
