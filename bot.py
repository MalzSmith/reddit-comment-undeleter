#coding=UTF8

# Some of this script is shamelessly stolen from https://github.com/fmhall/Petrosian-Bot/blob/master/src/main.py


import json
import threading, queue
import typing
from praw import Reddit
from praw.models import Comment
import logging
from dotenv import load_dotenv
from typing import Callable
import os


log_format = "%(asctime)s: %(threadName)s: %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

load_dotenv()
CLIENT = os.getenv("CLIENT_ID")
SECRET = os.getenv("CLIENT_SECRET")
REDDIT_USER = os.getenv("REDDIT_USER")
REDDIT_PASS = os.getenv("REDDIT_PASS")

# Delay for checking back on posts (in minutes)
DELAY = 15

# Path for saving the comments
PATH = 'comments'

# Create the reddit object instance using Praw
reddit = Reddit(
    user_agent="What's the point of this thing",
    client_id=CLIENT,
    client_secret=SECRET,
    ratelimit_seconds = 600,
# You don't really need these 2 as you don't make any comments with the bot anyways
    username=REDDIT_USER,
    password=REDDIT_PASS
)

# Create result directory
if not os.path.exists(PATH):
    os.makedirs(PATH)

# Create queue object
q = queue.Queue()

logger.info("Connected to Reddit!")

def restart(handler: Callable):
    """
    Decorator that restarts threads if they fail
    """

    def wrapped_handler(*args, **kwargs):
        logger.info("Starting thread with: %s", args)
        while True:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error("Exception: %s", e)

    return wrapped_handler

def is_removed(comment: Comment) -> bool:
	c = Comment(reddit, comment.id)
	try:
		author = str(c.author.name)
	except:
		author = '[Deleted]'
	if author == '[Deleted]':
		return True
	else:
		return False

def addToQueue(comment: Comment) -> None:
    q.put(comment)

@restart
def watcher(subreddit: str):
    for comment in reddit.subreddit(subreddit).stream.comments():
        t = threading.Timer(DELAY * 60, addToQueue, (comment, ))  
        t.start()

@restart
def worker():
    while True:
        comment = typing.cast(Comment, q.get())
        if is_removed(comment):
            parent_comment = {}
            try:
                parent = Comment(reddit, comment.parent_id)
                parent_comment = {
                    "author": f'https://reddit.com/u/{parent.author.name}',
                    "permalink": f'https://reddit.com{parent.permalink}',
                    "body": parent.body
                }
            except:
                pass
            data = {
                "author": f'https://reddit.com/u/{comment.author.name}',
                "permalink": f'https://reddit.com{comment.permalink}',
                "parent": parent_comment,
                "body": comment.body
            }
            with open (f'{PATH}/{comment.id}.json', 'w', encoding='utf-16') as f:
                json.dump(data, f, indent=2)
            logger.info(f'Deleted comment by {data["author"]}: {data["permalink"]}')
        q.task_done()


if __name__ == "__main__":
    threads = []
    threads.append(threading.Thread(target=watcher, args=("all", ), name="watcher"))
    threads.append(threading.Thread(target=worker, name="worker"))
    for th in threads:
        th.start()
