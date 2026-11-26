import { GetBridge, LvgljsTheme } from "../bridge";

const bridge = GetBridge();
const nativeTheme = bridge.NativeRender.theme;

type ThemeOptions = Parameters<LvgljsTheme["setTheme"]>[0];

export const Theme = {
  setTheme({ primaryColor, secondPrimaryValue, fontSize }: ThemeOptions) {
    nativeTheme.setTheme({
      primaryColor,
      secondPrimaryValue,
      fontSize,
    });
  },
  resetTheme() {
    nativeTheme.resetTheme();
  },
};
