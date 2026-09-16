# FrameMonster

Extract frames from a video (or a whole folder of videos) as images, using `ffmpeg`.

## Requirements

- Python 3.7+
- [ffmpeg](https://ffmpeg.org/) available on your `PATH`

### Installing ffmpeg

**macOS**

```sh
brew install ffmpeg
```

**Linux**

```sh
# Debian / Ubuntu
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

**Windows**

```sh
winget install ffmpeg
# or
choco install ffmpeg
```

Or download a static build for your platform from the [ffmpeg downloads page](https://ffmpeg.org/download.html) and add it to your `PATH`.

## Installation

Clone the repo and make the script executable:

```sh
git clone git@github.com:wernjien/framemonster.git
cd framemonster
chmod +x framemonster
```

Optionally, put it on your `PATH` so you can run `framemonster` from anywhere:

```sh
ln -s "$(pwd)/framemonster" /usr/local/bin/framemonster
```

> **Windows users:** the file has no extension and relies on a Unix-style `#!/usr/bin/env python3` shebang, so it won't run by double-clicking or via `framemonster` directly in cmd/PowerShell. Run it explicitly with Python instead:
>
> ```sh
> python framemonster <video> [options]
> ```

## Usage

```sh
./framemonster VIDEO [options]
```

`VIDEO` can be a single video file or a directory containing video files (use `-r`/`--recursive` to include subdirectories).

### Examples

Extract 1 frame per second (default) next to the video, into `myvideo_frames/`:

```sh
./framemonster myvideo.mp4
```

Extract 4 frames per second as PNGs:

```sh
./framemonster myvideo.mp4 --fps 4 --format png
```

Extract 1 frame every 2 seconds into a specific folder:

```sh
./framemonster myvideo.mp4 --interval 2 -o ./frames
```

Process every video in a folder (recursively), one subfolder of frames per video:

```sh
./framemonster ./videos -r -o ./frames
```

Extract a clip from 10s to 40s, resized to 1280px wide:

```sh
./framemonster myvideo.mp4 --start 00:00:10 --duration 00:00:30 --scale 1280x-1
```

### Options

| Flag | Description |
| --- | --- |
| `-o`, `--output-dir` | Directory to save frames into (default: `<video-name>_frames` next to the video) |
| `-r`, `--recursive` | When `VIDEO` is a directory, also search subdirectories |
| `--fps` | Frames to extract per second |
| `--interval` | Seconds between extracted frames (mutually exclusive with `--fps`) |
| `--format` | Output image format: `jpg` (default) or `png` |
| `--quality` | JPEG quality for ffmpeg's `-qscale:v` (2=best, 31=worst) |
| `--prefix` | Filename prefix for extracted frames (default: `frame`) |
| `--start-number` | Starting number for the frame filename sequence |
| `--scale` | Resize frames, e.g. `1280x720` or `1280x-1` (keep aspect ratio) |
| `--start` | Start time to begin extracting from, e.g. `00:00:10` or `10` |
| `--duration` | Duration to extract, e.g. `00:00:30` or `30` |
| `--overwrite` | Overwrite existing files in a non-empty output directory |

## License

MIT
