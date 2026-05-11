# Contributing to FlexRIC

This guide describes the current development workflow for this repository and the main places to change code depending on what you are building.

## Development Workflow

1. Configure the build from the repository root.

   ```bash
   cmake -S . -B build -DPython3_EXECUTABLE="$(which python3)"
   ```

2. Build the project.

   ```bash
   cmake --build build -j8
   ```

3. Run the test suite before sending changes.

   ```bash
   ctest --test-dir build -j8 --output-on-failure
   ```

4. If you changed the Python xApp SDK or portal, rebuild the SWIG target so the generated files are refreshed in `build/examples/xApp/python3`.

   ```bash
   cmake --build build --target xapp_sdk -j4
   ```

FlexRIC's Python xApps require Python 3.10 or newer, and the generated SWIG module must be built with the same interpreter you will use at runtime.

## Repository Map

| Path | Purpose |
|:-----|:--------|
| `src/agent/` | E2 agent runtime, transport, handlers, and agent-side plugin integration |
| `src/ric/` | nearRT-RIC runtime, E2 node management, and RIC-side integrations |
| `src/xApp/` | xApp runtime, dispatch/pending-event logic, database adapters, and SWIG bindings |
| `src/sm/` | Service model implementations for KPM, RC, MAC, RLC, PDCP, SLICE, TC, and GTP |
| `src/lib/` | Shared E2AP, 3GPP, message, and codec support libraries |
| `examples/emulator/agent/` | Emulated E2 agents used for local testing |
| `examples/ric/` | Runnable `nearRT-RIC` example |
| `examples/xApp/c/` | C xApp examples |
| `examples/xApp/python3/` | Python xApps, generated SDK consumers, and the current agent portal stack |
| `test/` | Unit, encode/decode, and end-to-end integration tests |

## Common Contribution Paths

### Agent, RIC, and protocol work

- Change `src/agent/` for E2 node agent behavior.
- Change `src/ric/` for nearRT-RIC behavior.
- Change `src/lib/` for shared E2AP, transport, or codec logic.
- Add or update tests in `test/agent-ric/`, `test/agent-ric-xapp/`, or `test/encode_decode/` when protocol behavior changes.

### Service model work

When adding or extending a service model, the change is usually spread across several layers:

- `src/sm/<name>_sm/` for the service model implementation itself
- `examples/emulator/agent/` to expose the model from the emulator
- `examples/xApp/c/` or `examples/xApp/python3/` to exercise subscriptions or controls
- `test/sm/` and, when applicable, `test/encode_decode/sm/` for validation
- the relevant `CMakeLists.txt` files so the new sources are compiled into the right targets

KPM is versioned separately (`v02.01`, `v02.03`, `v03.00`), so changes there should be checked against the configured `KPM_VERSION` and the selected `E2AP_VERSION`.

### Python xApps and portal work

- Source edits for the Python portal live in `examples/xApp/python3/`.
- The runtime copy used for execution lives under `build/examples/xApp/python3/` after building `xapp_sdk`.
- The current portal/backend layout is documented in `examples/xApp/python3/README.md`.

If you touch the SWIG bridge in `src/xApp/swig/`, the Python SDK runtime in `src/xApp/`, or Python example files under `examples/xApp/python3/`, rebuild `xapp_sdk` and verify the generated runtime from the build tree.

## Validation Expectations

- Run `ctest --test-dir build -j8 --output-on-failure` after C or CMake changes.
- Prefer adding or updating the closest existing test when fixing a bug.
- If the change affects Python examples or the portal, run them from `build/examples/xApp/python3/` so you are testing against the generated `_xapp_sdk.so` and `xapp_sdk.py`.
- If the change affects build options such as `E2AP_VERSION`, `KPM_VERSION`, or `XAPP_MULTILANGUAGE`, mention the configuration you validated.

## Practical Guidelines

- Keep documentation in sync with runtime changes, especially when scripts, ports, paths, or required dependencies change.
- Avoid committing generated or local-only artifacts when possible, such as `build/`, `__pycache__/`, `.pyc`, and ad hoc backup files.
- Be careful with version-coupled code paths. FlexRIC supports multiple E2AP and KPM combinations, and those switches are selected in CMake rather than inside a single runtime profile.
