// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.
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
