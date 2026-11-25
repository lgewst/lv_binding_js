#pragma once
#include <memory>

#include <lvgl.h>
#include <quickjs.h>

// 이 바인딩은 LVGL v9 API 로 작성되어 있다. 메이저 버전이 올라가면 컴파일 에러가
// 쏟아지기 전에 여기서 멈춘다.
static_assert(LVGL_VERSION_MAJOR == 9, "lvgljs는 LVGL 9 기준입니다. 상위 버전은 API 이름 확인이 필요합니다.");

extern "C" {
#include "private.h"
};
