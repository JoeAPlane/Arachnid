Arachnid 1.0.0 | Windows 11 x64 portable release

Quit any earlier preview, then extract the entire archive to its own
folder. Open the Arachnid folder and double-click Arachnid.exe. Keep the
_internal folder beside it. Python is bundled and your preferences carry over.
This portable build is unsigned. Review its origin and the published checksum
before opening it.

Left-click to pet the scorpion. It crouches, wags its tail, and shows a heart. When picked up, it trails the
cursor briefly, kicks its legs, and pouts until you put it down.
Right-click and choose Rest to make it sleep or Wake Up to rouse it.
Pause and Resume remain separate controls. Enable Curl up while sleeping
in Settings to use the curled pose when you choose Rest.
Right-click the Arachnid system tray icon for Pause/Resume, Rest/Wake Up,
Show/Hide, Settings, and Quit. Check the taskbar's hidden-icons arrow if
the icon is in overflow. The tray menu remains available while Arachnid
is hidden or asleep. Left-click the icon to reopen Arachnid after
hiding it or closing the window. Quit exits the app. To reopen after Quit,
right-click Arachnid.exe and choose Show more options > Pin to taskbar.
Launching again brings back the running companion when it uses the same
settings profile.

On startup, Arachnid pulls open a rift with its front legs and walks out.
Blackout Red is the default for a fresh settings profile.

In Settings, pick Graphite, Foundry, Glacier, Blackout Red, or EdgeRunner,
then choose Save. The Size slider previews sizes from 70% to 150%.
EdgeRunner has weathered yellow plating, exposed wiring, and a segmented
cyan visor that glitches briefly on wake-up and pickup.
Click sound is muted by default. Preferences are stored per Windows user.
Enable Bird's-eye view to roam in any direction on the current display.
Use the side view to climb and perch on application windows.
Drop Arachnid just below a window with room underneath to crawl upside down.
Or drop it beside the lower half of either side to watch it descend
and round the bottom corner. A higher drop leads toward the top.
Drag sideways to see the chassis lean, then release to see it settle.
In bird's-eye view, the robot shortens its stride during sharp turns.

To try climbing, focus an unmaximized app window with room around it.
Drop Arachnid beside a side edge or place its feet on the top edge.
Move the cursor away so its autonomous behavior can resume.

Arachnid hides for fullscreen apps and restores your last Show/Hide choice
when you return to the desktop. It stays visible with ordinary title-bar
windows that are maximized.

Optional PowerShell launch flags from the extracted folder:
    Start-Process .\Arachnid.exe -ArgumentList '--paused'
    Start-Process .\Arachnid.exe -ArgumentList '--speed','180'

On one 1920 x 1080 Windows display, the overlay hid over the live VALORANT
lobby. It also hid and returned during tests with borderless fullscreen and
a Direct3D 9 fullscreen swap chain. Physical mixed-DPI monitor changes and
system sleep/resume still need verification.

See THIRD_PARTY_NOTICES.txt and LICENSES for the bundled components.
