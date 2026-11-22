# Project plan

See [TEST_REPORT.md](TEST_REPORT.md) for release validation and the remaining checks on physical displays and other Windows profiles.

| Milestone | Work |
| --- | --- |
| 0.1 | Set up the Python environment, document launch, and initialize the repository. |
| 0.2 | Render a small transparent Qt window with a placeholder, topmost placement, and a quit control. |
| 0.3 | Test clicks, hover, drag capture, and native input through transparent pixels. |
| 0.4 | Add timed movement, speed selection, pause, and work-area boundaries. |
| 0.5 | Detect visible desktop windows and changes in their bounds. |
| 0.6 | Record automated and desktop test results, performance, and display limitations. |

## Phase 1

The prototype has six independently articulated legs, a segmented tail, and a two-tone sensor light. The legs alternate between two groups of three. Walking speed controls gait cadence and the character faces the new direction at each screen edge.

## Phase 2

The robot alternates short walks and rests, attends to nearby cursor movement, and reacts to clicks. Pausing, opening the menu, and dragging suspend its active behavior timer.

## Phase 3

ARACHNID can perch or walk on the active window's top edge, climb either side, and turn the upper corner. It follows eligible window moves and resizes on one display. A foreground fullscreen window suppresses the overlay and its behavior.

## Phase 4

The refined rig has three armor finishes, smoother movement and poses, and separately controlled click light and servo feedback. A settings dialog previews finishes and saves preferences per Windows user.

## Phase 5

The portable build bundles Python, Qt, and the servo sample. Default operation avoids the full desktop-window census used by diagnostics. The packaged build and release checks are recorded in the test report.

## Preview reliability

Version 0.5.1 corrects fullscreen detection for conventional maximized windows, keeps the overlay hidden during short focus gaps, and hardens placement when displays change. Physical mixed-DPI transitions, live display disconnects, and a separate clean Windows account still need a hands-on check.

## Desktop controls and finishes

Version 0.6 added weighted pickup, overhead roaming, manual Rest/Wake Up, and underside crawling. Version 0.7 adds the Windows tray controls and gives Neon Runner its own chassis and visor in both views.

The 0.7.1 desktop reliability pass verifies the 0.7.0 binary through the Explorer notification area and at both 100% and 150% Qt scaling. The native navigation test now uses an isolated preference file. See the [test report](TEST_REPORT.md) for results.

Version 0.7.2 fixes drag release and display-removal recovery. The fullscreen checks passed on a single display, including the VALORANT lobby and a Direct3D fullscreen fixture. The physical mixed-DPI and system sleep/resume checks are pending.

Version 0.8 adds a staged pickup and landing, lower-corner transitions into underside crawling, and shorter strides while turning in bird’s-eye view. The Windows x64 build passed motion checks at 100% and 150% Qt scaling.

Version 0.9 is the Windows release candidate. The [test report](TEST_REPORT.md) records matched CPU and memory samples against 0.8.0, portable startup, and fresh-profile settings persistence.
