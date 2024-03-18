import requests
import re
from bs4 import BeautifulSoup
import json
import argparse
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def fetch_description_link(problem_handle):
    # Construct the URL with the problem handle
    url = f"https://vjudge.net/problem/{problem_handle}"

    try:
        # Fetch the webpage
        response = requests.get(url)
        webpage = response.text

        # Regular expression to find the description link
        regex = r'<iframe id="frame-description"\s*src="(/problem/description/\d+\?\d+)"'

        # Search for the link using the regex
        match = re.search(regex, webpage)

        if match:
            description_link = match.group(1)
            full_link = f"https://vjudge.net{description_link}"
            return full_link
        else:
            return "Description link not found."
    except requests.RequestException as e:
        return f"An error occurred: {e}"


def fetch_problem_description(problem_description_link):
    # Construct the URL with the problem handle
    url = problem_description_link

    try:
        # Fetch the webpage
        response = requests.get(url)
        webpage = response.text

        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(webpage, "html.parser")

        # Find the textarea element containing the JSON data
        textarea = soup.find("textarea", class_="data-json-container")
        if textarea:
            # Parse the JSON data
            data_json = json.loads(textarea.text)
            return data_json
        else:
            return "Problem description not found."
    except requests.RequestException as e:
        return f"An error occurred: {e}"


def query_ai(messages):
    while True:
        messages = [
            {
                # hyponotize the AI if necessary...
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "",
                    }
                ],
            }
        ] + messages
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="gpt-3.5-turbo",
            max_tokens=4096,
        )
        content = chat_completion.choices[0].message.content
        if content and "I'm sorry," not in content:
            return chat_completion.choices[0].message.content
        else:
            print(f"Request rejected by AI with '{content}'. Retrying...")


def main():
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Fetch description for a given problem from VJudge."
    )
    parser.add_argument(
        "problem_handle",
        type=str,
        help="The problem handle (e.g., 'CodeForces-1046C').",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Fetch and print the description link
    description_link = fetch_description_link(args.problem_handle)
    if not description_link.startswith("http"):
        print(
            description_link
        )  # Print error message if the description link is not found
        return

    result = fetch_problem_description(description_link)
    if not isinstance(result, dict):
        print(result)
        return

    sections = result["sections"]
    print(str(sections))

    training_dir = "training/"
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an assistant that transcribes HTML text into TeX format. Please transcribe the statement and do not make any edits other than formatting since this is archiving. Please use TeX-style formatting, including $...$ for formulas, `...' and ``...'' for quotation marks, and other text formatting commands such as \texttt.",
                }
            ],
        }
    ]

    # Iterate over each file in the training directory
    for filename in sorted(os.listdir(training_dir)):
        if filename.endswith(".in"):
            # Determine the corresponding output file
            out_filename = filename.replace(".in", ".out")

            # Ensure the output file exists
            if out_filename in os.listdir(training_dir):
                # Read the input file
                with open(os.path.join(training_dir, filename), "r") as file:
                    user_content = file.read()

                # Read the output file
                with open(os.path.join(training_dir, out_filename), "r") as file:
                    assistant_content = file.read()

                # Assemble the data structure for this pair of files
                message_pair = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_content.strip(),
                            }
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": assistant_content.strip(),
                            }
                        ],
                    },
                ]

                # Add the message pair to the list of messages
                messages.extend(message_pair)

    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": str(sections),
                }
            ],
        },
    )

    result = query_ai(messages)

    print(result)


if __name__ == "__main__":
    main()
