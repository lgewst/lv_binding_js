#pragma once
#include <memory>

#include <lvgl.h>
#include <quickjs.h>

// Written against the LVGL v9 API. Stop on a major version bump instead of
// burying the reader in a few hundred unresolved identifiers.
static_assert(LVGL_VERSION_MAJOR == 9, "lvgljs는 LVGL 9 기준입니다. 상위 버전은 API 이름 확인이 필요합니다.");

extern "C" {
#include "private.h"
};
