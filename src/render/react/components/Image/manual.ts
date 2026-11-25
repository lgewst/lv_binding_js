// 규칙으로 쓸 수 없어 수작업으로 남긴 세터. 생성된 comp.ts 가 끼워 쓴다.
// 근거는 명세의 해당 prop 에 있다.
import { BUILT_IN_SYMBOL } from "../../core/style/symbol";
import { isValidUrl } from "../../utils/helpers";
import { fetchAssetBinary, loadLocalAsset } from "../../utils/assets";

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    src(url) {
      if (url && url !== oldProps.src) {
        if (BUILT_IN_SYMBOL[url]) {
          comp.setSymbol(BUILT_IN_SYMBOL[url]);
          return;
        }
        if (!isValidUrl(url)) {
          loadLocalAsset(url, "setImage error", (buffer) =>
            comp.setImageBinary(buffer));
        } else {
          fetchAssetBinary(url)
            .then((buffer) => comp.setImageBinary(buffer))
            .catch(console.warn);
        }
      }
    },
  };
}
