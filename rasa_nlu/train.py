#!/usr/bin/env python

from argparse import ArgumentParser
import os
from pathlib import Path


class EnvironmentVariableNotDefinedException(Exception):
    pass


class CommandFailedError(Exception):
    pass


class AbstractExecutor:
    def execute(self, command):
        raise NotImplementedError()

    def on_done(self):
        pass

    def train(self, url):
        self.execute(
            f"curl --fail --location -XPOST {url} --header 'Content-Type: application/x-yaml' "
            f"--data-binary '@./training-data-config.yml' -OJ -vv"
        )


class Executor(AbstractExecutor):
    def execute(self, command):
        exit_code = os.system(command)
        if exit_code != 0:
            raise CommandFailedError(
                f"Expected '{command}' to succeed but it failed with code {exit_code}"
            )


class Printer(AbstractExecutor):
    def __init__(self):
        self._commands = []

    def execute(self, command):
        self._commands.append(command)

    def on_done(self):
        print(" && ".join(self._commands))


def getenv(key, default=None):
    value = os.getenv(key, default)
    if value:
        return value
    if default is not None:
        return default
    raise EnvironmentVariableNotDefinedException(
        "Expected environment variable '{}' to be defined but it wasn't".
        format(key))


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "language",
        help="(required) the language in which to train the model in ISO 639 format. E.g. 'eng', 'sv', 'spa'..."
    )  # yapf: disable
    parser.add_argument(
        "--print-commands",
        action="store_true",
        help="print subcommands instead of executing them, allowing the hosting shell to execute them instead"
    )  # yapf: disable
    parser.add_argument("-u",
                        "--url",
                        default="http://127.0.0.1:5010/model/train",
                        help="URL to Rasa server")  # yapf: disable
    return parser.parse_args()


def concatenate_config_and_nlu_data(language):
    def read(path):
        path = Path(path)
        with path.open() as fd:
            return fd.read()

    def concatenate():
        training_data = read(f"training-data-{language}.yml")
        config = read(f"config-{language}.yml")
        return config + "\n" + training_data

    def write(config_and_training_data):
        with Path("training-data-config.yml").open(mode="w") as file_:
            file_.write(config_and_training_data)

    config_and_training_data = concatenate()
    write(config_and_training_data)


def main():
    args = parse_args()
    executor = Printer() if args.print_commands else Executor()
    concatenate_config_and_nlu_data(args.language)
    executor.train(args.url)
    executor.on_done()


if __name__ == "__main__":
    main()
