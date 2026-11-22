# Arachnid 1.0 release guide

## Windows download

The 1.0 release is a portable x64 ZIP for Windows 11. Extract it to a permanent folder and open `Arachnid.exe`. Keep `_internal` beside the executable. Closing the companion hides it in the notification area. Reopening the executable or clicking its tray icon brings it back. **Quit Arachnid** exits the process.

Publish the Windows ZIP and its `.sha256` file together. The archive includes the bundled runtime, third-party notices, and license texts. The current package is unsigned. Windows SmartScreen can warn about an unsigned download, and managed devices may block it. For a signed Windows release, obtain a trusted publisher identity, sign and timestamp the executable before packaging, then verify the signature and regenerate the ZIP checksum. [Microsoft’s Windows signing options](https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options) · [SmartScreen reputation](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation)

## Draft release notes

**Arachnid 1.0.0 for Windows** is the first stable build of the desktop scorpion companion. Pet it, pick it up, let it crawl around a window, or enable bird’s-eye roaming. The tray gives you quick access to Show, Hide, Rest, Wake Up, Settings, and Quit. Pick a finish, adjust the size, and choose whether it curls up to sleep. Arachnid hides when a fullscreen app takes focus and returns according to your visibility setting.

In the startup build, Arachnid pries open a rift and walks onto the desktop. Fresh profiles start with Blackout Red.

Existing Arachnid preferences carry over. Start by quitting your earlier preview, then extract the entire 1.0 ZIP to its own folder. Windows 11 x64 is the release target. The current download is unsigned.

## GitHub publishing

1. Create a private repository first if you want to try the process before sharing the source. Import the 1.0 source snapshot and choose whether you want to grant an open-source license before making the repository public.
2. Commit the source and tag the exact commit used to build the download. For the startup build, use `v1.0.0-startup` if the repository already contains the earlier `v1.0.0` tag. Create a draft GitHub Release on the matching tag and paste the release notes above.
3. Attach `Arachnid-1.0.0-startup-win-x64.zip` and its `.sha256` file as release assets. GitHub also supplies a source archive from the tag. The Windows ZIP is the download that includes the runnable executable and its runtime.
4. Test the download from the draft before publishing. A public repository is useful for source and release downloads. GitHub also supports releases and assets in private repositories for people with access. [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) · [Creating a draft release and attaching files](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
