import unittest
from unittest.mock import patch
import urllib.error

from update_language_donut import collect, api


class PrivateLanguageTests(unittest.TestCase):
    def test_private_collection_paginates_and_only_returns_aggregates(self):
        repo = {'full_name': 'owner/confidential-project', 'owner': {'login': 'owner'},
                'fork': False, 'stargazers_count': 2, 'forks_count': 1}

        def response(path, token):
            if path == '/user':
                return {'login': 'owner'}
            if path.startswith('/user/repos'):
                return [repo] * (100 if '&page=1' in path else 1)
            return {'Java': 300, 'C#': 100}

        with patch('update_language_donut.api', side_effect=response) as mock:
            result = collect('owner', 'test-token', True)
        self.assertEqual(result, ({'Java': 30300, 'C#': 10100}, 202, 101))
        self.assertNotIn('confidential-project', str(result))
        self.assertTrue(any('page=2' in call.args[0] for call in mock.call_args_list))

    def test_private_mode_rejects_another_account(self):
        with patch('update_language_donut.api', return_value={'login': 'someone-else'}):
            with self.assertRaisesRegex(RuntimeError, 'profile owner'):
                collect('owner', 'test-token', True)

    def test_network_errors_do_not_expose_private_endpoint(self):
        error = urllib.error.URLError('https://api.github.com/repos/owner/confidential-project/languages')
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                api('/repos/owner/confidential-project/languages', 'test-token')
        self.assertNotIn('confidential-project', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
