import re
import argparse
import unicodedata
import requests
import lxml.html


def get_tweets_from_url(url: str) -> list:
    """指定したURLのつぶやきのリストを取得する"""
    try:
        togetter_id = get_togetter_id(url)
        page = 1
        tweets = []
        first_tweets = None
        while True:
            new_tweets = get_tweets(togetter_id, page)
            if (new_tweets is None) or (first_tweets is not None and first_tweets == new_tweets):
                # 新しいtweet が取得できなかったらこれまで取得したものを返す
                return tweets
            else:
                tweets.extend(new_tweets)
                first_tweets = new_tweets if first_tweets is None else first_tweets  # 1ページ目のつぶやきをとっておく
                page += 1
    except:
        return None


TOGETTER_URL_PATTERN = re.compile("http://togetter.com/li/([0-9]+)")
def get_togetter_id(url: str) -> int:
    """URLからtogetterのまとめIDを取得する"""
    matched = TOGETTER_URL_PATTERN.match(url)
    togetter_id = matched.group(1)
    return togetter_id


def get_title_from_url(url: str) -> str:
    """Togetter URL からまとめタイトルを取得する"""
    togetter_id = get_togetter_id(url)
    title = get_title(togetter_id)
    return title


def get_title(togetter_id: int) -> str:
    """TogetterまとめIDに対応するタイトルを取得する"""
    url = "http://togetter.com/li/{0}".format(togetter_id)
    res = requests.get(url)
    if res.status_code != 200:
        return None
    root = lxml.html.fromstring(res.content)
    title = root.xpath("//a[@class='info_title']")[0].text
    return title


def get_tweets(togetter_id: int, page: int=1) -> list:
    """TogetterまとめIDと指定ページのつぶやきを収集する

    http://togetter.com/li/{id}?page={page} からつぶやきのリストを取得する
    参考: http://h3poteto.hatenablog.com/entry/2013/10/20/135403
    """
    url = "http://togetter.com/li/{0}?page={1}".format(togetter_id, page)
    res = requests.get(url)
    if res.status_code != 200:
        return None
    root = lxml.html.fromstring(res.content)
    tweets = list(
        filter(lambda text: text is not None,
               map(lambda tag: tag.text, root.xpath("//div[@class='tweet']"))))

    # 続きを読むが存在するなら取得する
    try:
        if len(root.xpath("//div[@class='more_tweet_box']")) > 0:
            csrf_tokens = root.xpath("/html/head/meta[@name='csrf_token']")
            csrf_token = csrf_tokens[0].attrib["content"]

            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                       "referer": url}
            payload = {"page": page, "csrf_token": csrf_token}
            cookies = {"__gads": "ID=5fe476c6f712153d:T=1420286758:S=ALNI_MZKRdR",
                       "csrf_secret": res.cookies["csrf_secret"]}

            res_more_tweets = requests.post("http://togetter.com/api/moreTweets/{0}".format(togetter_id),
                                            headers=headers, data=payload, cookies=cookies)

            root_more_tweets = lxml.html.fromstring(res_more_tweets.content.decode("UTF-8"))
            more_tweets = list(filter(lambda text: text is not None,
                                      map(lambda tag: tag.text, root_more_tweets.xpath("//div[@class='tweet']"))))
            tweets += more_tweets
    except:
        # 指定したページがそもそも存在していない可能性が高い
        return None

    return tweets


def create_argparser() -> argparse.ArgumentParser:
    """引数パーサを作成"""
    parser = argparse.ArgumentParser(description="Get tweets from Togetter.")
    parser.add_argument("url", metavar="URL", type=str, help="Togetter URL")
    parser.add_argument("-d", dest="directory", metavar="DST", type=str,
                        help="directory to write a result text.")
    return parser


def main():
    """エントリポイント"""
    arg_parser = create_argparser()
    args = arg_parser.parse_args()

    import sys
    togetter_url = args.url
    tweets = get_tweets_from_url(togetter_url)
    if tweets is None:
        print("Failed to get tweets {0}".format(togetter_url), file=sys.stderr)
        sys.exit(1)

    if args.directory is not None:
        # 指定ディレクトリにファイルとして出力
        import os
        output_directory = os.path.abspath(os.path.expanduser(args.directory))
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        title = get_title_from_url(togetter_url)
        output_file_path = os.path.join(output_directory, "{0}.txt".format(title))
        assert(os.path.isabs(output_file_path))

        with open(output_file_path, "w") as f:
            f.writelines(tweets)
    else:
        # 標準出力へ
        for tweet in tweets:
            print(tweet)


if __name__ == "__main__":
    main()