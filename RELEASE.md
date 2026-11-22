# Arachnid 1.0 release guide

## Windows download

Local builds are saved under `Documents\ARACHNID\<version>`, including the executable, Windows ZIP, and SHA-256 file.

The 1.0 release is a portable x64 ZIP for Windows 11 with the supported Microsoft Visual C++ v14 x64 Redistributable. Extract it to a permanent folder and open `Arachnid.exe`. Keep `_internal` beside the executable. Closing the companion hides it in the notification area. Reopening the executable or clicking its tray icon brings it back. **Quit Arachnid** exits the process.

Publish the Windows ZIP and its `.sha256` file together. The archive includes Python, Qt, third-party notices, and license texts. The current package is unsigned. Windows SmartScreen can warn about an unsigned download, and managed devices may block it. For a signed Windows release, obtain a trusted publisher identity, sign and timestamp the executable before packaging, then verify the signature and regenerate the ZIP checksum. [Microsoft’s Windows signing options](https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options) · [SmartScreen reputation](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation)

## Draft release notes

**Arachnid 1.0.0 for Windows** is the first stable build of the desktop scorpion companion. Pet it, pick it up, let it crawl around a window, or enable bird’s-eye roaming. The tray gives you quick access to Show, Hide, Rest, Wake Up, Settings, and Quit. Pick a finish, adjust the size, and choose whether it curls up to sleep. Arachnid hides when a fullscreen app takes focus and returns according to your visibility setting.

On startup, Arachnid pries open a rift and walks onto the desktop. Fresh profiles start with Blackout Red.

Existing Arachnid preferences carry over. Start by quitting your earlier preview, then extract the entire 1.0 ZIP to its own folder. Windows 11 x64 is the release target. The current download is unsigned.

## GitHub publishing

1. Review the hardened 1.0.0 source and MIT license in the private repository before approving public visibility.
2. Commit the source and tag the exact commit used to build the download. Use `v1.0.0` in the public repository after confirming that tag is available. Create a draft GitHub Release on the matching tag and paste the release notes above.
3. Attach `Arachnid-1.0.0-win-x64.zip` and its `.sha256` file as release assets. GitHub also supplies a source archive from the tag. The Windows ZIP includes the runnable executable and its bundled libraries. Include the corresponding Qt Base and PySide/Shiboken source links from the package notices alongside the binary download. Verify that they match the files distributed and remain accessible.
4. Verify the ZIP checksum and test the download on a clean Windows 11 x64 installation with the Microsoft Visual C++ x64 Redistributable before publishing. A public repository is useful for source and release downloads. GitHub also supports releases and assets in private repositories for people with access. [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) · [Creating a draft release and attaching files](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
