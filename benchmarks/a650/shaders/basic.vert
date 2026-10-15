#version 450
layout(location=0) in vec3 inPosition;
layout(location=1) in vec2 inUV;
layout(location=0) out vec2 uv;
layout(push_constant) uniform Push { mat4 mvp; } pc;
void main() { uv = inUV; gl_Position = pc.mvp * vec4(inPosition, 1.0); }
