# Opt-in A650 SYSMEM screen

Primary variable: disable GMEM selection on A650 in our own pinned driver.
Hypothesis: remove costly tile load/store work in the GPU-saturated busy street;
possible downside is increased bandwidth and slower geometry/fragment rendering.
This is adapted from a source idea, not a third-party driver replacement.

Build profile sd865-sysmem-screen keeps Mesa76b9372, API29, A77/O3/ThinLTO,
program-reference,512KiB pipeline allocator and normal synchronization. Existing
profiles are unchanged. The new artifact-only CI builds just this candidate,
records builder/source/patch/binary hashes and performs ELF and allocator checks.

Device acceptance remains required: distinct import/selection/mapped binary hash,
A650-only SYSMEM trace reason,60s actual fixed720p busy street, crash/graphics
correctness, current driver comparison, then baseline driver/hash restoration.
Screening heuristics10% mean interval or15%P99 prioritize longer repeated native
validation. Do not infer source FPS or promote from successful compilation.
No Engine.ini/save/cache modifications; never replace an existing driver label.
