#!/bin/bash -e

green='\033[0;32m'
red='\033[0;31m'
nocolor='\033[0m'
deps="git meson ninja patchelf unzip curl flex bison zip glslangValidator ccache"
workdir="$(pwd)/turnip_workdir"
ndkver="android-ndk-r29"
ndk="$workdir/$ndkver/toolchains/llvm/prebuilt/linux-x86_64/bin"
sdkver="34"
mesasrc="https://gitlab.freedesktop.org/mesa/mesa"
srcfolder="mesa"
mesa_commit="${MESA_COMMIT:-}"
perf_profile="${PERF_PROFILE:-generic}"
program_reference=0
pipeline_512k=0
pipeline_256k=0
memory_audit=0
ff7r_budget=0
ff7r_pipeline=0
pipeline_a650_kib=128
sysmem_screen=0
render_mode_a650="auto"
platform_sdk="36"
min_api="28"
metadata_vulkan="1.3.0"
case "$perf_profile" in
	generic)
		cpu_tune_flags=""
		perf_description="A6xx/A7xx generic AArch64 performance build"
		;;
	sd865-cortex-a77)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="Snapdragon 865 / Adreno 650 Cortex-A77-tuned performance build"
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-program-reference)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 candidate: A77 tuning with borrowed graphics program state"
		program_reference=1
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-memory-audit)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 memory-pressure fix: release KGSL BOs when lazy sparse binding fails"
		memory_audit=1
		mesa_commit="dc671cbf0f76194c72b621205b6cc84e1c914fad"
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-ff7r-budget75-512k)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="FF7R SD865 experimental: 512 KiB pipeline suballocation with conservative 75% available-memory budget reporting"
		ff7r_pipeline=1
		pipeline_a650_kib=512
		ff7r_budget=1
		mesa_commit="dc671cbf0f76194c72b621205b6cc84e1c914fad"
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-pipeline-512k)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 isolated candidate: 512 KiB pipeline backing BOs; owned graphics program state"
		pipeline_512k=1
		pipeline_a650_kib=512
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-pipeline-256k)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 isolated candidate: 256 KiB pipeline backing BOs; owned graphics program state"
		pipeline_256k=1
		pipeline_a650_kib=256
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-sysmem-screen)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 isolated diagnostic: forced SYSMEM rendering; no program-reference or suballocation patch"
		sysmem_screen=1
		render_mode_a650="sysmem"
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-combined-512k)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 combined candidate: borrowed graphics program state and 512 KiB pipeline backing BOs"
		program_reference=1
		pipeline_512k=1
		pipeline_a650_kib=512
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	sd865-combined-sysmem)
		cpu_tune_flags="-mtune=cortex-a77"
		perf_description="SD865 A650 combined diagnostic: borrowed graphics program state, 512 KiB pipeline backing BOs, and forced SYSMEM"
		program_reference=1
		pipeline_512k=1
		pipeline_a650_kib=512
		sysmem_screen=1
		render_mode_a650="sysmem"
		sdkver="29"
		platform_sdk="$sdkver"
		min_api="$sdkver"
		metadata_vulkan="1.3.0"
		;;
	*)
		echo "Unsupported PERF_PROFILE: $perf_profile" >&2
		exit 2
		;;
esac
if [ -n "$mesa_commit" ] && ! [[ "$mesa_commit" =~ ^[0-9a-f]{40}$ ]]; then
	echo "MESA_COMMIT must be a full lowercase commit SHA" >&2
	exit 2
fi

run_all(){
	echo -e "${green}====== Begin building TU Perf ${perf_profile} V${BUILD_VERSION}! ======${nocolor}"
	check_deps
	prepare_workdir
	if [ -n "$mesa_commit" ]; then
		git -C "$workdir/$srcfolder" fetch --depth=1 origin "$mesa_commit"
		git -C "$workdir/$srcfolder" checkout --detach "$mesa_commit"
		test "$(git -C "$workdir/$srcfolder" rev-parse HEAD)" = "$mesa_commit"
	fi
	build_lib_for_android main
}

