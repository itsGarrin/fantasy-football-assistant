import os
import re
from datetime import datetime, timedelta, UTC, timezone

import pandas as pd
import praw
from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

# Hugging Face Configurations
HF_TOKEN = os.getenv("HF_TOKEN")  # Replace with your token
REPO_ID = os.getenv("REPO_ID")  # Replace with your repo ID

# Reddit API Configuration
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent="fantasyfootballdata",
    username="joindaclub",
)


def extract_links_from_post(submission_id):
    submission = reddit.submission(id=submission_id)

    # Full selftext
    full_text = submission.selftext

    # Regex pattern to match markdown links starting with "Official:"
    pattern = r'\[Official:.*?\]\((/r/fantasyfootball/comments/[^\)]+)\)'
    matches = re.findall(pattern, full_text)

    # Prepend "https://reddit.com" to convert relative links to absolute URLs
    links = [f"https://reddit.com{match}" for match in matches]

    return links


def collect_answers_from_comment(comment, question_id):
    answers = []

    # If the comment is a reply to the question, capture it as an answer
    if comment.parent_id == f"t1_{question_id}" and comment.score >= 0:
        # Skip deleted comments
        if comment.body.lower() == "[deleted]" or not comment.author:
            return []

        answers.append({
            "answer": comment.body,
            "author": comment.author.name if comment.author else "Deleted"
        })

    # If there are replies to this comment, recursively collect them
    for reply in comment.replies:
        answers.extend(collect_answers_from_comment(reply, question_id))

    return answers


def scrape_thread_content(thread_url):
    # Extract thread ID from the URL
    thread_id = thread_url.split("/")[-3]
    thread = reddit.submission(id=thread_id)

    # Extract thread details
    thread_content = {
        "title": thread.title,
        "url": thread.url,
        "author": thread.author.name if thread.author else "Deleted",
        "qa_pairs": [],
    }

    # Scrape comments
    thread.comments.replace_more(limit=None)
    comments = list(thread.comments.list())

    # Iterate over all comments and treat only parent comments as questions
    for comment in comments:
        # Skip deleted comments
        if comment.body.lower() == "[deleted]" or not comment.author:
            continue

        if comment.score >= 0 and comment.parent_id == f"t3_{thread_id}":  # Only include parent comments (questions)
            question = comment.body
            question_author = comment.author.name if comment.author else "Deleted"

            # Collect answers to the question
            answers = collect_answers_from_comment(comment, comment.id)

            # If there are any answers, add the question and answers to the list
            if answers:
                thread_content["qa_pairs"].append({
                    "question": question,
                    "question_author": question_author,
                    "answers": answers
                })

    return thread_content


def classify_thread_type(title):
    title_lower = title.lower()

    # Classify thread by its title
    if "add/drop" in title_lower:
        return "Add_Drop"
    elif "trade" in title_lower:
        return "Trade"
    elif "wdis flex" in title_lower:
        return "WDIS_Flex"
    elif "wdis k/te/def" in title_lower:
        return "WDIS_K_TE_DEF"
    elif "wdis qb" in title_lower:
        return "WDIS_QB"
    elif "wdis rb" in title_lower:
        return "WDIS_RB"
    elif "wdis wr" in title_lower:
        return "WDIS_WR"
    else:
        return "General"  # Default category


def scrape_daily_post_threads(post_ids):
    # Dictionary to store Q&A pairs for each thread type
    threads_data = {
        "Add_Drop": [],
        "Trade": [],
        "WDIS_Flex": [],
        "WDIS_K_TE_DEF": [],
        "WDIS_QB": [],
        "WDIS_RB": [],
        "WDIS_WR": [],
        "General": []
    }

    for post_id in post_ids:
        # Get all links from the daily post
        links = extract_links_from_post(post_id)
        print(f"Found {len(links)} threads from post ID {post_id}.")

        for link in links:
            thread_data = scrape_thread_content(link)

            # Classify thread by its title
            thread_type = classify_thread_type(thread_data["title"])

            # Store Q&A pairs in the corresponding thread type category
            for qa_pair in thread_data["qa_pairs"]:
                question = qa_pair["question"]
                question_author = qa_pair["question_author"]
                for answer in qa_pair["answers"]:
                    threads_data[thread_type].append({
                        "thread_title": thread_data["title"],
                        "thread_url": thread_data["url"],
                        "question": question,
                        "question_author": question_author,
                        "answer": answer["answer"],
                        "answer_author": answer["author"]
                    })

    return threads_data


def get_index_thread_ids(username, days):
    user = reddit.redditor(username)
    thread_ids = []
    cutoff_date = datetime.now(UTC) - timedelta(days=days)
    for submission in user.submissions.new(limit=None):
        submission_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)

        if "Index" in submission.title and submission_time > cutoff_date:
            thread_ids.append(submission.id)
        if len(thread_ids) == days * 3:  # 3 posts a day, stop if we have enough threads
            break
    return thread_ids


def upload_to_huggingface(file_path, repo_id):
    """
    Upload a file to Hugging Face dataset hub.
    """
    api = HfApi()
    try:
        # Upload file to Hugging Face Hub
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=os.path.basename(file_path),
            repo_id=repo_id,
            token=HF_TOKEN,
            repo_type="dataset",
        )
        print(f"Uploaded {file_path} to {repo_id}")
    except Exception as e:
        print(f"Failed to upload {file_path}: {e}")


# Usage Example
if __name__ == "__main__":
    username = "ffbot"
    days = 7  # Number of days to scrape
    post_ids = get_index_thread_ids(username, days)

    # Scrape threads from each post ID
    threads = scrape_daily_post_threads(post_ids)

    # Save each thread type to a separate parquet file
    for thread_type, thread_list in threads.items():
        if thread_list:  # Only save files that have data
            df = pd.DataFrame(thread_list)
            file_name = f"../parquet/{thread_type}_qa_pairs.parquet"
            df.to_parquet(file_name, index=False)

            # Upload the file to Hugging Face
            upload_to_huggingface(file_name, REPO_ID)

            print(f"Saved {len(df)} Q&A pairs for {thread_type} to {file_name}")
