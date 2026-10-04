# FrameMonster

Extract frames from videos and save them as JPG or PNG images. Process one video
or a folder of videos, choose how often to take a frame, and optionally trim or
resize the result.

By default, FrameMonster saves **one frame per second** as JPG files named
`frame_00001.jpg`, `frame_00002.jpg`, and so on. Your source videos are kept intact.

## Requirements

- [Python](https://www.python.org/downloads/) 3.7 or newer.
- [FFmpeg](https://ffmpeg.org/download.html), installed and available on your `PATH`
  (the directories your terminal searches for commands).

FrameMonster uses Python's standard library; no Python packages need to be installed.

### Install FFmpeg

**macOS** with [Homebrew](https://brew.sh):

```sh
brew install ffmpeg
```

**Linux** — use the command for your distribution:

```sh
# Debian / Ubuntu
sudo apt update
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

**Windows** — in PowerShell or Command Prompt, using
[Windows Package Manager](https://learn.microsoft.com/windows/package-manager/winget/):

```powershell
winget install --id Gyan.FFmpeg --exact
```

If you use Chocolatey, `choco install ffmpeg` is another option. You can also get a
build from the [FFmpeg downloads page](https://ffmpeg.org/download.html) and add its
`bin` directory to your `PATH`. Open a new terminal after installation.

Check that FFmpeg is available:

```sh
ffmpeg -version
```

## Quick start

Download this repository as a ZIP and extract it, or clone it with Git:

```sh
git clone https://github.com/wernjien/framemonster.git
cd framemonster
```

Run the following command from the repository folder. Replace `my video.mp4` with
the path to your own video; keep quotation marks around paths containing spaces.

**macOS / Linux:**

```sh
python3 framemonster "my video.mp4"
```

**Windows:**

```powershell
python framemonster "my video.mp4"
```

The images will appear in a new `my video_frames` folder beside the video.
Output folders are created automatically. Use `python3 framemonster --help` to see
all options; on Windows, replace `python3` with `python` in the examples below.

On macOS / Linux, you can also run `chmod +x framemonster` once and then use
`./framemonster` instead of `python3 framemonster`.

## Common examples

Save four frames per second as PNG images:

```sh
python3 framemonster myvideo.mp4 --fps 4 --format png
```

Save one frame every two seconds in a folder named `frames`:

```sh
python3 framemonster myvideo.mp4 --interval 2 -o ./frames
```

Extract a 30-second section starting at 10 seconds, with images 1280 pixels wide:

```sh
python3 framemonster myvideo.mp4 --start 00:00:10 --duration 00:00:30 --scale 1280x-1
```

`--duration` is the length of the section. This example covers seconds 10 through
40. `1280x-1` calculates the height automatically to preserve the video's aspect
ratio. Use `1280x720` to set both dimensions, or `1280x-2` to calculate an even height.
Other negative values, such as `-4`, calculate a dimension divisible by that number,
as described in the [FFmpeg scale documentation](https://ffmpeg.org/ffmpeg-filters.html#scale).

Change the filename prefix and start numbering at 100:

```sh
python3 framemonster myvideo.mp4 --prefix shot --start-number 100
```

The first image will be named `shot_00100.jpg`. Numbering uses at least five digits.

### Process a folder of videos

```sh
python3 framemonster ./videos -r -o ./frames
```

`-r` includes subdirectories. Each video gets its own output folder, and the source
subdirectory structure is preserved:

```text
Input                           Output
videos/intro.mp4                 frames/intro/frame_00001.jpg
videos/day1/clip.mp4             frames/day1/clip/frame_00001.jpg
videos/day2/clip.mp4             frames/day2/clip/frame_00001.jpg
```

Without `-o`, each output folder is created beside its video with `_frames` added
to the name. When video names would share an output folder, their file extensions
are included to keep them separate: `clip.mp4` and `clip.mov` become
`frames/clip.mp4/` and `frames/clip.mov/`, or `clip.mp4_frames/` and
`clip.mov_frames/` without `-o`.

Folder searches recognize these extensions, regardless of capitalization:
`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.m4v`, `.wmv`, `.flv`, `.mpg`, `.mpeg`,
and `.3gp`. A directly supplied video file can use any format that your FFmpeg
installation supports.

If upgrading from a version that flattened recursive output into one folder,
check the preserved subdirectories under your chosen output folder.

### Run again or replace existing frames

FrameMonster skips any non-empty output folder by default. To allow writing into
it and replace matching filenames, add `--overwrite`:

```sh
python3 framemonster myvideo.mp4 -o ./frames --overwrite
```

**`--overwrite` keeps files that the current run does not replace.** For example,
if an earlier run saved 100 images and the new run saves 10, images 11 through 100
remain. Use a new or empty output folder when you want only the frames from the
new run. The reported frame count always describes the current run.

## Options

| Option | What it does | Default |
| --- | --- | --- |
| `-o`, `--output-dir` | Save one video's frames directly here, or a batch in subfolders here | `<video-name>_frames` beside each video |
| `-r`, `--recursive` | Include subdirectories when the input is a folder | Off |
| `--fps` | Frames per second; must be a positive, finite number | 1 |
| `--interval` | Seconds between frames; must be a positive, finite number. Choose either this or `--fps` | Unset |
| `--format` | `jpg` or `png` | `jpg` |
| `--quality` | JPG quality: 2 is highest, 31 is lowest. Ignored for PNG | 2 |
| `--prefix` | Filename prefix; use a name without path separators or characters invalid in Windows filenames | `frame` |
| `--start-number` | First frame number, from 0 to 2147483647 | 1 |
| `--scale` | Image size as `WIDTHxHEIGHT`; `0` keeps the source dimension, `-1` calculates it, `-2` calculates an even value | Original size |
| `--start` | Start position, in seconds or `HH:MM:SS` (fractional seconds allowed) | Beginning |
| `--duration` | Length to extract, in seconds or `HH:MM:SS` (fractional seconds allowed) | Until the end |
| `--overwrite` | Allow non-empty output folders and replace matching filenames | Off |

## Troubleshooting

- **`ffmpeg not found on PATH`:** install FFmpeg, open a new terminal, and check
  `ffmpeg -version`. For a manual installation, add the folder containing the
  FFmpeg executable to your `PATH`.
- **`video file or directory not found`:** check the input path. Relative paths are
  interpreted from the terminal's current folder. Put paths with spaces in quotes.
- **`output directory is not empty`:** choose a new output folder or use
  `--overwrite` after checking its contents.
- **`cannot use output directory`:** check write permissions and make sure the
  output path points to a folder rather than an existing file.
- **`ffmpeg exited with status ...`:** read the FFmpeg error printed above it. The
  input may be damaged, lack a video stream, or use an unsupported codec. In a
  batch, FrameMonster continues with the remaining videos.
- **No frames saved:** try a longer section, an earlier start position, or a higher
  frame rate. A section shorter than the sampling interval may produce no frames.

Exit codes are `0` for a successful run, `1` if a video fails or an output folder
is skipped, and `2` for invalid command-line options. A batch prints how many
videos succeeded.

## Development

Run the regression tests from the repository folder:

```sh
python3 -m unittest discover -s tests -v
```

The tests use Python's standard library. Extraction tests create small temporary
videos and run real FFmpeg commands; they are skipped if FFmpeg is unavailable.
On Windows, use `python` in place of `python3`.

For optional formatting and lint checks, install
[Ruff](https://docs.astral.sh/ruff/) with `python3 -m pip install ruff`, then run:

```sh
ruff format framemonster tests
ruff check framemonster tests
```

## License

[MIT](LICENSE)
