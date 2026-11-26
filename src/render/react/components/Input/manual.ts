// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    mode(mode) {
      if (mode == oldProps.mode) return;
      if (mode === "password") {
        comp.setPasswordMode(true);
      } else if (oldProps.mode === "password") {
        comp.setPasswordMode(false);
      }
    },
  };
}
