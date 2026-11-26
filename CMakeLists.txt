cmake_minimum_required(VERSION 3.16)

project(lvgljs LANGUAGES C CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(LV_CONF_PATH ${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h CACHE INTERNAL "LV_CONF_PATH")

set(BUILD_NATIVE OFF CACHE BOOL "Build wasm3 with native support")
set(BUILD_LVGL_SIMULATOR OFF CACHE BOOL "Build as lvgl simulator")
option(USE_GENERATED_SWITCH_WRAPPER "Build the generated Switch JS/C++ wrapper" OFF)
set(GENERATED_CPP_WIDGETS "" CACHE STRING "Semicolon-separated generated C++ wrapper widgets")
# Every widget the spec marks generate.nativeClass. Set to "" to build the
# handwritten components instead; they stay in the tree as the comparison
# baseline. See autogen/README.md
set(GENERATED_CPP_COMPONENTS
    "Switch;Arc;Chart;Checkbox;Slider;Dropdownlist;Textarea;Roller;Keyboard;ProgressBar;Calendar;Line;Button;GIF;Image;Mask;Tabs;Text;View"
    CACHE STRING "Semicolon-separated generated C++ widget implementations")

find_path(LVGL_PATH lvgl.h PATHS ${CMAKE_CURRENT_SOURCE_DIR}/deps PATH_SUFFIXES lvgl)

if (MSVC)
    set(CMAKE_CXX_STANDARD 23)
else()
    set(CMAKE_CXX_STANDARD 14)
endif()

add_executable(lvgljs
    src/engine/engine.cpp
    src/engine/hal/framebuffer32_to_rgba.c
    src/engine/hal/screenshot.cpp
    src/render/native/core/style/style.cpp
    src/render/native/core/style/font/font.cpp
    src/render/native/core/event/value_change/value_change.cpp
    src/render/native/core/event/normal/normal.cpp
    src/render/native/core/event/select/select.cpp
    src/render/native/core/event/click/click.cpp
    src/render/native/core/refresh/refresh.cpp
    src/render/native/core/lv_conf/lv_conf.cpp
    src/render/native/core/lv_conf/lv_anim_path.cpp
    src/render/native/core/lv_conf/lv_style_prop_extend.cpp
    src/render/native/core/utils/utils.cpp
    src/render/native/core/theme/theme.cpp
    src/render/native/core/dimensions/dimensions.cpp
    src/render/native/core/basic/comp.cpp
    src/render/native/core/event/event.cpp
    src/render/native/core/img/png/lodepng.cpp
    src/render/native/core/img/png/png.cpp
    src/render/native/core/img/gif/gif.cpp
    src/render/native/core/img/img.cpp
    src/render/native/core/utils/utils.hpp
    src/render/native/core/animate/animate.cpp
    src/render/native/components/arc/arc.cpp
    src/render/native/components/arc/arc_wrap.cpp
    src/render/native/components/mask/mask.cpp
    src/render/native/components/mask/mask_wrap.cpp
    src/render/native/components/gif/gif.cpp
    src/render/native/components/gif/gif_wrap.cpp
    src/render/native/components/chart/chart.cpp
    src/render/native/components/chart/chart_wrap.cpp
    src/render/native/components/tabview/tabview.cpp
    src/render/native/components/tabview/tabview_wrap.cpp
    src/render/native/components/calendar/calendar.cpp
    src/render/native/components/calendar/calendar_wrap.cpp
    src/render/native/components/line/line.cpp
    src/render/native/components/line/line_wrap.cpp
    src/render/native/components/roller/roller.cpp
    src/render/native/components/roller/roller_wrap.cpp
    src/render/native/components/progressbar/progressbar.cpp
    src/render/native/components/progressbar/progressbar_wrap.cpp
    src/render/native/components/dropdownlist/dropdownlist.cpp
    src/render/native/components/dropdownlist/dropdownlist_wrap.cpp
    src/render/native/components/checkbox/checkbox.cpp
    src/render/native/components/checkbox/checkbox_wrap.cpp
    src/render/native/components/keyboard/keyboard.cpp
    src/render/native/components/keyboard/keyboard_wrap.cpp
    src/render/native/components/textarea/textarea.cpp
    src/render/native/components/textarea/textarea_wrap.cpp
    src/render/native/components/switch/switch.cpp
    src/render/native/components/switch/switch_wrap.cpp
    src/render/native/components/slider/slider.cpp
    src/render/native/components/slider/slider_wrap.cpp
    # src/render/native/components/image/lodepng.cpp
    src/render/native/components/button/button.cpp
    src/render/native/components/button/button_wrap.cpp
    src/render/native/components/image/image.cpp
    src/render/native/components/image/image_wrap.cpp
    src/render/native/components/text/text.cpp
    src/render/native/components/text/text_wrap.cpp
    src/render/native/components/view/view.cpp
    src/render/native/components/view/view_wrap.cpp
    src/render/native/components/window/window.cpp
    # src/render/native/components/window/window_wrap.cpp
    src/render/native/components/component.cpp
    src/render/native/bootstrap/render_bootstrap.cpp
)

# Replace only selected widgets with generated code. Use handwritten code by default.
set(_generated_cpp_widgets ${GENERATED_CPP_WIDGETS})
set(_generated_cpp_components ${GENERATED_CPP_COMPONENTS})
list(REMOVE_DUPLICATES _generated_cpp_components)
list(APPEND _generated_cpp_widgets ${_generated_cpp_components})
if(USE_GENERATED_SWITCH_WRAPPER)
    list(APPEND _generated_cpp_widgets Switch)
endif()
list(REMOVE_DUPLICATES _generated_cpp_widgets)
get_target_property(_native_sources lvgljs SOURCES)
set(_generated_cpp_owners "")
if(_generated_cpp_widgets)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    file(GLOB _component_feature_templates CONFIGURE_DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/features/*.in")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/data/widgets_manifest.json"
        "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/autogen/component_cpp_emitter.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/autogen/component_cpp_rules.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/autogen/widget_cpp_emitter.py")
endif()
set(_generated_component_outputs "")
foreach(_widget IN LISTS _generated_cpp_components)
    # Check generated headers against wrapper calls before resolving paths.
    execute_process(
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
            --widget "${_widget}" --target all --describe
        RESULT_VARIABLE _component_result OUTPUT_VARIABLE _component_json ERROR_VARIABLE _component_error
        OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT _component_result EQUAL 0)
        message(FATAL_ERROR "Cannot generate component ${_widget}: ${_component_error}")
    endif()
    string(JSON _component_source GET "${_component_json}" componentSource)
    string(JSON _component_header GET "${_component_json}" componentHeader)
    string(JSON _component_define GET "${_component_json}" headerDefine)
    string(JSON _component_dir GET "${_component_json}" nativeDir)
    if(_component_source IN_LIST _generated_component_outputs)
        continue()
    endif()
    set(_manual_component "src/render/native/components/${_component_dir}/${_component_dir}.cpp")
    list(FIND _native_sources "${_manual_component}" _component_index)
    if(_component_index EQUAL -1)
        message(FATAL_ERROR "No compiled handwritten component to replace: ${_widget}")
    endif()
    list(REMOVE_AT _native_sources ${_component_index})
    add_custom_command(
        OUTPUT "${_component_source}" "${_component_header}"
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
            --widget "${_widget}" --target component
        COMMAND "${CMAKE_COMMAND}" -E touch "${_component_source}" "${_component_header}"
        DEPENDS
            "${CMAKE_CURRENT_SOURCE_DIR}/scripts/data/widgets_manifest.json"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/widget_cpp_emitter.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/component_cpp_emitter.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/component_cpp_rules.py"
            ${_component_feature_templates}
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/component.cpp.in"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/component.hpp.in"
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        COMMENT "Generating ${_widget} C++ implementation and header"
        VERBATIM)
    list(APPEND _generated_component_outputs "${_component_source}" "${_component_header}")
    list(APPEND _native_sources "${_component_source}")
    target_compile_definitions(lvgljs PRIVATE "${_component_define}=1")
endforeach()
if(_generated_component_outputs)
    # Generate headers before compilation and include the flat components directory.
    add_custom_target(generate_cpp_components DEPENDS ${_generated_component_outputs})
    add_dependencies(lvgljs generate_cpp_components)
    target_include_directories(lvgljs BEFORE PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/autogen/generated")
endif()
foreach(_widget IN LISTS _generated_cpp_widgets)
    # Use native paths from the manifest: Tabs uses tabview, and Input shares Textarea.
    set(_wrapper_component_args "")
    if(_widget IN_LIST _generated_cpp_components)
        list(APPEND _wrapper_component_args --component-header)
    endif()
    execute_process(
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
            --widget "${_widget}" ${_wrapper_component_args} --describe
        RESULT_VARIABLE _describe_result OUTPUT_VARIABLE _describe_json ERROR_VARIABLE _describe_error
        OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT _describe_result EQUAL 0)
        message(FATAL_ERROR "Cannot generate ${_widget}: ${_describe_error}")
    endif()
    string(JSON _owner GET "${_describe_json}" owner)
    if(_owner IN_LIST _generated_cpp_components)
        set(_wrapper_component_args --component-header)
    endif()
    string(JSON _source_name GET "${_describe_json}" nativeDir)
    string(JSON _output GET "${_describe_json}" output)
    if(_owner IN_LIST _generated_cpp_owners)
        continue()
    endif()
    list(APPEND _generated_cpp_owners "${_owner}")
    set(_manual "src/render/native/components/${_source_name}/${_source_name}_wrap.cpp")
    list(FIND _native_sources "${_manual}" _manual_index)
    if(_manual_index EQUAL -1)
        message(FATAL_ERROR "No compiled handwritten wrapper to replace: ${_widget} (${_manual})")
    endif()
    list(REMOVE_AT _native_sources ${_manual_index})
    add_custom_command(
        OUTPUT "${_output}"
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
            --widget "${_owner}" ${_wrapper_component_args}
        COMMAND "${CMAKE_COMMAND}" -E touch "${_output}"
        DEPENDS
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/cpp_emitter.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/component_cpp_emitter.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/component_cpp_rules.py"
            ${_component_feature_templates}
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/component.cpp.in"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/component.hpp.in"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/widget_cpp_emitter.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/widget_wrap.cpp.in"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/value_helpers.cpp.in"
            "${CMAKE_CURRENT_SOURCE_DIR}/autogen/templates/axis_helpers.cpp.in"
            "${CMAKE_CURRENT_SOURCE_DIR}/scripts/data/widgets_manifest.json"
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        COMMENT "Generating ${_widget} JS/C++ wrapper"
        VERBATIM
    )
    list(APPEND _native_sources "${_output}")
endforeach()
set_property(TARGET lvgljs PROPERTY SOURCES "${_native_sources}")

if(BUILD_LVGL_SIMULATOR)
    if (MSVC)
        add_compile_options("/utf-8")
        target_compile_definitions(lvgljs PRIVATE WIN32_LEAN_AND_MEAN)
    else()
        add_compile_options(-Wno-error=unused-but-set-variable)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O0 -Wall -g -ggdb")
    endif()
    set(BUILD_WITH_MIMALLOC OFF) # TODO: SDL and mimalloc don't play well together
    add_definitions(-DIS_SIM)
    # LVGL v9 ships its own SDL drivers, so the lvgl target needs the SDL2
    # headers too. Find SDL2 before adding the lvgl subdirectory.
    find_package(SDL2 REQUIRED)
    target_sources(lvgljs PRIVATE
        src/engine/hal/simulator/simulator.cpp
        src/engine/hal/simulator/mouse_cursor_icon.c
    )
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -Wall")
    add_definitions(-DIS_DEVICE)
    target_sources(lvgljs PRIVATE
        src/engine/hal/device/device.cpp
    )
endif()

add_subdirectory(deps/txiki EXCLUDE_FROM_ALL)
add_subdirectory(deps/lvgl EXCLUDE_FROM_ALL)

if(BUILD_LVGL_SIMULATOR)
    target_include_directories(lvgl PRIVATE ${SDL2_INCLUDE_DIRS})
endif()

target_include_directories(lvgljs PUBLIC
    ${LVGL_PATH}
    src/
    src/engine
    src/engine/hal
    src/engine/hal/device
    src/render
    src/render/native
    src/render/native/bootstrap
    src/render/native/components
    src/render/native/core
)

target_link_libraries(lvgljs PUBLIC
    tjs
    lvgl
)

if(BUILD_LVGL_SIMULATOR)
    target_link_libraries(lvgljs PUBLIC ${SDL2_LIBRARIES})
endif()
