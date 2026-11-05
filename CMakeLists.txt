# Keep legacy hosts and high-resolution hosts at the same scroll speed.
if(CONFIG_ZMK_POINTING_SMOOTH_SCROLLING AND
   (NOT CONFIG_ZMK_SPLIT OR CONFIG_ZMK_SPLIT_ROLE_CENTRAL))
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  set(scroll_compat_dir ${CMAKE_CURRENT_BINARY_DIR}/scroll-compat)
  execute_process(
    COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_LIST_DIR}/scripts/apply-scroll-compat.py
            ${APPLICATION_SOURCE_DIR}
            ${scroll_compat_dir}
    RESULT_VARIABLE scroll_patch_result
  )
  if(NOT scroll_patch_result EQUAL 0)
    message(FATAL_ERROR "Could not apply the pinned Velvet scroll compatibility patch")
  endif()
  # Replace these sources only in this build. Leave the west checkout untouched,
  # so peripheral builds and configurations without smooth scrolling reuse it.
  foreach(source src/hid.c src/pointing/input_listener.c src/pointing/resolution_multipliers.c)
    set_source_files_properties(${APPLICATION_SOURCE_DIR}/${source}
      TARGET_DIRECTORY app PROPERTIES HEADER_FILE_ONLY TRUE)
    target_sources(app PRIVATE ${scroll_compat_dir}/${source})
  endforeach()
  target_include_directories(app PRIVATE src)
  target_sources(app PRIVATE src/scroll_resolution.c)
endif()
