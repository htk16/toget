import requests
import lxml.html
import re


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
def get_togetter_id(url: str) -> str:
    """URLからtogetterのまとめIDを取得する"""
    matched = TOGETTER_URL_PATTERN.match(url)
    togetter_id = matched.group(1)
    return togetter_id


def get_tweets(id: int, page:int =1) -> list:
    """http://togetter.com/li/{id}?page={page} からつぶやきのリストを取得する

    参考: http://h3poteto.hatenablog.com/entry/2013/10/20/135403
    """
    url = "http://togetter.com/li/{0}?page={1}".format(id, page)
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
            payload = {"page":page, "csrf_token": csrf_token}
            cookies = {"__gads": "ID=5fe476c6f712153d:T=1420286758:S=ALNI_MZKRdR",
                       "csrf_secret": res.cookies["csrf_secret"]}

            res_more_tweets = requests.post("http://togetter.com/api/moreTweets/{0}".format(id),
                                            headers=headers, data=payload, cookies=cookies)

            root_more_tweets = lxml.html.fromstring(res_more_tweets.content.decode("UTF-8"))
            more_tweets = list(
            filter(lambda text: text is not None,
                   map(lambda tag: tag.text, root_more_tweets.xpath("//div[@class='tweet']"))))
            tweets += more_tweets
    except:
        # 指定したページがそもそも存在していない可能性が高い
        return None

    return tweets


if __name__ == "__main__":
    # tweets = get_tweets(75597, 1)
    import sys
    if len(sys.argv) != 2:
        print("usage: toget togetter_url")
        import os
        os.abort()

    togetter_url = sys.argv[1]
    tweets = get_tweets_from_url(togetter_url)
    if tweets is None:
        print("Failed to get tweets {0}".format(togetter_url), file=sys.stderr)
        os.abort()

    for tweet in tweets:
        print(tweet)
