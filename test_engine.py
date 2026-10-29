import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine

VIDEO = 'https://www.youtube.com/watch?v=abcdefghijk'

class EngineTests(unittest.TestCase):
    def test_youtube_variants_are_canonical(self):
        for url in ['https://youtu.be/abcdefghijk?si=abc', 'https://www.youtube.com/shorts/abcdefghijk', 'https://m.youtube.com/watch?v=abcdefghijk&list=x', 'https://www.youtube.com/embed/abcdefghijk']:
            with self.subTest(url=url):
                self.assertEqual(engine.normalize_url(url), ('youtube', VIDEO))

    def test_instagram_links_strip_tracking(self):
        self.assertEqual(engine.normalize_url('https://www.instagram.com/reel/ABC_def/?utm_source=x'), ('instagram', 'https://www.instagram.com/reel/ABC_def/'))
        self.assertEqual(engine.normalize_url('https://instagram.com/stories/person/12345/')[0], 'instagram')

    def test_rejects_arbitrary_urls_and_credentials(self):
        for url in ['https://localhost/test', 'http://youtube.com/watch?v=abcdefghijk', 'https://youtube.com.evil.com/watch?v=abcdefghijk', 'https://user:pass@youtube.com/watch?v=abcdefghijk', 'https://youtube.com:444/watch?v=abcdefghijk', 'https://youtube.com/playlist?list=x', 'https://instagram.com/person/', 'file:///etc/passwd', 'https://127.0.0.1/', 'https://youtube.com/watch?v=short', 'https://instagram.com/stories/name/not-a-number/']:
            with self.subTest(url=url), self.assertRaises(engine.UserError):
                engine.normalize_url(url)

    def test_metadata_whitelists_public_fields(self):
        got = engine.public_metadata({'id': 'x', 'title': 'Title', 'http_headers': {'Cookie': 'secret'}, 'url': 'signed-private-cdn', 'description': 'x' * 21000}, 'youtube', VIDEO)
        self.assertNotIn('http_headers', got)
        self.assertNotIn('url', got)
        self.assertEqual(len(got['description']), 20000)

    def test_duration_guards(self):
        for info in [{'duration': None}, {'duration': engine.MAX_DURATION + 1}, {'duration': 0}]:
            with self.assertRaises(engine.UserError): engine.check_duration(info)
        engine.check_duration({'duration': 30})

    def test_caption_segments_export(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            def fake(*args):
                (folder / 'captions.en.json3').write_text(json.dumps({'events': [{'tStartMs': 1000, 'segs': [{'utf8': 'Hello '}, {'utf8': 'world'}]}, {'segs': [{'utf8': '\n'}]}]}))
            with patch.object(engine, 'run_yt', side_effect=fake):
                got = engine.captions(VIDEO, folder, 'en')
                self.assertEqual(got['text'], 'Hello world')
                self.assertEqual(got['segments'][0]['start_seconds'], 1)
                out = engine.save_transcript(folder, got)
                self.assertEqual(out[0].read_text(), 'Hello world')

    def test_missing_captions_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(engine, 'run_yt'):
            with self.assertRaisesRegex(engine.UserError, 'No captions'):
                engine.captions(VIDEO, Path(temp), 'ur')

    def test_no_ai_key_is_clear_error(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            with self.assertRaisesRegex(engine.UserError, 'OPENAI_API_KEY'):
                engine.seo_generate({'title': 'sample'}, 'en')

    def test_no_story_session_is_clear_error(self):
        # Minimal import stub: guard executes before any provider methods.
        import types
        stub = types.SimpleNamespace(Instaloader=lambda **kwargs: object())
        with patch.dict(sys.modules, {'instaloader': stub}), patch.dict(os.environ, {'IG_USERNAME': '', 'IG_SESSION_FILE': '', 'APP_TOKEN': ''}):
            with self.assertRaisesRegex(engine.UserError, 'authorized'):
                engine.instagram_info('https://www.instagram.com/stories/name/123/')

    def test_cdn_rejects_untrusted_before_network(self):
        for url in ['https://evil.com/file', 'https://127.0.0.1/file', 'http://i.ytimg.com/a', 'https://ytimg.com.evil.com/a', 'https://u:p@i.ytimg.com/a']:
            with self.subTest(url=url), self.assertRaises(engine.UserError):
                engine.fetch_asset(url, Path('/tmp/not-written'), 'image')

    def test_cdn_rejects_private_dns(self):
        answer = [(2, 1, 6, '', ('127.0.0.1', 443))]
        with patch.object(engine.socket, 'getaddrinfo', return_value=answer):
            with self.assertRaisesRegex(engine.UserError, 'Unsafe'):
                engine.fetch_asset('https://i.ytimg.com/a', Path('/tmp/not-written'), 'image')

    def test_extract_metadata_writes_json_and_cleans_input(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'input.json').write_text('{}')
            with patch.object(engine, 'youtube_info', return_value={'id': 'abcdefghijk', 'title': 'Owned video', 'duration': 30}):
                result = engine.execute({'url': VIDEO, 'action': 'metadata'}, folder)
            self.assertEqual(result['files'][0]['name'], 'metadata.json')
            self.assertEqual(json.loads((folder / 'metadata.json').read_text())['title'], 'Owned video')
            self.assertFalse((folder / 'input.json').exists())

    def test_instagram_image_only_video_error(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(engine, 'instagram_info', return_value=({'title': 'Photo'}, [{'video': None, 'image': 'not-fetched'}])):
            with self.assertRaisesRegex(engine.UserError, 'no video'):
                engine.execute({'url': 'https://instagram.com/p/ABC123/', 'action': 'video'}, Path(temp))

    def test_instagram_captions_explains_asr(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(engine, 'instagram_info', return_value=({'title': 'Reel'}, [])):
            with self.assertRaisesRegex(engine.UserError, 'Audio transcript'):
                engine.execute({'url': 'https://instagram.com/reel/ABC123/', 'action': 'transcript'}, Path(temp))

    def test_bad_action_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(engine.UserError):
            engine.execute({'url': VIDEO, 'action': 'shell'}, Path(temp))

if __name__ == '__main__':
    unittest.main()
