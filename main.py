from argparse import ArgumentParser
from os import remove
from os.path import join, normpath
from textwrap import indent
from urllib.parse import urlparse, urlunparse
from urllib.request import urlretrieve
from subprocess import check_output
from json import loads


def main():
    args = parse_args()
    if args.mode == 'overrides':
        compare_overrides(args.left, args.right)
    else:
        compare_configs(args.left, args.right)


def parse_args():
    parser = ArgumentParser("Overrides diff")
    parser.add_argument('--mode', choices=('configs', 'overrides'))
    parser.add_argument('left', nargs='?')
    parser.add_argument('right', nargs='?')
    return parser.parse_args()


def compare_overrides(left_url, right_url):
    print_set_differences(override_set(left_url), override_set(right_url))


def compare_configs(left_url, right_url):
    print_set_differences(config_override_set(left_url), config_override_set(right_url))


def print_set_differences(left, right):
    print("Tests skipped in both overrides:")
    print(indent("\n".join(sorted(left & right)), " " * 4))
    print("Tests skipped only in left:")
    print(indent("\n".join(sorted(left - right)), " " * 4))
    print("Tests skipped only in right:")
    print(indent("\n".join(sorted(right - left)), " " * 4))


def remote_js_to_json(url):
    tmp_file, headers = urlretrieve(url)
    try:
        code = "console.log(JSON.stringify(require('{}')))".format(tmp_file)
        return loads(check_output(["node", "--eval", code], encoding="utf-8"))
    finally:
        remove(tmp_file)


def override_files_urls(config_url):
    index_json = remote_js_to_json(config_url)
    return fix_local_paths(config_url, index_json['overrides'])


def fix_local_paths(config_url, override_list):
    results = []
    config_path = urlparse(config_url)
    for override_path in override_list:
        splitted = urlparse(override_path)
        if splitted.scheme:
            results.append(override_path)
        else:
            absolute_override_path = normpath(join(config_path.path, '../..', override_path + ".js"))
            results.append(urlunparse(config_path._replace(path=absolute_override_path)))
    return results


def override_set(override_url):
    return set(remote_js_to_json(override_url).keys())


def config_override_set(config_url):
    results = set()
    for override_url in override_files_urls(config_url):
        results |= override_set(override_url)
    return results


if __name__ == '__main__':
    main()


def test_fix_local_paths():
    fixed = fix_local_paths('https://host/dir/configuration/index.js',
                            ['https://host/dir/overrides.js', './configuration/local'])

    assert fixed == ['https://host/dir/overrides.js', 'https://host/dir/configuration/local.js']
