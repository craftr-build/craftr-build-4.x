# type: ignore

project.apply('cxx')

lib = project.c_library('array')
lib.public_include_paths = [project.file('src/lib')]
lib.sources = project.glob('src/lib/*.c')

app = project.cpp_application('main')
app.sources = project.glob('src/*.cpp')
app.dependencies.append(lib)

run = project.run()
run.dependencies.append(app)
