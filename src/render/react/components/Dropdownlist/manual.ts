// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    arrow(arrow) {
      if (arrow != oldProps.arrow && typeof arrow === "number") {
        comp.setArrowDir(arrow);
      }
    },
  };
}
