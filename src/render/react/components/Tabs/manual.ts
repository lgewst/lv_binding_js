// 규칙으로 표현되지 않아 수작업으로 남긴 부분.
// 생성된 comp.ts 가 이 파일을 끼워 쓴다. 근거는 명세에 있다.

// 자식은 추가되는 순서대로 탭 하나씩에 배정된다. 순서가 상태라 규칙으로 쓸 수 없다.
export const manualChildren = {
  insertBefore(child, beforeChild) {},
  appendInitialChild(child) {
    this.appendChild(child);
  },
  appendChild(child) {
    this.setTab(this.tabs[this.currentAppendIndex] || "", child);
    this.currentAppendIndex++;
  },
};
