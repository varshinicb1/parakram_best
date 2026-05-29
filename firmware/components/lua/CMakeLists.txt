file(GLOB LUA_SRCS "src/*.c")
idf_component_register(
    SRCS ${LUA_SRCS}
    INCLUDE_DIRS "src"
)