check_deps(){
	echo "Checking system for required Dependencies ..."
	for deps_chk in $deps; do
		if command -v "$deps_chk" >/dev/null 2>&1 ; then
			echo -e "$green - $deps_chk found $nocolor"
		else
			echo -e "$red - $deps_chk not found, can't continue. $nocolor"
			deps_missing=1
		fi
	done

	if [ "$deps_missing" == "1" ]; then
		echo "Please install missing dependencies" && exit 1
	fi

	PIP_CMD="$(command -v pip || command -v pip3 || true)"
	if [ -z "$PIP_CMD" ]; then
		echo "Missing pip or pip3; cannot install Python Mako dependency" >&2
		exit 1
	fi
	echo "Installing python Mako dependency..."
	"$PIP_CMD" install mako &> /dev/null || true
}

prepare_workdir(){
	echo "Preparing work directory..."
	mkdir -p "$workdir" && cd "$_"

	if [ "${SKIP_SOURCE_DOWNLOAD}" = "1" ]; then
		echo "Skipping NDK + Mesa download (reusing existing source)..."
		if [ -d "$srcfolder/.git" ]; then
			echo "Resetting Mesa source tree..."
			git -C "$srcfolder" checkout .
		fi
		return
	fi

	echo "Downloading android-ndk from google server..."
	curl -sL https://dl.google.com/android/repository/"$ndkver"-linux.zip --output "$ndkver"-linux.zip &> /dev/null

	echo "Extracting android-ndk..."
	unzip -q "$ndkver"-linux.zip &> /dev/null

	echo "Downloading mesa source..."
	git clone $mesasrc --depth=1 -b main $srcfolder
}

