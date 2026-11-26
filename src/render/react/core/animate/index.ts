import { GetBridge, LvgljsNativeAnimate, LvgljsNativeAnimateStartOptions } from "../bridge";
import { ANIM_PATH } from "../lv_types";

const bridge = GetBridge();
const NativeAnimate = bridge.NativeRender.Animate;

export const EAnimateEasingFunc = ANIM_PATH;

/** A key of ANIM_PATH, or a raw lv_anim path value. */
export type AnimateEasing = keyof typeof ANIM_PATH | number;

/**
 * Receives the animated value. animate.cpp passes one number for the exec
 * callback and none for start and ready, so the parameter is optional.
 */
export type AnimateCallback = (...args: number[]) => void;

export interface AnimateParams {
  duration?: number;
  startValue?: number;
  endValue?: number;
  delay?: number;
  easing?: AnimateEasing;
  execCallback?: AnimateCallback;
  instanceId?: number | string;
  useNative?: boolean;
  playBackDelay?: number;
  playBackTime?: number;
  repeatDelay?: number;
  repeatCount?: number;
  startCallback?: AnimateCallback;
  readyCallback?: AnimateCallback;
}

function resolveEasing(easing: AnimateEasing | undefined): number {
  if (typeof easing === "number") {
    return easing;
  }
  if (typeof easing === "string") {
    return ANIM_PATH[easing] ?? ANIM_PATH.linear;
  }
  return ANIM_PATH.linear;
}

let uid = 0;
const callbackObj: Record<number, AnimateCallback> = {};
const animateInsObj: Record<number, AnimateBase> = {};

globalThis.ANIMIATE_CALLBACK = function (cbUid: number, ...args: number[]) {
  if (typeof callbackObj[cbUid] === "function") {
    try {
      callbackObj[cbUid].call(null, ...args);
    } catch (e) {
      console.log(e);
    }
  }
};

class AnimateBase extends NativeAnimate {
  duration?: number;
  startValue?: number;
  endValue?: number;
  delay?: number;
  easing?: AnimateEasing;
  execCallback?: AnimateCallback;
  instanceId?: number | string;
  useNative: boolean;
  playBackDelay?: number;
  playBackTime?: number;
  repeatDelay?: number;
  repeatCount?: number;
  startCallback?: AnimateCallback;
  readyCallback?: AnimateCallback;
  uid?: number;
  execUid?: number;
  startCbUid?: number;
  readyCbUid?: number;

  constructor({
    duration,
    startValue,
    endValue,
    delay,
    easing,
    execCallback,
    instanceId,
    useNative = false,
    playBackDelay,
    playBackTime,
    repeatDelay,
    repeatCount,
    startCallback,
    readyCallback,
  }: AnimateParams) {
    super();
    this.duration = duration;
    this.startValue = startValue;
    this.endValue = endValue;
    this.delay = delay;
    this.easing = easing;
    this.execCallback = execCallback;
    this.instanceId = instanceId;
    this.useNative = useNative;
    this.playBackDelay = playBackDelay;
    this.playBackTime = playBackTime;
    this.repeatDelay = repeatDelay;
    this.repeatCount = repeatCount;
    this.startCallback = startCallback;
    this.readyCallback = readyCallback;
  }

  start() {
    const {
      duration,
      startValue,
      endValue,
      delay,
      easing,
      execCallback,
      instanceId,
      useNative,
      playBackDelay,
      playBackTime,
      repeatDelay,
      repeatCount = 0,
      startCallback,
      readyCallback,
    } = this;
    if (
      duration == void 0 ||
      startValue == void 0 ||
      endValue == void 0 ||
      !execCallback
    )
      return;
    if (!useNative && typeof execCallback === "function") {
      callbackObj[++uid] = execCallback;
      this.execUid = uid;
    }
    if (typeof startCallback === "function") {
      callbackObj[++uid] = startCallback;
      this.startCbUid = uid;
    }
    if (typeof readyCallback === "function") {
      callbackObj[++uid] = readyCallback;
      this.readyCbUid = uid;
    }
    animateInsObj[++uid] = this;
    this.uid = uid;
    const options: LvgljsNativeAnimateStartOptions = {
      duration,
      startValue,
      endValue,
      easing: resolveEasing(easing),
      instanceId,
      useNative,
      delay,
      playBackDelay,
      playBackTime,
      repeatDelay,
      repeatCount: !isFinite(repeatCount) ? 0xffff : repeatCount,
      uid: this.uid,
      execUid: this.execUid,
      startCbUid: this.startCbUid,
      readyCbUid: this.readyCbUid,
    };
    super.start(options);
  }

  release() {
    if (this.uid !== undefined) {
      delete animateInsObj[this.uid];
    }
  }
}

function createTimingAnimate(params: AnimateParams): AnimateBase {
  return new AnimateBase(params);
}

class ParallelAnimate {
  animates: AnimateBase[];

  constructor(animates: AnimateBase[]) {
    this.animates = animates;
  }

  start() {
    this.animates.forEach((animate) => {
      if (animate instanceof AnimateBase) {
        animate?.start();
      }
    });
  }
}

function createParallelAnimate(animates: Iterable<AnimateBase>): ParallelAnimate {
  return new ParallelAnimate(Array.from(animates));
}

export const Animate = {
  timing: createTimingAnimate,
  parallel: createParallelAnimate,
};
