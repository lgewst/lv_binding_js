// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.

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
