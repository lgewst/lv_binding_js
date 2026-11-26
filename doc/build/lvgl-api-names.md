# LVGL API Names

lvgljs targets the **LVGL v9 API**. This page explains why the build refuses
LVGL's older names, and what to do when one appears.

## The compatibility headers

`lvgl.h` ends with a block of renaming headers:

```c
/* Define LV_DISABLE_API_MAPPING using a compiler option
 * to make sure your application is not using deprecated names */
#ifndef LV_DISABLE_API_MAPPING
#include "src/lv_api_map_v8.h"
#include "src/lv_api_map_v9_0.h"
...
#include "src/lv_api_map_v9_4.h"
#endif
```

Each is a list of `#define`s and typedefs mapping a name LVGL used to have onto
the one it has now - `lv_obj_clear_flag` to `lv_obj_remove_flag`,
`lv_coord_t` to `int32_t`, and so on. They exist so that code written against
an older LVGL keeps compiling, and LVGL's own comment says what they are for:
they are there to be removed. Code that depends on them builds today and stops
building the moment those headers go.

Using them is therefore invisible technical debt: nothing fails, nothing warns,
and the cost arrives all at once at the next major version bump.

## Two guards

**`scripts/check-lvgl-api-names.py`** reads the `lv_api_map_v*.h` files in the
LVGL submodule, collects every name they define, and fails if any appears in
`src/`, `autogen/` or `scripts/data/widgets_manifest.json`. It needs no build
and runs in under a second. Because the list comes from the submodule, bumping
LVGL also updates what the check looks for.

```sh
python3 scripts/check-lvgl-api-names.py
```

The failure output names the file, line and symbol. The replacement is usually
the right-hand side of that symbol's `#define` in the header the message names.
A few entries are `static inline` wrappers rather than renames - LVGL has no
single call that replaces them, so their bodies have to be inlined at the call
site. `lv_obj_move_foreground` and `lv_obj_move_background` are the two this
repository had.

**A build with the mapping switched off** is the stronger check, and catches
what a textual scan cannot - a deprecated name reached through a macro, or
through another header:

```sh
cmake -B build-strict -DBUILD_LVGL_SIMULATOR=OFF \
  -DCMAKE_C_FLAGS=-DLV_DISABLE_API_MAPPING \
  -DCMAKE_CXX_FLAGS=-DLV_DISABLE_API_MAPPING
cmake --build build-strict -j
```

Both run in the `Linux device` CI job.

## Version assertion

`src/render/native/lv_bindings_js.h` asserts the major version:

```c
static_assert(LVGL_VERSION_MAJOR == 9, ...);
```

A submodule bump to v10 then stops with one clear message instead of a few
hundred unresolved identifiers.

## Code generation

The C++ emitters write LVGL calls from two places, and both are covered by the
check above:

- `scripts/data/widgets_manifest.json` - `lvglCreate` and the `function` field
  of each entry under `calls` and `afterCreate` hold LVGL function names
  literally. Write the v9 name.
- `autogen/component_cpp_emitter.py` and `autogen/templates/` - names that are
  not in the spec, such as the flag and state calls made in a constructor.
  `FLAG_OPS` maps the spec's `operation` values (`add`, `clear`) onto the whole
  function name, so the spec keeps its own vocabulary while the generated code
  uses current names. Write the name out rather than assembling it from parts:
  a name built as `"lv_obj_" + operation + "_flag"` never appears as a token in
  any file, so neither guard can see it.
