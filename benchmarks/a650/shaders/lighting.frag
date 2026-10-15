#version 450
layout(location=0) in vec3 normal;
layout(location=1) in vec3 lightDir;
layout(location=0) out vec4 color;
void main() {
 vec3 n = normalize(normal);
 vec3 l = normalize(lightDir);
 float diffuse = max(dot(n,l), 0.0);
 float specular = pow(max(dot(reflect(-l,n), vec3(0,0,1)), 0.0), 24.0);
 color = vec4(vec3(0.06) + vec3(0.75) * diffuse + vec3(0.18) * specular, 1.0);
}
