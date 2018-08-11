#version 330 core
uniform sampler2D tex;
in vec2 uv;
out vec3 color;
void main() {
  color = texture(tex, uv).xyz;
}
