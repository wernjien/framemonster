"""Regression tests, including extraction with small real FFmpeg videos."""

import contextlib
import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "framemonster"
LOADER = SourceFileLoader("framemonster", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
framemonster = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(framemonster)


class ArgumentTests(unittest.TestCase):
    def assert_invalid(self, options):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
            framemonster.parse_args(["video.mp4", *options])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("error:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_rates_must_be_positive_and_finite(self):
        for option in ["--fps", "--interval"]:
            for value in ["0", "-1", "nan", "inf", "-inf"]:
                with self.subTest(option=option, value=value):
                    self.assert_invalid([f"{option}={value}"])

    def test_rates_are_mutually_exclusive(self):
        self.assert_invalid(["--fps", "1", "--interval", "2"])

    def test_invalid_scales_are_rejected(self):
        for value in ["invalid", "1280", "1x2x3", "1280xno", "2147483648x720"]:
            with self.subTest(value=value):
                self.assert_invalid(["--scale", value])

    def test_valid_scales_and_rate_defaults(self):
        for value in ["1280x720", "1280X-1", "1280x-2", "1280x-4", "0x720"]:
            with self.subTest(value=value):
                args = framemonster.parse_args(["video.mp4", "--scale", value])
                self.assertEqual(args.scale, value.lower())
        self.assertEqual(
            framemonster.build_fps_expr(framemonster.parse_args(["v"])), "1"
        )

    def test_quality_and_sequence_number_ranges(self):
        for option, values in [
            ("--quality", ["1", "32"]),
            ("--start-number", ["-1", "2147483648"]),
        ]:
            for value in values:
                with self.subTest(option=option, value=value):
                    self.assert_invalid([option, value])
        args = framemonster.parse_args(["v", "--quality", "31", "--start-number", "0"])
        self.assertEqual((args.quality, args.start_number), (31, 0))

    def test_prefix_cannot_escape_output_directory(self):
        for value in ["", "../outside", "..\\outside", "/absolute", "bad:prefix"]:
            with self.subTest(value=value):
                self.assert_invalid(["--prefix", value])
        args = framemonster.parse_args(["v", "--prefix", "still[100%]"])
        self.assertEqual(args.prefix, "still[100%]")


class OutputPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="framemonster-plan-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_recursive_outputs_keep_subdirectories(self):
        source = self.root / "videos"
        videos = [source / "one" / "clip.mp4", source / "two" / "clip.mp4"]
        output = self.root / "frames"
        plan = framemonster.plan_outputs(source, videos, output)
        self.assertEqual(
            [folder for _, folder in plan],
            [output / "one" / "clip", output / "two" / "clip"],
        )

    def test_same_stem_uses_extension_with_and_without_output_option(self):
        videos = [self.root / "clip.mp4", self.root / "clip.mov"]
        for output in [None, self.root / "frames"]:
            with self.subTest(output=output):
                plan = framemonster.plan_outputs(self.root, videos, output)
                names = [folder.name for _, folder in plan]
                suffix = "_frames" if output is None else ""
                self.assertEqual(names, ["clip.mp4" + suffix, "clip.mov" + suffix])

    def test_extension_fallback_cannot_collide_with_another_stem(self):
        videos = [
            self.root / "clip.mp4",
            self.root / "clip.mov",
            self.root / "clip.mp4.mov",
        ]
        plan = framemonster.plan_outputs(self.root, videos, self.root / "frames")
        self.assertEqual(
            [folder.name for _, folder in plan],
            ["clip.mp4", "clip.mov", "clip.mp4.mov"],
        )

    def test_unresolvable_collision_fails_before_extraction(self):
        videos = [self.root / "clip.mp4", self.root / "CLIP.MP4"]
        with self.assertRaisesRegex(ValueError, "rename"):
            framemonster.plan_outputs(self.root, videos, self.root / "frames")

    def test_find_videos_filters_extensions_and_handles_uppercase(self):
        for name in ["clip.MP4", "other.mov", "notes.txt", "nested/deep.mkv"]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        (self.root / "folder.mp4").mkdir()
        self.assertEqual(len(framemonster.find_videos(self.root, False)), 2)
        self.assertEqual(len(framemonster.find_videos(self.root, True)), 3)


class ErrorHandlingTests(unittest.TestCase):
    def test_failure_to_launch_ffmpeg_has_readable_error(self):
        with tempfile.TemporaryDirectory(prefix="framemonster-error-") as directory:
            stderr = io.StringIO()
            args = framemonster.parse_args(["video.mp4"])
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(
                        framemonster.subprocess,
                        "run",
                        side_effect=FileNotFoundError("missing"),
                    )
                )
                stack.enter_context(contextlib.redirect_stderr(stderr))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                result = framemonster.extract_frames(
                    Path("video.mp4"), Path(directory), args, "1"
                )
            self.assertIsNone(result)
            self.assertIn("cannot run ffmpeg", stderr.getvalue())


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for extraction tests")
class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = tempfile.TemporaryDirectory(prefix="framemonster-fixture-")
        cls.video = Path(cls.fixture_dir.name) / "source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=160x120:rate=8:duration=3",
                "-c:v",
                "mpeg4",
                str(cls.video),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture_dir.cleanup()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="framemonster-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.frames = self.root / "frames"

    def run_cli(self, *options, video=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(video or self.video), *options],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            cwd=self.root,
        )

    def assert_success(self, result, frame_count):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Done. {frame_count} frame(s)", result.stdout)

    def test_default_jpeg_extraction(self):
        self.assert_success(self.run_cli("-o", str(self.frames)), 3)
        self.assertEqual(
            sorted(image.name for image in self.frames.iterdir()),
            ["frame_00001.jpg", "frame_00002.jpg", "frame_00003.jpg"],
        )

    def test_png_rate_resize_and_custom_numbering(self):
        for scale in ["80x-2", "80x-4"]:
            with self.subTest(scale=scale):
                output = self.frames / scale
                self.assert_success(
                    self.run_cli(
                        "-o",
                        str(output),
                        "--format",
                        "png",
                        "--fps",
                        "2",
                        "--scale",
                        scale,
                        "--prefix",
                        "shot",
                        "--start-number",
                        "10",
                    ),
                    6,
                )
                images = sorted(output.glob("*.png"))
                self.assertEqual(len(images), 6)
                self.assertEqual(images[0].name, "shot_00010.png")
                # PNG's IHDR stores width and height at bytes 16..24.
                header = images[0].read_bytes()[:24]
                self.assertEqual(header[:8], bytes([137, 80, 78, 71, 13, 10, 26, 10]))
                self.assertEqual(int.from_bytes(header[16:20], "big"), 80)
                self.assertEqual(int.from_bytes(header[20:24], "big"), 60)

    def test_interval_and_clip_selection(self):
        self.assert_success(
            self.run_cli(
                "-o",
                str(self.frames),
                "--interval",
                "0.5",
                "--start",
                "00:00:01",
                "--duration",
                "1",
            ),
            2,
        )
        self.assertEqual(len(list(self.frames.glob("*.jpg"))), 2)

    def test_nonempty_output_is_unchanged_without_overwrite(self):
        self.assert_success(self.run_cli("-o", str(self.frames)), 3)
        before = {image.name: image.read_bytes() for image in self.frames.iterdir()}
        result = self.run_cli("-o", str(self.frames), "--fps", "2")
        self.assertEqual(result.returncode, 1)
        self.assertIn("output directory is not empty", result.stderr)
        self.assertEqual(
            {image.name: image.read_bytes() for image in self.frames.iterdir()}, before
        )

    def test_overwrite_reports_only_current_run_and_keeps_other_files(self):
        self.assert_success(self.run_cli("-o", str(self.frames)), 3)
        notes = self.frames / "notes.txt"
        notes.write_text("keep this", encoding="utf-8")
        self.assert_success(
            self.run_cli("-o", str(self.frames), "--duration", "1", "--overwrite"), 1
        )
        self.assertEqual(len(list(self.frames.glob("*.jpg"))), 3)
        self.assertEqual(notes.read_text(encoding="utf-8"), "keep this")

    def test_percent_and_brackets_in_paths_are_literal(self):
        output = self.root / "frames [100%]"
        self.assert_success(self.run_cli("-o", str(output), "--prefix", "shot[50%]"), 3)
        self.assertTrue((output / "shot[50%]_00001.jpg").is_file())
        self.assertEqual(len(list(output.iterdir())), 3)

    def test_recursive_same_name_videos_have_separate_frames(self):
        videos = self.root / "videos"
        for subfolder in ["one", "two"]:
            target = videos / subfolder / "clip.MP4"
            target.parent.mkdir(parents=True)
            shutil.copyfile(self.video, target)
        result = self.run_cli("-r", "-o", str(self.frames), video=videos)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Processed 2/2 video(s)", result.stdout)
        for subfolder in ["one", "two"]:
            self.assertEqual(
                len(list((self.frames / subfolder / "clip").glob("*.jpg"))), 3
            )

    def test_same_stem_formats_both_extract(self):
        videos = self.root / "videos"
        videos.mkdir()
        for name in ["clip.mp4", "clip.mov"]:
            shutil.copyfile(self.video, videos / name)
        result = self.run_cli("-o", str(self.frames), video=videos)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ["clip.mp4", "clip.mov"]:
            self.assertEqual(len(list((self.frames / name).glob("*.jpg"))), 3)

    def test_batch_continues_after_corrupt_video(self):
        videos = self.root / "videos"
        videos.mkdir()
        (videos / "a-broken.mp4").write_bytes(b"not a video")
        shutil.copyfile(self.video, videos / "b-working.mp4")
        result = self.run_cli("-o", str(self.frames), video=videos)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Processed 1/2 video(s)", result.stdout)
        self.assertEqual(len(list((self.frames / "b-working").glob("*.jpg"))), 3)
        self.assertNotIn("Traceback", result.stderr)

    def test_output_file_is_reported_without_traceback(self):
        self.frames.write_text("existing file", encoding="utf-8")
        result = self.run_cli("-o", str(self.frames))
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot use output directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.frames.read_text(encoding="utf-8"), "existing file")

    def test_empty_and_missing_inputs_have_readable_errors(self):
        empty = self.root / "empty"
        empty.mkdir()
        for source, message in [
            (empty, "no video files found"),
            (self.root / "missing.mp4", "video file or directory not found"),
        ]:
            with self.subTest(source=source):
                result = self.run_cli(video=source)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
