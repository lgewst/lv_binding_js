// Hand-written setters for props no rule can express. The generated comp.ts
// splices these into its setter table; the spec records why each one is here.
import { BUILT_IN_SYMBOL } from "../../core/style/symbol";
import { isValidUrl } from "../../utils/helpers";
import { fetchAssetBinary, loadLocalAsset } from "../../utils/assets";

function applyGIF(comp, buffer?: ArrayBuffer, paused?: boolean) {
  if (buffer != null) {
    comp.setGIFBinary(buffer);
  }
  if (paused) {
    comp.pause();
  } else if (paused === false) {
    comp.resume();
  }
}

export function manualSetters({ comp, newProps, oldProps }) {
  return {
    src(url) {
      if (url && url !== oldProps.src) {
        if (BUILT_IN_SYMBOL[url]) {
          comp.setSymbol(BUILT_IN_SYMBOL[url]);
          return;
        }
        if (!isValidUrl(url)) {
          loadLocalAsset(url, "setGIF error", (buffer) =>
            applyGIF(comp, buffer, newProps.paused));
        } else {
          fetchAssetBinary(url)
            .then((buffer) => applyGIF(comp, buffer, newProps.paused))
            .catch(console.warn);
        }
      }
    },
    paused(shouldPause) {
      applyGIF(comp, undefined, shouldPause);
    },
  };
}
