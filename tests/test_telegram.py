"""Tests for APK parsing and Telegram caption generation."""

import unittest
from revanced_bot.models import ReleaseAsset
from revanced_bot.telegram import _build_caption, _format_app_name, _parse_apk_name, _split_version_arch


class TestApkParsing(unittest.TestCase):
    def test_twitter_piko(self) -> None:
        filename = "twitter-piko-v12.29.1-prod.01-all.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "Twitter")
        self.assertEqual(version, "12.29.1-prod.01")
        self.assertEqual(arch, "all")

        asset = ReleaseAsset(name=filename, size=50 * 1024 * 1024, download_url="https://example.com")
        caption = _build_caption(asset, "20221066")
        self.assertIn("🐦 **Twitter ReVanced**", caption)
        self.assertIn("📌 Version: `v12.29.1-prod.01`", caption)
        self.assertIn("🏗️ Arch: `all`", caption)

    def test_googlephotos_devanced(self) -> None:
        filename = "googlephotos-devanced-v7.92.0.977185651-all.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "Google Photos")
        self.assertEqual(version, "7.92.0.977185651")
        self.assertEqual(arch, "all")

        asset = ReleaseAsset(name=filename, size=80 * 1024 * 1024, download_url="https://example.com")
        caption = _build_caption(asset, "20221066")
        self.assertIn("📷 **Google Photos ReVanced**", caption)
        self.assertIn("📌 Version: `v7.92.0.977185651`", caption)
        self.assertIn("🏗️ Arch: `all`", caption)

    def test_googlephotos_revanced(self) -> None:
        filename = "googlephotos-revanced-v7.88.0.966185373-all.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "Google Photos")
        self.assertEqual(version, "7.88.0.966185373")
        self.assertEqual(arch, "all")

    def test_music_morphe_multisegment_arch(self) -> None:
        filename = "music-morphe-v9.20.53-arm64-v8a.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "Music")
        self.assertEqual(version, "9.20.53")
        self.assertEqual(arch, "arm64-v8a")

        asset = ReleaseAsset(name=filename, size=30 * 1024 * 1024, download_url="https://example.com")
        caption = _build_caption(asset, "20221066")
        self.assertIn("🎵 **Music ReVanced**", caption)
        self.assertIn("📌 Version: `v9.20.53`", caption)
        self.assertIn("🏗️ Arch: `arm64-v8a`", caption)

    def test_youtube_morphe(self) -> None:
        filename = "youtube-morphe-v21.16.256-all.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "YouTube")
        self.assertEqual(version, "21.16.256")
        self.assertEqual(arch, "all")

        asset = ReleaseAsset(name=filename, size=120 * 1024 * 1024, download_url="https://example.com")
        caption = _build_caption(asset, "20221066")
        self.assertIn("▶️ **YouTube ReVanced**", caption)
        self.assertIn("📌 Version: `v21.16.256`", caption)
        self.assertIn("🏗️ Arch: `all`", caption)

    def test_reddit_morphe(self) -> None:
        filename = "reddit-morphe-v2026.24.0-all.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "Reddit")
        self.assertEqual(version, "2026.24.0")
        self.assertEqual(arch, "all")

        asset = ReleaseAsset(name=filename, size=60 * 1024 * 1024, download_url="https://example.com")
        caption = _build_caption(asset, "20221066")
        self.assertIn("🤖 **Reddit ReVanced**", caption)
        self.assertIn("📌 Version: `v2026.24.0`", caption)
        self.assertIn("🏗️ Arch: `all`", caption)

    def test_apk_without_patcher(self) -> None:
        filename = "youtube-v21.16.256-all.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "YouTube")
        self.assertEqual(version, "21.16.256")
        self.assertEqual(arch, "all")

    def test_fallback_unrecognized_filename(self) -> None:
        filename = "unknown_custom_file.apk"
        name, version, arch = _parse_apk_name(filename)
        self.assertEqual(name, "unknown_custom_file")
        self.assertEqual(version, "unknown")
        self.assertEqual(arch, "unknown")

        asset = ReleaseAsset(name=filename, size=10 * 1024 * 1024, download_url="https://example.com")
        caption = _build_caption(asset, "123")
        self.assertIn("📌 Version: `unknown`", caption)

    def test_all_known_upstream_releases(self) -> None:
        expected = [
            ("googlephotos-devanced-v7.80.0.929302933-all.apk", ("Google Photos", "7.80.0.929302933", "all")),
            ("googlephotos-devanced-v7.91.0.973540846-all.apk", ("Google Photos", "7.91.0.973540846", "all")),
            ("googlephotos-devanced-v7.92.0.977185651-all.apk", ("Google Photos", "7.92.0.977185651", "all")),
            ("googlephotos-revanced-v7.88.0.966185373-all.apk", ("Google Photos", "7.88.0.966185373", "all")),
            ("googlephotos-revanced-v7.90.0.971743778-all.apk", ("Google Photos", "7.90.0.971743778", "all")),
            ("music-morphe-v9.15.51-arm-v7a.apk", ("Music", "9.15.51", "arm-v7a")),
            ("music-morphe-v9.15.51-arm64-v8a.apk", ("Music", "9.15.51", "arm64-v8a")),
            ("music-morphe-v9.20.53-arm-v7a.apk", ("Music", "9.20.53", "arm-v7a")),
            ("music-morphe-v9.20.53-arm64-v8a.apk", ("Music", "9.20.53", "arm64-v8a")),
            ("reddit-morphe-v2026.14.0-all.apk", ("Reddit", "2026.14.0", "all")),
            ("reddit-morphe-v2026.24.0-all.apk", ("Reddit", "2026.24.0", "all")),
            ("twitter-piko-v12.22.0-prod.01-all.apk", ("Twitter", "12.22.0-prod.01", "all")),
            ("twitter-piko-v12.24.0-prod.02-all.apk", ("Twitter", "12.24.0-prod.02", "all")),
            ("twitter-piko-v12.25.2-prod.01-all.apk", ("Twitter", "12.25.2-prod.01", "all")),
            ("twitter-piko-v12.27.0-prod.01-all.apk", ("Twitter", "12.27.0-prod.01", "all")),
            ("twitter-piko-v12.28.0-prod.01-all.apk", ("Twitter", "12.28.0-prod.01", "all")),
            ("twitter-piko-v12.29.1-prod.01-all.apk", ("Twitter", "12.29.1-prod.01", "all")),
            ("youtube-morphe-v21.04.223-all.apk", ("YouTube", "21.04.223", "all")),
            ("youtube-morphe-v21.07.247-all.apk", ("YouTube", "21.07.247", "all")),
            ("youtube-morphe-v21.13.164-all.apk", ("YouTube", "21.13.164", "all")),
            ("youtube-morphe-v21.16.256-all.apk", ("YouTube", "21.16.256", "all")),
        ]
        for filename, exp in expected:
            with self.subTest(filename=filename):
                self.assertEqual(_parse_apk_name(filename), exp)


if __name__ == "__main__":
    unittest.main()
