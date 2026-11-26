// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    textarea(textarea) {
      if (textarea?.uid !== oldProps.textarea?.uid) {
        comp.setTextarea(textarea);
      }
    },
  };
}
