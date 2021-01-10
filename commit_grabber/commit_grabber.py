import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Text, Union

from dataclasses_json import DataClassJsonMixin
from git import Git
from pydriller import Commit, RepositoryMining


@dataclass
class ParsedModification(DataClassJsonMixin):
    old_filepath: Text
    new_filepath: Text
    old_content: Text
    new_content: Text


@dataclass
class ParsedCommit(DataClassJsonMixin):
    hash: Text
    message: Text
    modifications: List[ParsedModification]


@dataclass
class DataSample(DataClassJsonMixin):
    commit: ParsedCommit
    repository: Text
    labels: List[Text] = field(default_factory=list)


class CommitGrabber:
    def parse_repository(
        self, repository_url: Text, output_path: Union[Text, Path]
    ) -> Union[Text, Path]:
        repo_path = self._clone_repository(repository_url)
        repo_mining = RepositoryMining(repo_path)

        commits: List[ParsedCommit] = []
        for commit in repo_mining.traverse_commits():
            parsed_commit = self._parse_commit(commit)
            if parsed_commit is not None:
                commits.append(parsed_commit)

        data_samples = [DataSample(commit, repository_url) for commit in commits]

        # prepare temp output path for storing result file
        temp_path = tempfile.mkdtemp()
        output_filename = os.path.basename(output_path)
        output_path = Path(os.path.join(temp_path, output_filename))

        # write parsed commits to the temp result file
        with open(output_path, mode="w") as output_file:
            data_samples_json = [sample.to_json() for sample in data_samples]
            output_file.writelines("\n".join(data_samples_json))

        # remove cloned repository path
        shutil.rmtree(repo_path)

        return output_path

    def _clone_repository(self, repository_url: Text) -> Text:
        repo_name = os.path.split(repository_url)[-1]
        repo_path = tempfile.mkdtemp()
        repo_git = Git(repo_path)
        repo_git.clone(repository_url)
        return os.path.join(repo_path, repo_name)

    def _parse_commit(self, commit: Commit) -> Optional[ParsedCommit]:
        if len(commit.modifications) > 5:
            return None
        elif "merged" in commit.msg:
            return None
        elif "reverted" in commit.msg:
            return None
        elif not self._is_conventional(commit.msg):
            return None

        modifications: List[ParsedModification] = []
        for mod in commit.modifications:
            parsed_mod = ParsedModification(
                old_filepath=mod.old_path or "",
                new_filepath=mod.new_path or "",
                old_content=mod.source_code_before or "",
                new_content=mod.source_code or "",
            )

            # filter out non-python source files
            filepath = parsed_mod.old_filepath or parsed_mod.new_filepath
            file_ext = os.path.splitext(filepath)[-1]
            if file_ext != ".py":
                continue

            # filter out large source files
            nloc = mod.nloc or 0
            if nloc > 5_000:
                continue

            modifications.append(parsed_mod)

        if not modifications:
            return None

        return ParsedCommit(
            hash=commit.hash,
            message=commit.msg,
            modifications=modifications,
        )

    def _is_conventional(self, message: Text) -> bool:
        pattern = r"^(feat|feature|fix|refactor|ref|chore|ci|build|style|test|revert)(?:\(.*\))?:.*"
        match = re.match(pattern, message, re.IGNORECASE)
        return match is not None
