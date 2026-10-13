"""Run Mesa's actual suballocator with a fake BO backend, without a GPU."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesa', type=Path, required=True)
    parser.add_argument('--expected-pipeline-kib', type=int, required=True)
    args = parser.parse_args()
    device = (args.mesa / 'src/freedreno/vulkan/tu_device.cc').read_text()
    match = re.search(r'&device->pipeline_suballoc, device,\s*(.*?),\s*static_cast', device, re.S)
    assert match
    capacity_expression = match[1]
    info = (args.mesa / 'src/freedreno/common/freedreno_dev_info.h').read_text()
    gpu_id_function = info[info.index('fd_dev_gpu_id('):info.index('\n}', info.index('fd_dev_gpu_id(')) + 2]
    gpu_id_function = 'static inline uint32_t\n' + gpu_id_function
    assert re.search(r'&device->kgsl_profiling_suballoc, device,\s*128 \* 1024,', device)
    source = (args.mesa / 'src/freedreno/vulkan/tu_suballoc.cc').read_text()
    source = source.replace('#include "tu_suballoc.h"', '')
    prelude = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
using VkResult = int;
constexpr int VK_SUCCESS = 0, VK_ERROR_OUT_OF_HOST_MEMORY = -1, VK_ERROR_OUT_OF_DEVICE_MEMORY = -2;
enum tu_bo_alloc_flags { FLAGS = 0 };
struct fd_dev_id { uint32_t gpu_id; uint64_t chip_id; };
GPU_ID_FUNCTION
struct PhysicalDevice { fd_dev_id dev_id; };
uint32_t pipeline_capacity(uint32_t gpu_id, uint64_t chip_id = 0) {
  PhysicalDevice physical{{gpu_id, chip_id}};
  auto* physical_device = &physical;
  return PIPELINE_CAPACITY;
}
struct tu_device { unsigned calls = 0; uint64_t bytes = 0, live = 0; bool fail_alloc = false, fail_map = false; };
struct tu_bo { uint32_t size; uint64_t iova; int refcnt = 1; void* map; };
struct tu_suballocator { tu_device* dev; uint32_t default_size; tu_bo_alloc_flags flags; tu_bo* bo; tu_bo* cached_bo; const char* name; uint32_t next_offset; };
struct tu_suballoc_bo { tu_bo* bo = nullptr; uint64_t iova = 0; uint32_t size = 0; };
uint32_t align(uint32_t n, uint32_t a) { return (n + a - 1) & ~(a - 1); }
#define MAX2(a,b) std::max(a,b)
int p_atomic_read(int* value) { return *value; }
tu_bo* tu_bo_get_ref(tu_bo* bo) { ++bo->refcnt; return bo; }
void tu_bo_finish(tu_device* dev, tu_bo* bo) {
  if (--bo->refcnt == 0) { dev->live -= bo->size; delete[] static_cast<char*>(bo->map); delete bo; }
}
VkResult tu_bo_init_new(tu_device* dev, void*, tu_bo** result, uint32_t size, tu_bo_alloc_flags, const char*) {
  ++dev->calls;
  if (dev->fail_alloc) return VK_ERROR_OUT_OF_DEVICE_MEMORY;
  dev->bytes += size; dev->live += size;
  *result = new tu_bo{size, uint64_t(dev->calls) << 32, 1, new char[size]};
  return VK_SUCCESS;
}
VkResult tu_bo_map(tu_device* dev, tu_bo*, void*) { return dev->fail_map ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_SUCCESS; }
'''
    checks = r'''
unsigned burst(unsigned capacity, unsigned expected) {
  tu_device dev;
  tu_suballocator allocator{};
  tu_bo_suballocator_init(&allocator, &dev, capacity, FLAGS, "pipeline");
  std::vector<tu_suballoc_bo> slices(64);
  for (unsigned i = 0; i < slices.size(); ++i) {
    assert(tu_suballoc_bo_alloc(&slices[i], &allocator, 16384, 64) == VK_SUCCESS);
    assert(slices[i].iova % 64 == 0);
    std::memset(tu_suballoc_bo_map(&slices[i]), i, slices[i].size);
  }
  assert(dev.calls == expected && dev.bytes == 1024 * 1024);
  for (unsigned i = 0; i < slices.size(); ++i) {
    auto data = static_cast<unsigned char*>(tu_suballoc_bo_map(&slices[i]));
    for (unsigned j = 0; j < slices[i].size; ++j) assert(data[j] == i);
    tu_suballoc_bo_free(&allocator, &slices[i]);
  }
  tu_bo_suballocator_finish(&allocator);
  assert(dev.live == 0);
  return dev.calls;
}
void edges(unsigned capacity) {
  tu_device dev;
  tu_suballocator allocator{};
  tu_bo_suballocator_init(&allocator, &dev, capacity, FLAGS, "pipeline");
  tu_suballoc_bo first, second, large;
  assert(tu_suballoc_bo_alloc(&first, &allocator, 13, 64) == VK_SUCCESS);
  assert(tu_suballoc_bo_alloc(&second, &allocator, 7, 64) == VK_SUCCESS);
  assert(second.iova == first.iova + 64);
  std::memset(tu_suballoc_bo_map(&first), 0x11, 13);
  std::memset(tu_suballoc_bo_map(&second), 0x22, 7);
  assert(static_cast<unsigned char*>(tu_suballoc_bo_map(&first))[12] == 0x11);
  assert(tu_suballoc_bo_alloc(&large, &allocator, capacity + 4096, 64) == VK_SUCCESS);
  assert(large.bo->size == capacity + 4096);
  tu_suballoc_bo_free(&allocator, &first);
  tu_suballoc_bo_free(&allocator, &second);
  tu_suballoc_bo_free(&allocator, &large);
  tu_bo_suballocator_finish(&allocator);
  assert(dev.live == 0);
  for (bool map_failure : {false, true}) {
    tu_device failed;
    failed.fail_alloc = !map_failure;
    failed.fail_map = map_failure;
    tu_suballocator alloc{};
    tu_bo_suballocator_init(&alloc, &failed, capacity, FLAGS, "pipeline");
    tu_suballoc_bo slice;
    auto result = tu_suballoc_bo_alloc(&slice, &alloc, 16, 64);
    assert(result == (map_failure ? VK_ERROR_OUT_OF_HOST_MEMORY : VK_ERROR_OUT_OF_DEVICE_MEMORY));
    assert(!slice.bo && !alloc.bo && !failed.live);
    tu_bo_suballocator_finish(&alloc);
  }
}
int main() {
  assert(pipeline_capacity(650) == EXPECTED_PIPELINE * 1024);
  assert(pipeline_capacity(0, 0x06050000) == EXPECTED_PIPELINE * 1024);
  for (unsigned id : {618, 640, 660, 730, 750, 830}) assert(pipeline_capacity(id) == 128 * 1024);
  auto control = burst(128 * 1024, 8);
  auto candidate = burst(512 * 1024, 2);
  edges(128 * 1024); edges(512 * 1024);
  std::cout << "{\"controlBoCalls\":" << control << ",\"candidateBoCalls\":" << candidate
            << ",\"bytesPerArm\":1048576,\"placementAndFailureChecks\":true}\n";
}
'''
    with tempfile.TemporaryDirectory() as directory:
        cpp = Path(directory) / 'suballoc.cpp'
        binary = Path(directory) / 'suballoc'
        cpp.write_text((prelude + source + checks).replace('GPU_ID_FUNCTION', gpu_id_function).replace('PIPELINE_CAPACITY', capacity_expression).replace('EXPECTED_PIPELINE', str(args.expected_pipeline_kib)))
        subprocess.run(['g++', '-std=c++17', '-O2', str(cpp), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        print(json.dumps({'pipelineKiB': args.expected_pipeline_kib, 'checks': json.loads(result.stdout)}))


if __name__ == '__main__':
    main()
