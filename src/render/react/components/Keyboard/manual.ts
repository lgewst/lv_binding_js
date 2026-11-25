// 규칙으로 쓸 수 없어 수작업으로 남긴 세터. 생성된 comp.ts 가 끼워 쓴다.
// 근거는 명세의 해당 prop 에 있다.

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    textarea(textarea) {
      if (textarea?.uid !== oldProps.textarea?.uid) {
        comp.setTextarea(textarea);
      }
    },
  };
}