build_lib_for_android(){
	cd "$workdir/$srcfolder"
	echo "==== Building Mesa on $1 branch ($perf_description) ===="

	# KGSL fixes every leg ships (patches/common/SOURCE); fails the build if one does not land.
	bash ../../patches/common/apply_common.sh . || { echo -e "${red}patches/common did not apply, aborting!${nocolor}"; exit 1; }
	if [ "$memory_audit" = "1" ]; then
		patch=../../patches/sd865/0005-tu-kgsl-sparse-bind-oom-cleanup.patch
		git apply --check "$patch"
		git apply "$patch"
		grep -q "kgsl_bo_finish(dev, bo);" src/freedreno/vulkan/tu_knl_kgsl.cc
		grep -q "The kernel BO exists now, including on a later mapping failure." src/freedreno/vulkan/tu_knl_kgsl.cc
		telemetry_patch=../../patches/sd865/0006-tu-kgsl-bo-lifecycle-telemetry.patch
		git apply --check "$telemetry_patch"
		git apply "$telemetry_patch"
		grep -q "TU_KGSL_MEM event=alloc" src/freedreno/vulkan/tu_knl_kgsl.cc
		grep -q "TU_KGSL_MEM event=free" src/freedreno/vulkan/tu_knl_kgsl.cc
	fi

	if [ "$program_reference" = "1" ]; then
		# No fuzzy application or silently missing optimization in a named candidate.
		git apply --check ../../patches/sd865/0001-tu-reference-bound-program-state.patch
		git apply ../../patches/sd865/0001-tu-reference-bound-program-state.patch
	fi

	if [ "$pipeline_256k" = "1" ]; then
		git apply --check ../../patches/sd865/0004-tu-a650-pipeline-suballoc-256k.patch
		git apply ../../patches/sd865/0004-tu-a650-pipeline-suballoc-256k.patch
	fi

	if [ "$pipeline_512k" = "1" ]; then
		git apply --check ../../patches/sd865/0002-tu-a650-pipeline-suballoc-512k.patch
		git apply ../../patches/sd865/0002-tu-a650-pipeline-suballoc-512k.patch
	fi

	if [ "$ff7r_pipeline" = "1" ]; then
		# Guarded semantic rewrite avoids brittle hunk context; fail closed on drift.
		python3 - <<'PY'
import re
from pathlib import Path
p = Path("src/freedreno/vulkan/tu_device.cc")
s = p.read_text()
target = "(fd_dev_gpu_id(&physical_device->dev_id) == 650 ? 512 : 128) * 1024"
if target in s:
    raise SystemExit("FF7R 512 KiB pipeline change already present; refusing duplicate application")
pattern = re.compile(r"(tu_bo_suballocator_init\s*\(\s*&device->pipeline_suballoc\s*,\s*device\s*,\s*)128\s*\*\s*1024(\s*,)", re.MULTILINE)
s2, n = pattern.subn(lambda m: m.group(1) + target + m.group(2), s)
if n != 1:
    raise SystemExit(f"Expected exactly one pipeline suballocator size site, found {n}; source unchanged")
p.write_text(s2)
print("Applied guarded FF7R 512 KiB pipeline suballocation change.")
PY
		grep -Fq "(fd_dev_gpu_id(&physical_device->dev_id) == 650 ? 512 : 128) * 1024" src/freedreno/vulkan/tu_device.cc
	fi

	if [ "$ff7r_budget" = "1" ]; then
		# Guarded semantic rewrite: only alter the pinned upstream 90% policy.
		python3 - <<'PY'
import re
from pathlib import Path
p = Path("src/freedreno/vulkan/tu_device.cc")
s = p.read_text()
target = "sys_available * 3 / 4"
if target in s:
    raise SystemExit("FF7R conservative budget change already present; refusing duplicate application")
pattern = re.compile(r"sys_available\s*\*\s*9\s*/\s*10")
s2, n = pattern.subn(target, s)
if n != 1:
    raise SystemExit(f"Expected exactly one upstream 90% budget expression, found {n}; source unchanged")
p.write_text(s2)
print("Applied guarded FF7R 75% available-memory budget change.")
PY
		grep -Fq "sys_available * 3 / 4" src/freedreno/vulkan/tu_device.cc
	fi

	if [ "$sysmem_screen" = "1" ]; then
		git apply --check ../../patches/sd865/0003-tu-a650-sysmem-screen.patch
		git apply ../../patches/sd865/0003-tu-a650-sysmem-screen.patch
	fi

	# NDK r29 compatibility fixes
	sed -i 's/typedef const native_handle_t\* buffer_handle_t;/typedef void\* buffer_handle_t;/g' include/android_stub/cutils/native_handle.h || true
	sed -i 's/, hnd->handle/, (void \*)hnd->handle/g' src/util/u_gralloc/u_gralloc_fallback.c || true
	sed -i -E 's/([a-z_]+)->handle->/((const native_handle_t *)\1->handle)->/g' src/vulkan/runtime/vk_android.c || true

	mkdir -p "$workdir/bin"
	ln -sf "$ndk/clang" "$workdir/bin/cc"
	ln -sf "$ndk/clang++" "$workdir/bin/c++"
	export PATH="$workdir/bin:$ndk:$PATH"
	export CC=clang
	export CXX=clang++
	export AR=llvm-ar
	export RANLIB=llvm-ranlib
	export STRIP=llvm-strip
	export OBJDUMP=llvm-objdump
	export OBJCOPY=llvm-objcopy
	export LDFLAGS="-fuse-ld=lld -flto=thin"
	export CFLAGS="-D__ANDROID__ -O3 -fno-plt $cpu_tune_flags -flto=thin -Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"
	export CXXFLAGS="-D__ANDROID__ -O3 -fno-plt $cpu_tune_flags -flto=thin -Wno-error -Wno-deprecated-declarations -Wno-incompatible-pointer-types-discards-qualifiers -Wno-incompatible-pointer-types"

	GITHASH=$(git rev-parse --short HEAD)

	echo "Generating build files..."
	cat <<EOF >"android-aarch64.txt"
[binaries]
ar = '$ndk/llvm-ar'
c = ['ccache', '$ndk/aarch64-linux-android$sdkver-clang']
cpp = ['ccache', '$ndk/aarch64-linux-android$sdkver-clang++', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
c_ld = '$ndk/ld.lld'
cpp_ld = '$ndk/ld.lld'
strip = '$ndk/llvm-strip'
pkg-config = ['env', 'PKG_CONFIG_LIBDIR=$ndk/pkg-config', '/usr/bin/pkg-config']

[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8'
endian = 'little'
EOF

	cat <<EOF >"native.txt"
[build_machine]
c = ['ccache', 'clang']
cpp = ['ccache', 'clang++']
ar = 'llvm-ar'
strip = 'llvm-strip'
c_ld = 'ld.lld'
cpp_ld = 'ld.lld'
system = 'linux'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
EOF

	meson setup build-android-aarch64 \
		--cross-file "android-aarch64.txt" \
		--native-file "native.txt" \
		--prefix /tmp/turnip-$1 \
		-Dbuildtype=release \
		-Db_ndebug=true \
		-Dstrip=true \
		-Dplatforms=android \
		-Dvideo-codecs= \
		-Dplatform-sdk-version="$platform_sdk" \
		-Dandroid-stub=true \
		-Dandroid-strict=false \
		-Dgallium-drivers= \
		-Dvulkan-drivers=freedreno \
		-Dvulkan-beta=true \
		-Dfreedreno-kmds=kgsl \
		-Degl=disabled \
		-Dandroid-libbacktrace=disabled \
		--reconfigure

	echo "Compiling build files..."
	ninja -C build-android-aarch64 install

	if ! [ -f /tmp/turnip-$1/lib/libvulkan_freedreno.so ]; then
		echo -e "${red}Build failed!${nocolor}" && exit 1
	fi

	echo "Making the archive..."
	cd /tmp/turnip-$1/lib

	_zip_name="mesa-turnip-perf-${perf_profile}-$1.zip"

	cat <<EOF >"meta.json"
{
  "schemaVersion": 1,
  "name": "Banners Turnip Perf ${perf_profile} ${GITHASH}",
  "description": "${perf_description} — Mesa main (git ${GITHASH}). O3 + ThinLTO; ${cpu_tune_flags:-generic ISA tuning}. KGSL.",
  "author": "The412Banner",
  "packageVersion": "1",
  "vendor": "Mesa",
  "driverVersion": "Vulkan ${metadata_vulkan}",
  "minApi": ${min_api},
  "libraryName": "libvulkan_freedreno.so"
}
EOF
	# Keep sufficient provenance to reproduce and compare the exact pair.
	MESA_SOURCE_SHA=$(git -C "$workdir/$srcfolder" rev-parse HEAD)
	DRIVER_SHA=$(sha256sum libvulkan_freedreno.so | cut -d ' ' -f 1)
	PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0001-tu-reference-bound-program-state.patch" | cut -d ' ' -f 1)
	PIPELINE_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0002-tu-a650-pipeline-suballoc-512k.patch" | cut -d ' ' -f 1)
	PIPELINE_256_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0004-tu-a650-pipeline-suballoc-256k.patch" | cut -d ' ' -f 1)
	RENDER_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0003-tu-a650-sysmem-screen.patch" | cut -d ' ' -f 1)
	MEMORY_AUDIT_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0005-tu-kgsl-sparse-bind-oom-cleanup.patch" | cut -d ' ' -f 1)
	MEMORY_TELEMETRY_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0006-tu-kgsl-bo-lifecycle-telemetry.patch" | cut -d ' ' -f 1)
	FF7R_BUDGET_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0007-tu-ff7r-conservative-memory-budget.patch" | cut -d ' ' -f 1)
	FF7R_PIPELINE_PATCH_SHA=$(sha256sum "$workdir/../patches/sd865/0008-tu-ff7r-pipeline-suballoc-512k.patch" | cut -d ' ' -f 1)
	BUILDER_SHA=$(git -C "$workdir/.." rev-parse HEAD)
	# Record only patches actually applied to this profile; source hashes below are
	# retained for reproducibility, but are not a substitute for this applied list.
	APPLIED_PATCHES_JSON='['
	patch_sep=''
	if [ "$memory_audit" = "1" ]; then
		APPLIED_PATCHES_JSON+="\"patches/sd865/0005-tu-kgsl-sparse-bind-oom-cleanup.patch\""
		patch_sep=','
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0006-tu-kgsl-bo-lifecycle-telemetry.patch\""
		patch_sep=','
	fi
	if [ "$program_reference" = "1" ]; then
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0001-tu-reference-bound-program-state.patch\""
		patch_sep=','
	fi
	if [ "$pipeline_256k" = "1" ]; then
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0004-tu-a650-pipeline-suballoc-256k.patch\""
		patch_sep=','
	fi
	if [ "$pipeline_512k" = "1" ]; then
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0002-tu-a650-pipeline-suballoc-512k.patch\""
		patch_sep=','
	fi
	if [ "$ff7r_pipeline" = "1" ]; then
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0008-tu-ff7r-pipeline-suballoc-512k.patch\""
		patch_sep=','
	fi
	if [ "$sysmem_screen" = "1" ]; then
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0003-tu-a650-sysmem-screen.patch\""
		patch_sep=','
	fi
	if [ "$ff7r_budget" = "1" ]; then
		APPLIED_PATCHES_JSON+="${patch_sep}\"patches/sd865/0007-tu-ff7r-conservative-memory-budget.patch\""
	fi
	APPLIED_PATCHES_JSON+=']'
	cat <<EOF >"build-manifest.json"
{
  "mesaCommit": "${MESA_SOURCE_SHA}",
  "profile": "${perf_profile}",
  "appliedPatches": ${APPLIED_PATCHES_JSON},
  "builderCommit": "${BUILDER_SHA}",
  "renderModeA650": "${render_mode_a650}",
  "renderModePatchApplied": ${sysmem_screen},
  "renderModePatchSha256": "${RENDER_PATCH_SHA}",
  "programReference": ${program_reference},
  "memoryAuditPatchApplied": ${memory_audit},
  "memoryAuditPatchSha256": "${MEMORY_AUDIT_PATCH_SHA}",
  "memoryTelemetryPatchApplied": ${memory_audit},
  "memoryTelemetryPatchSha256": "${MEMORY_TELEMETRY_PATCH_SHA}",
  "ff7rConservativeBudgetPatchApplied": ${ff7r_budget},
  "ff7rConservativeBudgetPatchSha256": "${FF7R_BUDGET_PATCH_SHA}",
  "pipelineSuballocA650KiB": ${pipeline_a650_kib},
  "pipelineSuballoc256kPatchApplied": ${pipeline_256k},
  "pipelineSuballoc256kPatchSha256": "${PIPELINE_256_PATCH_SHA}",
  "pipelineSuballocPatchApplied": ${pipeline_512k},
  "pipelineSuballocPatchSha256": "${PIPELINE_PATCH_SHA}",
  "ff7rPipelinePatchApplied": ${ff7r_pipeline},
  "ff7rPipelinePatchSha256": "${FF7R_PIPELINE_PATCH_SHA}",
  "programReferencePatchSha256": "${PATCH_SHA}",
  "driverSha256": "${DRIVER_SHA}",
  "androidApi": ${sdkver},
  "platformSdk": ${platform_sdk},
  "cpuTune": "${cpu_tune_flags}",
  "ndk": "${ndkver}"
}
EOF
	cp build-manifest.json "$workdir/${_zip_name%.zip}.manifest.json"
	zip -q "/tmp/${_zip_name}" libvulkan_freedreno.so meta.json
	cd - > /dev/null

	if ! [ -f "/tmp/${_zip_name}" ]; then
		echo -e "${red}Failed to pack the archive!${nocolor}"
	else
		cp "/tmp/${_zip_name}" "$workdir/"
		echo -e "${green}Build completed successfully! → ${_zip_name}${nocolor}"
	fi
}

run_all
