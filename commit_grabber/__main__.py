import json
import os
import shutil
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict, List, Text, Union

from tqdm import tqdm

from commit_grabber.commit_grabber import CommitGrabber


PathType = Union[Text, Path]
JsonType = Dict[Text, Any]


def parse_repo_list(repo_list: Text) -> List[Text]:
    with open(repo_list, mode="r") as input_file:
        repos = [json.loads(line) for line in input_file.readlines()]
    return [repo["url"] for repo in repos]


def read_parsed_repo(repo_path: PathType) -> List[Text]:
    with open(repo_path, mode="r") as repo_file:
        data = repo_file.readlines()
    return data


def merge_parsed_repos(repo_paths: List[PathType], output_path: PathType) -> None:
    with open(output_path, mode="w") as output_file:
        for idx, repo_path in enumerate(repo_paths):
            # write temp file content to output file
            repo_content = read_parsed_repo(repo_path)
            output_file.writelines(repo_content)

            # append newline to merge files correctly
            if idx != len(repo_paths):
                output_file.write("\n")

            # remove temp dir
            shutil.rmtree(os.path.dirname(repo_path))


def main() -> None:
    # prepare cli argument parser
    parser = ArgumentParser()
    parser.add_argument("--repo_list", default=None, type=str, required=True, help="")
    parser.add_argument("--output_path", default=None, type=str, required=True, help="")
    args = parser.parse_args()

    # create output dir if needed
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # get repo urls for cloning
    repo_list = parse_repo_list(args.repo_list)

    # clone and parse repos, collect result files
    parsed_repos: List[PathType] = []
    for repo_url in tqdm(repo_list):
        grabber = CommitGrabber()
        parsed_repo = grabber.parse_repository(repo_url, output_path)
        parsed_repos.append(parsed_repo)

    # merge result files into one output
    merge_parsed_repos(parsed_repos, output_path)


if __name__ == "__main__":
    main()
