#version 330 core
layout(location = 0) in vec3 vertices;
out vec2 uv;
void main() {
  gl_Position = vec4(vertices.xy, 0.0, 1.0);
  uv = (vertices.xy + vec2(1.0, 1.0)) * vec2(0.5, 0.5);
}
