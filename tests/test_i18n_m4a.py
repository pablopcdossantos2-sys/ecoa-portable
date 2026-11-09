"""Testes para traduções, opções visíveis e conversão de arquivos M4A."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecoa import paths, schedule  # noqa: E402
from ecoa.i18n import LANGUAGES, language_label, theme_options, tr  # noqa: E402
from ecoa.models import AUDIO_EXTENSIONS, Settings  # noqa: E402
from ecoa.player import Player  # noqa: E402


class LanguageTests(unittest.TestCase):
    def test_three_languages_exist(self):
        self.assertEqual(set(LANGUAGES), {"pt_BR", "en", "es"})
        self.assertEqual(language_label("en"), "English")
        self.assertEqual(language_label("es"), "Español")

    def test_ui_strings_are_translated(self):
        self.assertEqual(tr("pt_BR", "pause_all"), "Pausar tudo")
        self.assertEqual(tr("en", "pause_all"), "Pause All")
        self.assertEqual(tr("es", "pause_all"), "Pausar Todo")

    def test_theme_options_start_with_uppercase(self):
        for language in LANGUAGES:
            for option in theme_options(language):
                self.assertTrue(option[0].isupper(), (language, option))

    def test_settings_restore_language_and_fallback(self):
        self.assertEqual(Settings.from_dict({"language": "es"}).language, "es")
        self.assertEqual(Settings.from_dict({"language": "fr"}).language, "pt_BR")

    def test_weekday_status_is_localized(self):
        now = schedule.datetime(2026, 11, 9, 10, 0)
        target = schedule.datetime(2026, 11, 10, 9, 0)
        self.assertIn("tomorrow", schedule.fmt_when(target, now, "en"))
        self.assertIn("mañana", schedule.fmt_when(target, now, "es"))


class M4ATests(unittest.TestCase):
    def test_m4a_is_an_allowed_extension(self):
        self.assertIn(".m4a", AUDIO_EXTENSIONS)

    def test_m4a_is_converted_once_to_cached_wav(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "voice.m4a"
            source.write_bytes(b"fake m4a payload")
            cache = root / "dados"
            cache.mkdir()
            patcher = patch.object(paths, "data_dir", return_value=cache)
            patcher.start()
            self.addCleanup(patcher.stop)

            def fake_run(command, **kwargs):
                destination = Path(command[-1])
                destination.write_bytes(b"RIFF" + (b"0" * 80))
                return subprocess.CompletedProcess(command, 0, "", "")

            fake_module = SimpleNamespace(get_ffmpeg_exe=lambda: "ffmpeg-test")
            player = Player()
            with patch.dict(sys.modules, {"imageio_ffmpeg": fake_module}), patch(
                "ecoa.player.subprocess.run", side_effect=fake_run
            ) as run:
                converted = Path(player._prepare_audio_path(str(source)))
                self.assertTrue(converted.is_file())
                self.assertEqual(converted.suffix, ".wav")
                self.assertEqual(run.call_count, 1)
                self.assertEqual(Path(player._prepare_audio_path(str(source))), converted)
                self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
